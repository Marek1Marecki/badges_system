"""Widoki REST API dla obszaru Turysty (Faza C).

Warstwa HTTP jest cienką powłoką:
  - parsuje request i wyciąga profile_id z sesji (nigdy z body)
  - wywołuje Use Case przez kontener DI
  - serializuje wynik lub błąd do RFC 7807 JSON
  - NIE zawiera logiki biznesowej

Obsługa wyjątków domenowych jest zaimplementowana bezpośrednio w widokach,
ponieważ RequestFactory (używany w testach) omija middleware.process_exception.
Middleware RFC7807ErrorMiddleware działa jako dodatkowe zabezpieczenie
dla nieoczekiwanych wyjątków w środowisku produkcyjnym.
"""

import json
import logging
from typing import Any

from django.contrib.gis.measure import D
from django.core.cache import cache
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from pydantic import ValidationError

from application.dto.ascent_dto import AscentInputDTO
from application.dto.map_dto import MapExploreRequestDTO
from application.dto.user_context_dto import (
    LogisticStatusUpdateDTO,
    UpdateProfileRequestDTO,
)
from application.exceptions import (
    ApplicationException,
    BitemporalTimeError,
    ConflictError,
    IllegalStateTransitionError,
    ResourceNotFoundError,
    UseCaseError,
)
from apps.badges.models import TouristObject
from apps.badges.tasks import recalculate_poi_scores_task
from apps.tourists.models import TouristProfile
from bootstrap.rate_limiting import check_rate_limit, rate_limited_response

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _problem_detail(
    request,
    error_type: str,
    title: str,
    status: int,
    detail: str,
) -> JsonResponse:
    """Buduje odpowiedź RFC 7807 Problem Details.

    Args:
      request:
      error_type: str:
      title: str:
      status: int:
      detail: str:
      error_type: str:
      title: str:
      status: int:
      detail: str:

    Returns:
    """
    return JsonResponse(
        {
            "type": f"https://api.pttk-badges.pl/errors/{error_type}",
            "title": title,
            "status": status,
            "detail": detail,
            "instance": request.path,
            "request_id": getattr(request, "request_id", "unknown"),
        },
        status=status,
    )


def _require_auth(request) -> JsonResponse | None:
    """Guard: zwraca 401 jeśli użytkownik nie jest zalogowany.

    Args:
      request:

    Returns:
    """
    if not request.user or not request.user.is_authenticated:
        return _problem_detail(
            request,
            error_type="authentication-required",
            title="Wymagane uwierzytelnienie",
            status=401,
            detail="Zaloguj się, aby korzystać z API.",
        )
    return None


def _handle_application_exception(request, exc: ApplicationException) -> JsonResponse:
    """Centralny mapper wyjątków aplikacyjnych → RFC 7807.

    Wywoływany bezpośrednio z widoków, bo RequestFactory omija middleware.

    Args:
      request:
      exc: ApplicationException:
      exc: ApplicationException:

    Returns:
    """
    request_id = getattr(request, "request_id", "unknown")

    if isinstance(exc, ResourceNotFoundError):
        logger.info("resource_not_found", extra={"request_id": request_id})
        return _problem_detail(request, "resource-not-found", "Zasób nie istnieje", 404, "Zasób nie istnieje.")

    if isinstance(exc, IllegalStateTransitionError):
        logger.warning("invalid_state_transition", extra={"request_id": request_id})
        return _problem_detail(
            request,
            "invalid-state-transition",
            "Niedozwolona Zmiana Stanu",
            409,
            "Niedozwolona zmiana stanu logistycznego (Kanban FSM).",
        )

    if isinstance(exc, ConflictError):
        logger.warning("conflict", extra={"request_id": request_id})
        return _problem_detail(request, "conflict", "Konflikt Danych", 409, "Konflikt danych.")

    if isinstance(exc, BitemporalTimeError):
        logger.warning("bitemporal_violation", extra={"request_id": request_id})
        return _problem_detail(
            request,
            "bitemporal-constraint-violated",
            "Naruszenie Bitemporalności",
            422,
            "Naruszenie bitemporalności.",
        )

    if isinstance(exc, UseCaseError):
        logger.info("validation_failed", extra={"request_id": request_id})
        return _problem_detail(request, "validation-failed", "Błąd Walidacji", 422, "Błąd walidacji.")

    logger.error(
        "unhandled_application_exception",
        extra={"request_id": request_id},
        exc_info=True,
    )
    return _problem_detail(
        request,
        "internal-error",
        "Wewnętrzny Błąd Serwera",
        500,
        "Wystąpił wewnętrzny błąd serwera.",
    )


