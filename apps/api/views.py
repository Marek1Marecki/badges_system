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
from typing import Any

from django.contrib.gis.measure import D
from django.core.cache import cache
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

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
    ResourceNotFoundError,
    UseCaseError,
)
from apps.badges.models import TouristObject
from apps.badges.tasks import recalculate_poi_scores_task
from apps.tourists.models import TouristProfile
from bootstrap import get_container

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
    """Buduje odpowiedź RFC 7807 Problem Details."""
    return JsonResponse(
        {
            "type": f"https://api.pttk-badges.pl/errors/{error_type}",
            "title": title,
            "status": status,
            "detail": detail,
            "instance": request.path,
        },
        status=status,
    )


def _require_auth(request) -> JsonResponse | None:
    """Guard: zwraca 401 jeśli użytkownik nie jest zalogowany."""
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
    """
    if isinstance(exc, ResourceNotFoundError):
        return _problem_detail(request, "resource-not-found", "Zasób nie istnieje", 404, str(exc))

    if isinstance(exc, ConflictError):
        return _problem_detail(request, "conflict", "Konflikt Danych", 409, str(exc))

    if isinstance(exc, BitemporalTimeError):
        return _problem_detail(request, "bitemporal-constraint-violated", "Naruszenie Bitemporalności", 422, str(exc))

    if isinstance(exc, UseCaseError):
        return _problem_detail(request, "validation-failed", "Błąd Walidacji", 422, str(exc))

    # Fallback dla nieznanych podklas ApplicationException
    return _problem_detail(request, "internal-error", "Wewnętrzny Błąd Serwera", 500, str(exc))


# ---------------------------------------------------------------------------
# Widoki
# ---------------------------------------------------------------------------


class AscentLogView(View):
    """POST /api/v1/ascents/

    Rejestruje wejście turysty na obiekt turystyczny.

    Request body (JSON):
        peak_id (int): ID obiektu turystycznego
        ascent_date (str): Data wejścia w formacie YYYY-MM-DD

    Returns:
        201: {"ascent_id": int}
        401: RFC 7807 — brak autentykacji
        409: RFC 7807 — duplikat wejścia (D-04)
        422: RFC 7807 — naruszenie bitemporalności (T-01) lub data z przyszłości (T-03)
    """

    def post(self, request: Any) -> JsonResponse:
        """Rejestruje nowe wejście na szczyt (US-C03)."""
        auth_error = _require_auth(request)
        if auth_error:
            return auth_error

        profile_id = request.session.get("active_profile_id") or request.user.profiles.first().id

        try:
            body = json.loads(request.body)
            ascent_input = AscentInputDTO(**body)
        except (json.JSONDecodeError, ValueError) as e:
            return _problem_detail(
                request=request,
                error_type="validation-error",
                title="Błąd Walidacji Danych Wejściowych",
                status=422,
                detail=str(e),
            )

        try:
            use_case = get_container().log_ascent

            # WPISUJEMY TYLKO TO (UoW i Event Publisher są zaszyte w środku!)
            ascent_id = use_case.execute(profile_id=profile_id, dto=ascent_input)

            return JsonResponse({"ascent_id": ascent_id, "status": "CREATED"}, status=201)

        except ApplicationException as exc:
            return _handle_application_exception(exc, request.path)


class BadgeSubscribeView(View):
    """POST /api/v1/badges/{badge_code}/subscribe/

    Rozpoczyna zdobywanie odznaki (subskrypcja + zakotwiczenie Praw Nabytych).

    Returns:
        201: {"progress_id": int, "status": "SUBSCRIBED"}
        401: RFC 7807 — brak autentykacji
        422: RFC 7807 — brak regulaminu dla daty zakotwiczenia
    """

    def post(self, request: Any, badge_code: str) -> JsonResponse:
        """Rozpoczyna zdobywanie nowej odznaki i zakotwicza regulamin (US-C05)."""
        auth_error = _require_auth(request)
        if auth_error:
            return auth_error

        profile_id = request.session.get("active_profile_id") or request.user.profiles.first().id

        try:
            use_case = get_container().start_badge_progress

            # WPISUJEMY TYLKO TO:
            progress_id = use_case.execute(profile_id=profile_id, badge_code=badge_code)

            return JsonResponse({"progress_id": progress_id, "status": "SUBSCRIBED"}, status=201)

        except ApplicationException as exc:
            return _handle_application_exception(exc, request.path)

    def delete(self, request, badge_code: str):
        auth_error = _require_auth(request)
        if auth_error:
            return auth_error

        profile_id = request.session.get("active_profile_id") or request.user.profiles.first().id

        try:
            use_case = get_container().unsubscribe_badge
            use_case.execute(profile_id=profile_id, badge_code=badge_code)

            return JsonResponse({"status": "UNSUBSCRIBED"}, status=200)

        except ApplicationException as exc:
            return _handle_application_exception(exc, request.path)


class BadgeProgressView(View):
    """GET /api/v1/badges/{badge_code}/progress/

    Oblicza i zwraca aktualny postęp turysty w zdobywaniu odznaki (On-Demand).

    Query params:
        cycle (int, optional): Numer cyklu, domyślnie 1

    Returns:
        200: słownik z wynikiem ewaluacji domenowej
        401: RFC 7807 — brak autentykacji
        404: RFC 7807 — turysta nie subskrybuje odznaki
    """

    def get(self, request, badge_code: str):
        auth_error = _require_auth(request)
        if auth_error:
            return auth_error

        cycle_number = int(request.GET.get("cycle", 1))

        # Nie potrzebujemy tu w ogóle obiektu DTO (skoro UseCase przyjmuje proste parametry!)
        # Wyciągamy po prostu bezpiecznie profile_id z sesji (Ochrona IDOR z AUDYT-070)
        profile_id = request.session.get("active_profile_id") or request.user.profiles.first().id

        try:
            use_case = get_container().evaluate_badge_progress
            result = use_case.execute(profile_id=profile_id, badge_code=badge_code, cycle_number=cycle_number)
        except ApplicationException as exc:
            return _handle_application_exception(request, exc)

        return JsonResponse(result, status=200)


class MapObjectsView(View):
    """GET /api/v1/map/objects?bbox={min_lon,min_lat,max_lon,max_lat}

    Zwraca GeoJSON z obiektami dla widocznego okna mapy (ADR-011).
    Kolory punktów odzwierciedlają postęp turysty (ADR-010).
    """

    def get(self, request):
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

        # Pobieramy profil bezpośrednio z sesji lub z relacji użytkownika
        profile_id = request.session.get("active_profile_id")
        if not profile_id:
            first_profile = request.user.profiles.first()
            profile_id = first_profile.id if first_profile else 0

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
        except Exception as e:
            return _problem_detail(request, "validation-failed", "Nieprawidłowe dane wejściowe", 422, str(e))

        try:
            use_case = get_container().explore_map
            geojson_data = use_case.execute(dto)
        except ApplicationException as exc:
            return _handle_application_exception(request, exc)

        return JsonResponse(geojson_data, status=200)


class BadgeLogisticsView(View):
    """PATCH /api/v1/progress/{progress_id}/logistics/

    Aktualizuje status logistyczny odznaki w Osobistym Trackerze Turysty.
    """

    def patch(self, request, progress_id: int):
        auth_error = _require_auth(request)
        if auth_error:
            return auth_error

        try:
            body = json.loads(request.body)
        except json.JSONDecodeError, ValueError:
            return _problem_detail(
                request, "validation-failed", "Nieprawidłowe dane", 422, "Ciało żądania musi być JSON."
            )

        try:
            dto = LogisticStatusUpdateDTO(**body)
        except Exception as e:
            return _problem_detail(request, "validation-failed", "Błąd Walidacji", 422, str(e))

        # SECURITY: Identyfikacja użytkownika zawsze z sesji
        profile_id = request.profile.id

        try:
            use_case = get_container().advance_logistic_status
            use_case.execute(
                profile_id=profile_id,
                progress_id=progress_id,
                new_logistic_status=dto.logistic_status,
                status_date=dto.status_date,
            )
        except ApplicationException as exc:
            return _handle_application_exception(request, exc)

        return JsonResponse({"status": "UPDATED", "logistic_status": dto.logistic_status}, status=200)


class VectorTileView(View):
    """GET /api/v1/tiles/{layer}/{z}/{x}/{y}.pbf

    Zwraca zbuforowane, skompresowane (GZIP) kafelki wektorowe.
    """

    def get(self, request, layer: str, z: int, x: int, y: int):
        try:
            use_case = get_container().get_mvt_tile
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
    """

    def get(self, request: HttpRequest, object_id: int) -> JsonResponse:
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
    """

    def post(self, request: HttpRequest) -> JsonResponse:
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

        file_content = gpx_file.read()

        try:
            use_case = get_container().analyze_gpx_track
            result = use_case.execute(file_content)
        except ApplicationException as exc:
            return _handle_application_exception(request, exc)

        return JsonResponse(result.model_dump(), status=200)


class BulkAscentLogView(View):
    """POST /api/v1/ascents/bulk/

    Masowy zapis logów (np. po akceptacji z GPX). Zwraca wynik częściowy.
    """

    def post(self, request: Any) -> JsonResponse:
        """Masowo rejestruje logi wejść z pliku GPX (US-C17)."""
        auth_error = _require_auth(request)
        if auth_error:
            return auth_error

        profile_id = request.session.get("active_profile_id") or request.user.profiles.first().id

        try:
            body = json.loads(request.body)
            if not isinstance(body, list):
                raise ValueError("Payload musi być listą obiektów JSON.")
            ascents = [AscentInputDTO(**item) for item in body]
        except (json.JSONDecodeError, ValueError) as e:
            return _problem_detail(
                request=request,
                error_type="validation-error",
                title="Błąd Walidacji Danych Wejściowych",
                status=422,
                detail=str(e),
            )
        try:
            use_case = get_container().bulk_log_ascents

            # WPISUJEMY TYLKO TO:
            result = use_case.execute(profile_id=profile_id, ascents=ascents)

            return JsonResponse(result, status=200)

        except ApplicationException as exc:
            return _handle_application_exception(exc, request.path)


class ProfileSettingsView(View):
    """PATCH /api/v1/profiles/{profile_id}/

    Aktualizuje ustawienia profilu (np. Wiek, Mapa). Posiada ochronę IDOR.
    """

    def patch(self, request, profile_id: int):
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
            # Puste stringi dla daty zamieniamy na None (czyszczenie wieku)
            if body.get("birth_date") == "":
                body["birth_date"] = None
            dto = UpdateProfileRequestDTO(**body)
        except Exception as e:
            return _problem_detail(request, "validation-failed", "Błąd Walidacji", 422, str(e))

        if dto.nickname:
            profile.nickname = dto.nickname
        if dto.birth_date is not None or "birth_date" in body:
            profile.birth_date = dto.birth_date
        if dto.preferred_base_map:
            profile.preferred_base_map = dto.preferred_base_map

        profile.save(update_fields=["nickname", "birth_date", "preferred_base_map"])
        return JsonResponse({"status": "UPDATED"}, status=200)


class ProfileUpgradeView(View):
    """POST /api/v1/profiles/{profile_id}/upgrade/

    Sztuczna bramka płatności (Wymusza pakiet PRO dla testów UX).
    """

    def post(self, request, profile_id: int):
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

        profile.active_plan = "PRO"
        profile.save(update_fields=["active_plan"])

        # Opcjonalne przeliczenie map w tle. Ponieważ to atrapa API i operacja jest
        # autocommited z ORM Django bez otwierania długiej transakcji, robimy to natychmiast:

        recalculate_poi_scores_task.delay(profile_id)

        return JsonResponse({"status": "UPGRADED"}, status=200)
