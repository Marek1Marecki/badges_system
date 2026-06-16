"""Routing URL dla obszaru API (apps/api/urls.py).

Rejestracja w głównym urls.py projektu:
    path("api/v1/", include("apps.api.urls", namespace="api")),
"""

from django.urls import path

from apps.api.views import (
    AscentLogView,
    BadgeLogisticsView,
    BadgeProgressView,
    BadgeSubscribeView,
    BulkAscentLogView,
    GpxAnalyzeView,
    MapObjectsView,
    NearbyObjectsView,
    VectorTileView,
)

app_name = "api"

urlpatterns = [
    # Logi wejść
    path("v1/ascents/", AscentLogView.as_view(), name="ascents"),
    path("v1/ascents/bulk/", BulkAscentLogView.as_view(), name="ascents_bulk"),  # <--- DODANE
    path("v1/gpx/analyze/", GpxAnalyzeView.as_view(), name="gpx_analyze"),  # <--- DODANE
    # Odznaki
    path("v1/badges/<str:badge_code>/subscribe/", BadgeSubscribeView.as_view(), name="badge_subscribe"),
    path("v1/badges/<str:badge_code>/progress/", BadgeProgressView.as_view(), name="badge_progress"),
    path("v1/map/objects/", MapObjectsView.as_view(), name="map_objects"),
    path("v1/progress/<int:progress_id>/logistics/", BadgeLogisticsView.as_view(), name="badge_logistics"),
    path("v1/tiles/<str:layer>/<int:z>/<int:x>/<int:y>.pbf", VectorTileView.as_view(), name="vector_tiles"),
    path("v1/objects/<int:object_id>/nearby/", NearbyObjectsView.as_view(), name="nearby_objects"),
]