# ---------------------------------------------------------------------------
# Widoki
# ---------------------------------------------------------------------------


class AscentLogView(View):
    """POST /api/v1/ascents/

    Rejestruje wejście turysty na obiekt turystyczny.

    Request body (JSON):
        peak_id (int): ID obiektu turystycznego
        ascent_date (str): Data wejścia w formacie YYYY-MM-DD

    Args:

    Returns:
      201: {"ascent_id": int}
      401: RFC 7807 — brak autentykacji
      409: RFC 7807 — duplikat wejścia (D-04)
      422: RFC 7807 — naruszenie bitemporalności (T-01) lub data z przyszłości (T-03)
    """

    def post(self, request: Any) -> JsonResponse:
        """Rejestruje nowe wejście na szczyt (US-C03).

        Args:
          request: Any:
          request: Any:

        Returns:
        """
        auth_error = _require_auth(request)
        if auth_error:
            return auth_error

        profile_id = request.session.get("active_profile_id") or request.user.profiles.first().id

        try:
            body = json.loads(request.body)
            ascent_input = AscentInputDTO(**body)
        except (json.JSONDecodeError, ValueError):
            logger.warning(
                "invalid_ascent_payload",
                extra={"request_id": getattr(request, "request_id", "unknown")},
            )
            return _problem_detail(
                request=request,
                error_type="validation-error",
                title="Błąd Walidacji Danych Wejściowych",
                status=422,
                detail="Nieprawidłowe dane wejściowe.",
            )

        try:
            use_case = request.app_container.log_ascent

            # WPISUJEMY TYLKO TO (UoW i Event Publisher są zaszyte w środku!)
            ascent_id = use_case.execute(profile_id=profile_id, dto=ascent_input)

            return JsonResponse({"ascent_id": ascent_id, "status": "CREATED"}, status=201)

        except ApplicationException as exc:
            return _handle_application_exception(request, exc)


class BadgeSubscribeView(View):
    """POST /api/v1/badges/{badge_code}/subscribe/

    Rozpoczyna zdobywanie odznaki (subskrypcja + zakotwiczenie Praw Nabytych).

    Args:

    Returns:
      201: {"progress_id": int, "status": "SUBSCRIBED"}
      401: RFC 7807 — brak autentykacji
      422: RFC 7807 — brak regulaminu dla daty zakotwiczenia
    """

    def post(self, request: Any, badge_code: str) -> JsonResponse:
        """Rozpoczyna zdobywanie nowej odznaki i zakotwicza regulamin (US-C05).

        Args:
            request: Żądanie HTTP z zalogowanym użytkownikiem.
            badge_code: Kod odznaki do subskrypcji.

        Returns:
            201: {"progress_id": int, "status": "SUBSCRIBED"}
            401/404/422: RFC 7807 Problem Details
        """
        auth_error = _require_auth(request)
        if auth_error:
            return auth_error

        profile_id = request.session.get("active_profile_id") or request.user.profiles.first().id

        try:
            use_case = request.app_container.start_badge_progress

            # WPISUJEMY TYLKO TO:
            progress_id = use_case.execute(profile_id=profile_id, badge_code=badge_code)

            recalculate_poi_scores_task.delay(profile_id)

            return JsonResponse({"progress_id": progress_id, "status": "SUBSCRIBED"}, status=201)

        except ApplicationException as exc:
            return _handle_application_exception(request, exc)

    def delete(self, request, badge_code: str):
        """Anuluje subskrypcję odznaki i usuwa postęp (US-C05).

        Args:
            request: Żądanie HTTP z zalogowanym użytkownikiem.
            badge_code: Kod odznaki do wyrejestrowania.

        Returns:
            200: {"status": "UNSUBSCRIBED"}
            401/404: RFC 7807 Problem Details
        """
        auth_error = _require_auth(request)
        if auth_error:
            return auth_error

        profile_id = request.session.get("active_profile_id") or request.user.profiles.first().id

        try:
            use_case = request.app_container.unsubscribe_badge
            use_case.execute(profile_id=profile_id, badge_code=badge_code)

            return JsonResponse({"status": "UNSUBSCRIBED"}, status=200)

        except ApplicationException as exc:
            return _handle_application_exception(request, exc)


