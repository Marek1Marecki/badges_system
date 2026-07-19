from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path

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


def health_check(request):
    """Zwraca natychmiastowe 200 OK dla Docker Healthcheck/Load Balancer."""
    return HttpResponse("OK")


urlpatterns = [
    # --- INFRASTRUKTURA I API ---
    path("health/", health_check, name="health_check"),
    path("admin/", admin.site.urls),
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
