"""Tests for API URL configuration."""

from django.test import SimpleTestCase
from django.urls import resolve, reverse

from apps.api.views import (
    AscentLogView,
    BadgeLogisticsView,
    BadgeProgressView,
    BadgeSubscribeView,
    MapObjectsView,
    NearbyObjectsView,
    VectorTileView,
)


class TestApiUrls(SimpleTestCase):
    """Test suite for API URL routing."""

    def test_ascents_url_resolves(self):
        """Test that ascents URL resolves to AscentLogView."""
        url = reverse("api:ascents")
        assert resolve(url).func.view_class == AscentLogView

    def test_badge_subscribe_url_resolves(self):
        """Test that badge subscribe URL resolves to BadgeSubscribeView."""
        url = reverse("api:badge_subscribe", kwargs={"badge_code": "test-badge"})
        assert resolve(url).func.view_class == BadgeSubscribeView

    def test_badge_progress_url_resolves(self):
        """Test that badge progress URL resolves to BadgeProgressView."""
        url = reverse("api:badge_progress", kwargs={"badge_code": "test-badge"})
        assert resolve(url).func.view_class == BadgeProgressView

    def test_map_objects_url_resolves(self):
        """Test that map objects URL resolves to MapObjectsView."""
        url = reverse("api:map_objects")
        assert resolve(url).func.view_class == MapObjectsView

    def test_badge_logistics_url_resolves(self):
        """Test that badge logistics URL resolves to BadgeLogisticsView."""
        url = reverse("api:badge_logistics", kwargs={"progress_id": 1})
        assert resolve(url).func.view_class == BadgeLogisticsView

    def test_vector_tiles_url_resolves(self):
        """Test that vector tiles URL resolves to VectorTileView."""
        url = reverse("api:vector_tiles", kwargs={"layer": "peaks", "z": 10, "x": 100, "y": 200})
        assert resolve(url).func.view_class == VectorTileView

    def test_nearby_objects_url_resolves(self):
        """Test that nearby objects URL resolves to NearbyObjectsView."""
        url = reverse("api:nearby_objects", kwargs={"object_id": 1})
        assert resolve(url).func.view_class == NearbyObjectsView