class BadgeProgressView(View):
    """GET /api/v1/badges/{badge_code}/progress/

    Oblicza i zwraca aktualny postęp turysty w zdobywaniu odznaki (On-Demand).

    Query params:
        cycle (int, optional): Numer cyklu, domyślnie 1

    Args:

    Returns:
      200: słownik z wynikiem ewaluacji domenowej
      401: RFC 7807 — brak autentykacji
      404: RFC 7807 — turysta nie subskrybuje odznaki
    """

    def get(self, request, badge_code: str):
        """Oblicza i zwraca aktualny postęp turysty w zdobywaniu odznaki (On-Demand).

        Args:
            request: Żądanie HTTP z zalogowanym użytkownikiem.
            badge_code: Kod odznaki do sprawdzenia.

        Returns:
            200: Słownik z wynikiem ewaluacji domenowej.
            401/404/422: RFC 7807 Problem Details.
        """
        auth_error = _require_auth(request)
        if auth_error:
            return auth_error

        try:
            cycle_number = int(request.GET.get("cycle", 1))
        except (TypeError, ValueError):
            return _problem_detail(
                request, "validation-failed", "Błąd Walidacji", 422, "Parametr 'cycle' musi być liczbą całkowitą."
            )

        # Nie potrzebujemy tu w ogóle obiektu DTO (skoro UseCase przyjmuje proste parametry!)
        # Wyciągamy po prostu bezpiecznie profile_id z sesji (Ochrona IDOR z AUDYT-070)
        profile_id = request.session.get("active_profile_id") or request.user.profiles.first().id

        try:
            use_case = request.app_container.evaluate_badge_progress
            result = use_case.execute(profile_id=profile_id, badge_code=badge_code, cycle_number=cycle_number)
        except ApplicationException as exc:
            return _handle_application_exception(request, exc)

        return JsonResponse(result.model_dump(), status=200)


class MapObjectsView(View):
    """GET /api/v1/map/objects?bbox={min_lon,min_lat,max_lon,max_lat}

    Zwraca GeoJSON z obiektami dla widocznego okna mapy (ADR-011).
    Kolory punktów odzwierciedlają postęp turysty (ADR-010).

    Args:

    Returns:
    """

    def get(self, request):
        """Zwraca GeoJSON z obiektami dla widocznego okna mapy (ADR-011).

        Kolory punktów odzwierciedlają postęp turysty (ADR-010).

        Args:
            request: Żądanie HTTP z parametrami bbox, region_id, badge_code.

        Returns:
            200: GeoJSON FeatureCollection z obiektami i kolorami.
            401/422: RFC 7807 Problem Details.
        """
        auth_error = _require_auth(request)
        if auth_error:
            return auth_error

        bbox_str = request.GET.get("bbox")
        if not bbox_str:
            return _problem_detail(
                request, "validation-failed", "Błąd Walidacji", 422, "Parametr 'bbox' jest wymagany."
            )

        try:
            min_lon, min_lat, max_lon, max_lat = map(float, bbox_str.split(","))
        except ValueError:
            return _problem_detail(
                request, "validation-failed", "Błąd Walidacji", 422, "Format 'bbox' musi być: lon,lat,lon,lat."
            )

        region_id_str = request.GET.get("region_id")

        # SECURITY (AUDYT-070): Ujednolicony, bezpieczny pattern — zawsze fallback na pierwszy profil
        profile_id = request.session.get("active_profile_id") or request.user.profiles.first().id

        try:
            dto = MapExploreRequestDTO(
                profile_id=profile_id,
                min_lon=min_lon,
                min_lat=min_lat,
                max_lon=max_lon,
                max_lat=max_lat,
                badge_code=request.GET.get("badge_code"),
                region_level=request.GET.get("region_level"),
                region_id=int(region_id_str) if region_id_str else None,
            )
        except (ValueError, TypeError, ValidationError):
            return _problem_detail(
                request,
                "validation-failed",
                "Nieprawidłowe dane wejściowe",
                422,
                "Nieprawidłowe dane wejściowe.",
            )

        try:
            use_case = request.app_container.explore_map
            geojson_data = use_case.execute(dto)
        except ApplicationException as exc:
            return _handle_application_exception(request, exc)

        return JsonResponse(geojson_data, status=200)


