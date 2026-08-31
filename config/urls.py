from django.conf import settings
from django.contrib import admin
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.urls import include, path
from django.views.decorators.http import require_GET

import logging

from django.db import connection
from django.core.cache import cache

from apps.tourists.views import (
    badge_catalog_view,
    badge_detail_view,
    dashboard_view,
    logistics_view,
    object_detail_view,
    organizer_detail_view,
    poi_ranking_view,
    profile_settings_view,
    region_detail_view,
    region_ranking_view,
    switch_profile_view,
)

logger = logging.getLogger(__name__)


def health_check(request):
    """Zwraca status zdrowia aplikacji (liveness + readiness).

    Endpoint używany przez Docker Healthcheck i Load Balancer.
    Sprawdza połączenie z bazą danych i Redisem.
    """
    if settings.APP_ENV == "test":
        return JsonResponse({"status": "healthy", "checks": {"database": "skipped", "redis": "skipped"}})

    checks = {}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "healthy"
    except Exception as exc:  # noqa: BLE001
        logger.error("Database health check failed", exc_info=True)
        checks["database"] = "unhealthy"

    try:
        cache.set("healthcheck", "ok", timeout=1)
        if cache.get("healthcheck") != "ok":
            raise RuntimeError("Redis cache readback mismatch")
        checks["redis"] = "healthy"
    except Exception as exc:  # noqa: BLE001
        logger.error("Redis health check failed", exc_info=True)
        checks["redis"] = "unhealthy"

    if any("unhealthy" in str(v) for v in checks.values()):
        return JsonResponse({"status": "unhealthy", "checks": checks}, status=503)

    return JsonResponse({"status": "healthy", "checks": checks})


@require_GET
def openapi_schema(request):
    """Zwraca statyczny schemat OpenAPI dla Schemathesis."""
    from pathlib import Path

    schema_path = Path(__file__).resolve().parent / "openapi.json"
    return HttpResponse(schema_path.read_text(encoding="utf-8"), content_type="application/json")


urlpatterns = [
    # --- INFRASTRUKTURA I API ---
    path("health/", health_check, name="health_check"),
    path("admin/", admin.site.urls),
    path("api/openapi.json", openapi_schema, name="openapi_schema"),
    path("api/", include("apps.api.urls")),
    path("accounts/", include("allauth.urls")),
    # --- WIDOKI HTML TURYSTY (Faza C) ---
    path("", dashboard_view, name="home"),
    path("catalog/", badge_catalog_view, name="catalog"),
    path("profile/", profile_settings_view, name="profile"),
    path("profile/switch/<int:profile_id>/", switch_profile_view, name="switch_profile"),
    path("ranking/", poi_ranking_view, name="ranking"),
    path("ranking/regions/", region_ranking_view, name="region_ranking"),
    path("logistics/", logistics_view, name="logistics"),
    path("object/<int:object_id>/", object_detail_view, name="object_detail"),
    path("badge/<str:badge_code>/", badge_detail_view, name="badge_detail"),
    path("organizer/<int:organizer_id>/", organizer_detail_view, name="organizer_detail"),
    path("region/<str:region_level>/<int:region_id>/", region_detail_view, name="region_detail"),
]

