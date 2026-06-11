"""Widoki REST API dla obszaru Turysty (Faza C).

Warstwa HTTP jest cienką powłoką:
  - parsuje request i wyciąga user_id z sesji (nigdy z body)
  - wywołuje Use Case przez kontener DI
  - serializuje wynik lub błąd do RFC 7807 JSON
  - NIE zawiera logiki biznesowej

Obsługa wyjątków domenowych jest zaimplementowana bezpośrednio w widokach,
ponieważ RequestFactory (używany w testach) omija middleware.process_exception.
Middleware RFC7807ErrorMiddleware działa jako dodatkowe zabezpieczenie
dla nieoczekiwanych wyjątków w środowisku produkcyjnym.
"""

import json

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from application.dto.ascent_dto import AscentInputDTO
from application.dto.map_dto import MapExploreRequestDTO
from application.dto.verify_badge_dto import VerifyBadgeRequestDTO
from application.exceptions import (
    ApplicationException,
    BitemporalTimeError,
    ConflictError,
    ResourceNotFoundError,
    UseCaseError,
)
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


@method_decorator(csrf_exempt, name="dispatch")
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

    def post(self, request):
        auth_error = _require_auth(request)
        if auth_error:
            return auth_error

        try:
            body = json.loads(request.body)
        except json.JSONDecodeError, ValueError:  # <--- ZMIANA (nawiasy!)
            return _problem_detail(
                request,
                "validation-failed",
                "Nieprawidłowe dane wejściowe",
                422,
                "Ciało żądania musi być poprawnym dokumentem JSON.",
            )

        try:
            dto = AscentInputDTO(**body)
        except Exception as e:
            return _problem_detail(request, "validation-failed", "Nieprawidłowe dane wejściowe", 422, str(e))

        # SECURITY: user_id zawsze z sesji — nigdy z ciała żądania
        user_id = request.user.id

        try:
            use_case = get_container()["log_ascent"]
            ascent_id = use_case.execute(user_id=user_id, dto=dto)
        except ApplicationException as exc:
            return _handle_application_exception(request, exc)

        return JsonResponse({"ascent_id": ascent_id}, status=201)


@method_decorator(csrf_exempt, name="dispatch")
class BadgeSubscribeView(View):
    """POST /api/v1/badges/{badge_code}/subscribe/

    Rozpoczyna zdobywanie odznaki (subskrypcja + zakotwiczenie Praw Nabytych).

    Returns:
        201: {"progress_id": int, "status": "SUBSCRIBED"}
        401: RFC 7807 — brak autentykacji
        422: RFC 7807 — brak regulaminu dla daty zakotwiczenia
    """

    def post(self, request, badge_code: str):
        auth_error = _require_auth(request)
        if auth_error:
            return auth_error

        try:
            use_case = get_container()["start_badge_progress"]
            progress_id = use_case.execute(user_id=request.user.id, badge_code=badge_code)
        except ApplicationException as exc:
            return _handle_application_exception(request, exc)

        return JsonResponse({"progress_id": progress_id, "status": "SUBSCRIBED"}, status=201)


@method_decorator(csrf_exempt, name="dispatch")
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

        dto = VerifyBadgeRequestDTO(
            user_id=request.user.id,
            badge_code=badge_code,
            cycle_number=cycle_number,
        )

        try:
            use_case = get_container()["verify_badge"]
            result = use_case.execute(dto)
        except ApplicationException as exc:
            return _handle_application_exception(request, exc)

        return JsonResponse(result, status=200)


@method_decorator(csrf_exempt, name="dispatch")
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

        try:
            dto = MapExploreRequestDTO(
                user_id=request.user.id,
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
            use_case = get_container()["explore_map"]
            geojson_data = use_case.execute(dto)
        except ApplicationException as exc:
            return _handle_application_exception(request, exc)

        return JsonResponse(geojson_data, status=200)