class BadgeLogisticsView(View):
    """PATCH /api/v1/progress/{progress_id}/logistics/

    Aktualizuje status logistyczny odznaki w Osobistym Trackerze Turysty.

    Args:

    Returns:
    """

    def patch(self, request, progress_id: int):
        """Aktualizuje status logistyczny odznaki w Osobistym Trackerze Turysty.

        Args:
            request: Żądanie HTTP z JSON body zawierającym logistic_status i status_date.
            progress_id: ID postępu do aktualizacji.

        Returns:
            200: {"status": "UPDATED", "logistic_status": str}
            401/404/422: RFC 7807 Problem Details.
        """
        auth_error = _require_auth(request)
        if auth_error:
            return auth_error

        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return _problem_detail(
                request, "validation-failed", "Nieprawidłowe dane", 422, "Ciało żądania musi być JSON."
            )

        try:
            dto = LogisticStatusUpdateDTO(**body)
        except ValidationError:
            return _problem_detail(
                request,
                "validation-failed",
                "Błąd Walidacji",
                422,
                "Nieprawidłowe dane wejściowe.",
            )

        # SECURITY: Identyfikacja użytkownika zawsze z sesji
        profile_id = request.session.get("active_profile_id") or request.user.profiles.first().id

        try:
            use_case = request.app_container.advance_logistic_status
            use_case.execute(
                profile_id=profile_id,
                progress_id=progress_id,
                new_logistic_status=dto.logistic_status,
                status_date=dto.status_date,
                actor_user_id=request.user.id,
            )
        except ApplicationException as exc:
            return _handle_application_exception(request, exc)

        return JsonResponse({"status": "UPDATED", "logistic_status": dto.logistic_status}, status=200)


class VectorTileView(View):
    """GET /api/v1/tiles/{layer}/{z}/{x}/{y}.pbf.

    Zwraca zbuforowane, skompresowane (GZIP) kafelki wektorowe.

    Args:

    Returns:
    """

    def get(self, request, layer: str, z: int, x: int, y: int):
        """

        Args:
            request: Żądanie HTTP.
            layer: Nazwa warstwy mapy.
            z: Zoom.
            x: Kolumna kafelka.
            y: Rząd kafelka.

        Returns:
            200: Skompresowany kafelek wektorowy (GZIP).
            204: Brak danych dla tego obszaru.
            401/404: RFC 7807 Problem Details.
        """
        if not check_rate_limit("mvt_tiles", request, limit=120, window=60):
            return rate_limited_response(request, window=60)

        try:
            use_case = request.app_container.get_mvt_tile
            # Use Case zwraca skompresowane bajty (lub None) z DB/Redis
            tile_data = use_case.execute(layer, z, x, y)
        except ApplicationException as exc:
            return _handle_application_exception(request, exc)

        if not tile_data:
            # 204 No Content - standardowe zachowanie dla pustych kafelków
            return HttpResponse(status=204)

        response = HttpResponse(tile_data, content_type="application/vnd.mapbox-vector-tile")
        response["Content-Encoding"] = "gzip"
        response["Cache-Control"] = "public, max-age=86400"

        return response


class NearbyObjectsView(View):
    """GET /api/v1/objects/{id}/nearby/

    Zwraca obiekty w promieniu 2 km od celu w formacie GeoJSON (US-C14).

    Args:

    Returns:
    """

    def get(self, request: HttpRequest, object_id: int) -> JsonResponse:
        """Zwraca obiekty w promieniu 2 km od celu w formacie GeoJSON (US-C14).

        Args:
            request: Żądanie HTTP z zalogowanym użytkownikiem.
            object_id: ID centralnego obiektu turystycznego.

        Returns:
            200: GeoJSON FeatureCollection z obiektami i kolorami.
            401/404: RFC 7807 Problem Details.
        """
        if not check_rate_limit("nearby_objects", request, limit=120, window=60):
            return rate_limited_response(request, window=60)

        center_obj = get_object_or_404(TouristObject, id=object_id)

        if not center_obj.geom:
            return JsonResponse({"type": "FeatureCollection", "features": []})

        # GeoDjango używając ST_DWithin potrafi natywnie operować w metrach przez obiekt D()
        nearby_qs = TouristObject.objects.filter(
            geom__distance_lte=(center_obj.geom, D(m=2000)), is_active=True, status="READY"
        ).exclude(id=object_id)[:100]  # Limit bezpieczeństwa

        # Pobieramy stan kolorów z Redis dla zalogowanego turysty
        colors = {}
        if request.user.is_authenticated:
            cache_key = f"map_state:{request.user.id}"
            cached_data = cache.get(cache_key) or {}
            colors = cached_data.get("colors", {})

        features = []
        # Dodajemy sam środek radaru (główny obiekt) na sztywno jako pierwszy element
        center_color = colors.get(center_obj.id, colors.get(str(center_obj.id), "GRAY"))
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [center_obj.geom.x, center_obj.geom.y]},
                "properties": {
                    "id": center_obj.id,
                    "name": center_obj.name,
                    "type": center_obj.type,
                    "peak_color": center_color,
                    "is_center": True,
                },
            }
        )

        for n in nearby_qs:
            color = colors.get(n.id, colors.get(str(n.id), "GRAY"))
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [n.geom.x, n.geom.y]},
                    "properties": {"id": n.id, "name": n.name, "type": n.type, "peak_color": color, "is_center": False},
                }
            )

        return JsonResponse({"type": "FeatureCollection", "features": features})


