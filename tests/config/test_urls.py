"""Tests for main URL configuration."""

from django.test import SimpleTestCase
from django.urls import resolve, reverse


class TestMainUrls(SimpleTestCase):
    """Test suite for main URL routing."""

    def test_home_url_resolves(self):
        """Test that home URL resolves to dashboard_view."""
        url = reverse("home")
        assert resolve(url).func.__name__ == "dashboard_view"

    def test_catalog_url_resolves(self):
        """Test that catalog URL resolves to badge_catalog_view."""
        url = reverse("catalog")
        assert resolve(url).func.__name__ == "badge_catalog_view"

    def test_profile_url_resolves(self):
        """Test that profile URL resolves to profile_settings_view."""
        url = reverse("profile")
        assert resolve(url).func.__name__ == "profile_settings_view"

    def test_ranking_url_resolves(self):
        """Test that ranking URL resolves to poi_ranking_view."""
        url = reverse("ranking")
        assert resolve(url).func.__name__ == "poi_ranking_view"

    def test_object_detail_url_resolves(self):
        """Test that object detail URL resolves to object_detail_view."""
        url = reverse("object_detail", kwargs={"object_id": 1})
        assert resolve(url).func.__name__ == "object_detail_view"

    def test_badge_detail_url_resolves(self):
        """Test that badge detail URL resolves to badge_detail_view."""
        url = reverse("badge_detail", kwargs={"badge_code": "test-badge"})
        assert resolve(url).func.__name__ == "badge_detail_view"

    def test_region_ranking_url_resolves(self):
        """Test that region ranking URL resolves to region_ranking_view."""
        url = reverse("region_ranking")
        assert resolve(url).func.__name__ == "region_ranking_view"

    def test_organizer_detail_url_resolves(self):
        """Test that organizer detail URL resolves to organizer_detail_view."""
        url = reverse("organizer_detail", kwargs={"organizer_id": 1})
        assert resolve(url).func.__name__ == "organizer_detail_view"

    def test_health_check_view(self):
        """Test that health check view returns 200 OK."""
        response = self.client.get("/health/")
        assert response.status_code == 200
        assert response.content == b"OK"
