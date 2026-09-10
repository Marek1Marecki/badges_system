"""Testy kontrlera dla endpointu odrzucania wejść (AUDYT-089 — Czarna Lista).

Testy nie wymagają DB — mockujemy model AscentLog i request.session.
View używa request.app_container (ContainerMiddleware) dla innych endpointów,
ale AscentLogRejectView nie korzysta z use_cases — operuje bezpośrednio na modelu.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

TEST_TODAY = "2024-01-15"


@pytest.fixture
def factory():
    """RequestFactory z automatycznym wstrzykiem session i app_container."""
    from django.test import RequestFactory

    class SessionRequestFactory(RequestFactory):
        def generic(self, *args, **kwargs):
            req = super().generic(*args, **kwargs)
            req.session = {}
            return req

    return SessionRequestFactory()


@pytest.fixture
def mock_user():
    """Fake authenticated user — bez zapisu do bazy."""
    user = MagicMock()
    user.is_authenticated = True
    user.id = 1
    user.username = "turysta"

    mock_profile = MagicMock()
    mock_profile.id = 1
    user.profiles.first.return_value = mock_profile

    return user


class TestAscentLogRejectView:
    """Testy endpointu PATCH /ascents/{id}/reject/ (AUDYT-089 — Czarna Lista)."""

    def test_reject_unauthenticated_returns_401(self, factory) -> None:
        """Unauthenticated request returns 401 (RFC 7807)."""
        from apps.api.views import AscentLogRejectView

        request = factory.patch("/api/v1/ascents/42/reject/")
        request.user = MagicMock()
        request.user.is_authenticated = False
        request.session = {}

        response = AscentLogRejectView.as_view()(request, ascent_id=42)

        assert response.status_code == 401
        data = json.loads(response.content)
        assert "authentication-required" in data["type"]

    def test_reject_returns_200_with_ascent_id(self, factory, mock_user) -> None:
        """PATCH /ascents/{id}/reject/ flags the log as is_rejected=True."""
        from apps.api.views import AscentLogRejectView

        mock_ascent = MagicMock()
        mock_ascent.id = 42

        with patch("apps.tourists.models.AscentLog") as MockAscentLog:
            MockAscentLog.objects.select_related.return_value.get.return_value = mock_ascent
            request = factory.patch("/api/v1/ascents/42/reject/")
            request.user = mock_user
            request.session = {"active_profile_id": 1}

            response = AscentLogRejectView.as_view()(request, ascent_id=42)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["status"] == "REJECTED"
        assert data["ascent_id"] == 42
        mock_ascent.save.assert_called_once_with(update_fields=["is_rejected"])

    def test_reject_not_found_returns_404(self, factory, mock_user) -> None:
        """If the log does not exist, returns 404 (RFC 7807)."""
        from apps.api.views import AscentLogRejectView

        class FakeDoesNotExist(Exception):
            pass

        with patch("apps.tourists.models.AscentLog") as MockAscentLog:
            MockAscentLog.DoesNotExist = FakeDoesNotExist
            MockAscentLog.objects.select_related.return_value.get.side_effect = FakeDoesNotExist("not found")
            request = factory.patch("/api/v1/ascents/999/reject/")
            request.user = mock_user
            request.session = {}

            response = AscentLogRejectView.as_view()(request, ascent_id=999)

        assert response.status_code == 404
        data = json.loads(response.content)
        assert "request_id" in data


class TestBadgeLogisticsAuth:
    """Testy bezpieczeństwa dla BadgeLogisticsView — bez DB."""

    def test_logistics_unauthenticated_returns_401(self, factory) -> None:
        """Unauthenticated PATCH returns 401 (RFC 7807)."""
        from apps.api.views import BadgeLogisticsView

        request = factory.patch("/api/v1/progress/1/logistics/")
        request.user = MagicMock()
        request.user.is_authenticated = False
        request.session = {}
        request.app_container = MagicMock()

        response = BadgeLogisticsView.as_view()(request, progress_id=1)

        assert response.status_code == 401
        data = json.loads(response.content)
        assert "authentication-required" in data["type"]

    def test_logistics_invalid_json_returns_422(self, factory, mock_user) -> None:
        """Invalid JSON body returns 422 (RFC 7807)."""
        from apps.api.views import BadgeLogisticsView

        request = factory.patch(
            "/api/v1/progress/1/logistics/",
            data="not-json",
            content_type="application/json",
        )
        request.user = mock_user
        request.session = {}
        request.app_container = MagicMock()

        response = BadgeLogisticsView.as_view()(request, progress_id=1)

        assert response.status_code == 422

    def test_logistics_invalid_dto_returns_422(self, factory, mock_user) -> None:
        """Invalid logistic status DTO returns 422 (RFC 7807)."""
        from apps.api.views import BadgeLogisticsView

        request = factory.patch(
            "/api/v1/progress/1/logistics/",
            data=json.dumps({"invalid_field": "bad"}),
            content_type="application/json",
        )
        request.user = mock_user
        request.session = {}
        request.app_container = MagicMock()

        response = BadgeLogisticsView.as_view()(request, progress_id=1)

        assert response.status_code == 422


class TestBadgeVersionSwitchAuth:
    """Testy autoryzacji dla BadgeVersionSwitchView — bez DB."""

    def test_version_switch_unauthenticated_returns_401(self, factory) -> None:
        """Unauthenticated POST returns 401."""
        from apps.api.views import BadgeVersionSwitchView

        request = factory.patch(
            "/api/v1/progress/1/switch_version/", data=json.dumps({}), content_type="application/json"
        )
        request.user = MagicMock()
        request.user.is_authenticated = False
        request.session = {}
        request.app_container = MagicMock()

        response = BadgeVersionSwitchView.as_view()(request, progress_id=1)

        assert response.status_code == 401

    def test_version_switch_invalid_json_returns_422(self, factory, mock_user) -> None:
        """Invalid JSON body returns 422."""
        from apps.api.views import BadgeVersionSwitchView

        request = factory.patch("/api/v1/progress/1/switch_version/", data="not-json", content_type="application/json")
        request.user = mock_user
        request.session = {}
        request.app_container = MagicMock()

        response = BadgeVersionSwitchView.as_view()(request, progress_id=1)

        assert response.status_code == 422


class TestMapObjectsAuth:
    """Testy bezpieczeństwa dla MapObjectsView — bez DB (validation paths)."""

    def test_map_objects_missing_bbox_returns_422(self, factory, mock_user) -> None:
        """Missing bbox parameter returns 422 validation error."""
        from apps.api.views import MapObjectsView

        request = factory.get("/api/v1/map/objects/")
        request.user = mock_user
        request.session = {}
        request.app_container = MagicMock()

        response = MapObjectsView.as_view()(request)

        assert response.status_code == 422

    def test_map_objects_invalid_bbox_returns_422(self, factory, mock_user) -> None:
        """Invalid bbox format returns 422 validation error."""
        from apps.api.views import MapObjectsView

        request = factory.get("/api/v1/map/objects/?bbox=invalid")
        request.user = mock_user
        request.session = {}
        request.app_container = MagicMock()

        response = MapObjectsView.as_view()(request)

        assert response.status_code == 422


class TestBadgeProgressAuth:
    """Testy autoryzacji dla BadgeProgressView — bez DB (validation paths)."""

    def test_progress_unauthenticated_returns_401(self, factory) -> None:
        """Unauthenticated GET returns 401."""
        from apps.api.views import BadgeProgressView

        request = factory.get("/api/v1/badges/KGP/progress/")
        request.user = MagicMock()
        request.user.is_authenticated = False
        request.session = {}
        request.app_container = MagicMock()

        response = BadgeProgressView.as_view()(request, badge_code="KGP")

        assert response.status_code == 401

    def test_progress_invalid_cycle_returns_422(self, factory, mock_user) -> None:
        """Invalid cycle parameter returns 422."""
        from apps.api.views import BadgeProgressView

        request = factory.get("/api/v1/badges/KGP/progress/?cycle=abc")
        request.user = mock_user
        request.session = {}
        request.app_container = MagicMock()

        response = BadgeProgressView.as_view()(request, badge_code="KGP")

        assert response.status_code == 422