class GpxAnalyzeView(View):
    """POST /api/v1/gpx/analyze/

    Analizuje w locie przesłany plik GPX (w RAM) i zwraca propozycje obiektów.

    Args:

    Returns:
    """

    def post(self, request: HttpRequest) -> JsonResponse:
        """Analizuje w locie przesłany plik GPX (w RAM) i zwraca propozycje obiektów.

        Args:
            request: Żądanie HTTP z plikiem GPX w polu 'file'.

        Returns:
            200: Wynik analizy GPX.
            401/429/422: RFC 7807 Problem Details.
        """
        if not check_rate_limit("gpx_analyze", request, limit=30, window=60):
            return rate_limited_response(request, window=60)

        auth_error = _require_auth(request)
        if auth_error:
            return auth_error

        if "file" not in request.FILES:
            return _problem_detail(
                request, "validation-failed", "Błąd Walidacji", 422, "Należy przesłać plik GPX w polu 'file'."
            )

        gpx_file = request.FILES["file"]

        # Ochrona pamięci serwera: odrzucamy pliki > 10MB
        if gpx_file.size > 10 * 1024 * 1024:
            return _problem_detail(
                request, "validation-failed", "Plik za duży", 422, "Plik GPX nie może przekraczać 10 MB."
            )

        # SECURITY: Walidacja typu MIME i Magic Bytes zanim plik trafi do RAM
        allowed_mime_types = ("application/gpx+xml", "application/xml", "text/xml", "text/plain")
        content_type = gpx_file.content_type
        if content_type and content_type not in allowed_mime_types:
            return _problem_detail(
                request,
                "validation-failed",
                "Niedozwolony typ pliku",
                422,
                "Akceptowane są pliki GPX (application/gpx+xml, text/xml).",
            )

        # Magic bytes: GPX musi być XML-em
        first_chunk = gpx_file.read(512)
        gpx_file.seek(0)
        if b"<gpx" not in first_chunk and not first_chunk.lstrip().startswith(b"<?xml"):
            return _problem_detail(
                request,
                "validation-failed",
                "Nieprawidłowy format pliku",
                422,
                "Plik nie jest prawidłowym plikiem GPX ani XML.",
            )

        file_content = gpx_file.read()

        try:
            use_case = request.app_container.analyze_gpx_track
            result = use_case.execute(file_content)
        except ApplicationException as exc:
            return _handle_application_exception(request, exc)

        return JsonResponse(result.model_dump(), status=200)


class BulkAscentLogView(View):
    """POST /api/v1/ascents/bulk/

    Masowy zapis logów (np. po akceptacji z GPX). Zwraca wynik częściowy.

    Args:

    Returns:
    """

    def post(self, request: Any) -> JsonResponse:
        """Masowo rejestruje logi wejść z pliku GPX (US-C17).

        Args:
            request: Żądanie HTTP z listą wejść w body JSON.

        Returns:
            200: Wynik częściowy zapisu.
            401/422: RFC 7807 Problem Details.
        """
        auth_error = _require_auth(request)
        if auth_error:
            return auth_error

        profile_id = request.session.get("active_profile_id") or request.user.profiles.first().id

        try:
            body = json.loads(request.body)
            if not isinstance(body, list):
                raise ValueError("Payload musi być listą obiektów JSON.")
            ascents = [AscentInputDTO(**item) for item in body]
        except (json.JSONDecodeError, ValueError, ValidationError):
            return _problem_detail(
                request=request,
                error_type="validation-error",
                title="Błąd Walidacji Danych Wejściowych",
                status=422,
                detail="Nieprawidłowe dane wejściowe.",
            )
        try:
            use_case = request.app_container.bulk_log_ascents

            # WPISUJEMY TYLKO TO:
            result = use_case.execute(profile_id=profile_id, ascents=ascents)

            return JsonResponse(result, status=200)

        except ApplicationException as exc:
            return _handle_application_exception(request, exc)


