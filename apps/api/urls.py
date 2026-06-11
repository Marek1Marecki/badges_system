"""Routing URL dla obszaru API (apps/api/urls.py).

Rejestracja w głównym urls.py projektu:
    path("api/v1/", include("apps.api.urls", namespace="api")),
"""

from django.urls import path

from apps.api.views import AscentLogView, BadgeProgressView, BadgeSubscribeView, MapObjectsView

app_name = "api"

urlpatterns = [
    # Logi wejść
    path("v1/ascents/", AscentLogView.as_view(), name="ascents"),
    # Odznaki
    path("v1/badges/<str:badge_code>/subscribe/", BadgeSubscribeView.as_view(), name="badge_subscribe"),
    path("v1/badges/<str:badge_code>/progress/", BadgeProgressView.as_view(), name="badge_progress"),
    path("v1/map/objects", MapObjectsView.as_view(), name="map_objects"),
]