class ProfileSettingsView(View):
    """PATCH /api/v1/profiles/{profile_id}/

    Aktualizuje ustawienia profilu (np. Wiek, Mapa). Posiada ochronę IDOR.

    Args:

    Returns:
    """

    def patch(self, request, profile_id: int):
        """Aktualizuje ustawienia profilu (np.

        Wiek, Mapa). Posiada ochronę IDOR.
                Args:
                    request: Żądanie HTTP z JSON body (nickname, birth_date, preferred_base_map).
                    profile_id: ID profilu do aktualizacji.

                Returns:
                    200: {"status": "UPDATED"}
                    401/404/422: RFC 7807 Problem Details.
        """
        auth_error = _require_auth(request)
        if auth_error:
            return auth_error

        # IDOR GUARD: Tylko właściciel konta Google może modyfikować powiązane z nim profile!
        try:
            profile = get_object_or_404(TouristProfile, id=profile_id, user=request.user)
        except Http404:
            return _problem_detail(request, "resource-not-found", "Zasób nie istnieje", 404, "Brak dostępu do profilu.")

        try:
            body = json.loads(request.body)
            # SECURITY (AUDYT-048): zapisujemy oryginalne żądanie birth_date
            # zanim zostanie przekształcone (pusty string → None).
            original_birth_date_requested = body.get("birth_date")

            # Puste stringi dla daty zamieniamy na None (czyszczenie wieku)
            if original_birth_date_requested == "":
                body["birth_date"] = None
            dto = UpdateProfileRequestDTO(**body)
        except ValidationError:
            return _problem_detail(
                request,
                "validation-failed",
                "Błąd Walidacji",
                422,
                "Nieprawidłowe dane wejściowe.",
            )

        if dto.nickname:
            profile.nickname = dto.nickname

        # SECURITY (AUDYT-048): birth_date jest niezmienny po ustawieniu.
        # Chroni to przed Age Fraud — manipulacją wiekiem w celu zdobycia odznak.
        if original_birth_date_requested is not None:
            if profile.birth_date is not None:
                logger.warning(
                    "Attempt to modify birth_date for profile %s by user %s",
                    profile.id,
                    request.user.id,
                    extra={"request_id": getattr(request, "request_id", "unknown")},
                )
                return _problem_detail(
                    request,
                    "conflict",
                    "Niedozwolona zmiana",
                    409,
                    "Data urodzenia nie może być zmieniona po ustawieniu.",
                )
            profile.birth_date = dto.birth_date

        if dto.preferred_base_map:
            profile.preferred_base_map = dto.preferred_base_map

        try:
            profile.save(update_fields=["nickname", "birth_date", "preferred_base_map"])
            return JsonResponse({"status": "UPDATED"}, status=200)
        except ApplicationException as exc:
            return _handle_application_exception(request, exc)


class ProfileUpgradeView(View):
    """POST /api/v1/profiles/{profile_id}/upgrade/

    Sztuczna bramka płatności (Wymusza pakiet PRO dla testów UX).

    Args:

    Returns:
    """

    def post(self, request, profile_id: int):
        """Sztuczna bramka płatności (Wymusza pakiet PRO dla testów UX).

        Args:
            request: Żądanie HTTP z zalogowanym użytkownikiem.
            profile_id: ID profilu do podniesienia.

        Returns:
            200: {"status": "UPGRADED"}
            401/404: RFC 7807 Problem Details.
        """
        auth_error = _require_auth(request)
        if auth_error:
            return auth_error

        try:
            profile = get_object_or_404(TouristProfile, id=profile_id, user=request.user)
        except Http404:
            return _problem_detail(
                request=request,
                error_type="resource-not-found",
                title="Zasób nie istnieje",
                status=404,
                detail="Brak dostępu do profilu.",
            )

        try:
            profile.active_plan = "PRO"
            profile.save(update_fields=["active_plan"])

            recalculate_poi_scores_task.delay(profile_id)

            return JsonResponse({"status": "UPGRADED"}, status=200)
        except ApplicationException as exc:
            return _handle_application_exception(request, exc)
