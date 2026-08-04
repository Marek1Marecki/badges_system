"""Testy integracyjne dla REST API turysty (Faza C).

Strategia: RequestFactory + MagicMock user + patch na get_container.
"""

import json
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


class UseCaseContainer:
    def __init__(self, cases: dict):
        self._cases = dict(cases)
        for key, value in self._cases.items():
            setattr(self, key, value)

    def __getitem__(self, key):
        return self._cases[key]

    def __setitem__(self, key, value):
        self._cases[key] = value
        setattr(self, key, value)


# ZMIANA: Zezwalamy na dostęp do bazy dla transaction.on_commit
pytestmark = [pytest.mark.integration, pytest.mark.django_db]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def factory():
    from django.test import RequestFactory

    class SessionRequestFactory(RequestFactory):
        def generic(self, *args, **kwargs):
            req = super().generic(*args, **kwargs)
            # Wstrzyknięcie sesji, której RequestFactory domyślnie nie posiada
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

    # Zmockowanie zachowania konta rodzinnego: request.user.profiles.first().id
    mock_profile = MagicMock()
    mock_profile.id = 1
    user.profiles.first.return_value = mock_profile

    return user


@pytest.fixture
def use_cases():
    """Zwraca kontener mocków Use Case'ów i patch na get_container."""
    cases = {
        "log_ascent": MagicMock(),
        "start_badge_progress": MagicMock(),
        "verify_badge": MagicMock(),
        "explore_map": MagicMock(),
        "advance_logistic_status": MagicMock(),
        "unsubscribe_badge": MagicMock(),
        "get_mvt_tile": MagicMock(),
        "evaluate_badge_progress": MagicMock(),
        "bulk_log_ascents": MagicMock(),
        "analyze_gpx_track": MagicMock(),
    }
    container = UseCaseContainer(cases)
    with patch("apps.api.views.get_container", return_value=container):
        yield container


# ---------------------------------------------------------------------------
# AscentLogView — POST /api/v1/ascents/
# ---------------------------------------------------------------------------


class TestAscentLogView:
    def test_created_returns_201_with_ascent_id(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import AscentLogView

        use_cases["log_ascent"].execute.return_value = 77

        request = factory.post(
            "/api/v1/ascents/",
            data=json.dumps({"peak_id": 15, "ascent_date": str(date.today())}),
            content_type="application/json",
        )
        request.user = mock_user

        response = AscentLogView.as_view()(request)

        assert response.status_code == 201
        assert json.loads(response.content)["ascent_id"] == 77

    def test_profile_id_from_session_not_body(self, factory, mock_user, use_cases) -> None:
        """SECURITY: profile_id musi pochodzić z autoryzacji, a nie z payloadu."""
        from apps.api.views import AscentLogView

        use_cases["log_ascent"].execute.return_value = 1

        request = factory.post(
            "/api/v1/ascents/",
            data=json.dumps({"peak_id": 15, "ascent_date": str(date.today()), "profile_id": 999}),
            content_type="application/json",
        )
        request.user = mock_user

        AscentLogView.as_view()(request)

        call_kwargs = use_cases["log_ascent"].execute.call_args
        assert call_kwargs.kwargs["profile_id"] == 1

    def test_conflict_error_returns_409_rfc7807(self, factory, mock_user, use_cases) -> None:
        from application.exceptions import ConflictError
        from apps.api.views import AscentLogView

        use_cases["log_ascent"].execute.side_effect = ConflictError("Wejście jest duplikatem")

        request = factory.post(
            "/api/v1/ascents/",
            data=json.dumps({"peak_id": 15, "ascent_date": str(date.today())}),
            content_type="application/json",
        )
        request.user = mock_user

        response = AscentLogView.as_view()(request)

        assert response.status_code == 409
        data = json.loads(response.content)
        assert data["status"] == 409
        assert "duplikatem" in data["detail"]

    def test_bitemporal_error_returns_422(self, factory, mock_user, use_cases) -> None:
        from application.exceptions import BitemporalTimeError
        from apps.api.views import AscentLogView

        use_cases["log_ascent"].execute.side_effect = BitemporalTimeError("Błąd")

        request = factory.post(
            "/api/v1/ascents/",
            data=json.dumps({"peak_id": 15, "ascent_date": "1800-01-01"}),
            content_type="application/json",
        )
        request.user = mock_user

        response = AscentLogView.as_view()(request)

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# BadgeSubscribeView — POST /api/v1/badges/{badge_code}/subscribe/
# ---------------------------------------------------------------------------


class TestBadgeSubscribeView:
    def test_subscribe_returns_201_with_progress_id(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import BadgeSubscribeView

        use_cases["start_badge_progress"].execute.return_value = 99

        request = factory.post("/api/v1/badges/KGP/subscribe/")
        request.user = mock_user

        response = BadgeSubscribeView.as_view()(request, badge_code="KGP")

        assert response.status_code == 201
        assert json.loads(response.content)["progress_id"] == 99

    def test_subscribe_calls_use_case_with_correct_args(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import BadgeSubscribeView

        use_cases["start_badge_progress"].execute.return_value = 1

        request = factory.post("/api/v1/badges/KGP/subscribe/")
        request.user = mock_user

        BadgeSubscribeView.as_view()(request, badge_code="KGP")

        use_cases["start_badge_progress"].execute.assert_called_once_with(profile_id=1, badge_code="KGP")


# ---------------------------------------------------------------------------
# BadgeProgressView — GET /api/v1/badges/{badge_code}/progress/
# ---------------------------------------------------------------------------


class TestBadgeProgressView:
    def test_progress_200_returns_evaluation_result(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import BadgeProgressView

        use_cases["verify_badge"].execute.return_value = {
            "verified": False,
            "status": "IN_PROGRESS",
            "errors": [],
            "valid_ascents_count": 12,
        }

        request = factory.get("/api/v1/badges/KGP/progress/")
        request.user = mock_user

        response = BadgeProgressView.as_view()(request, badge_code="KGP")

        assert response.status_code == 200
        assert json.loads(response.content)["valid_ascents_count"] == 12

    def test_not_subscribed_returns_404_rfc7807(self, factory, mock_user, use_cases) -> None:
        from application.exceptions import ResourceNotFoundError
        from apps.api.views import BadgeProgressView

        use_cases["verify_badge"].execute.side_effect = ResourceNotFoundError("Nie subskrybuje")

        request = factory.get("/api/v1/badges/KGP/progress/")
        request.user = mock_user

        response = BadgeProgressView.as_view()(request, badge_code="KGP")

        assert response.status_code == 404
        assert json.loads(response.content)["status"] == 404


# ---------------------------------------------------------------------------
# BadgeLogisticsView — PATCH /api/v1/progress/{progress_id}/logistics/
# ---------------------------------------------------------------------------


class TestBadgeLogisticsView:
    def test_patch_returns_200_on_success(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import BadgeLogisticsView

        use_cases["advance_logistic_status"].execute.return_value = None

        request = factory.patch(
            "/api/v1/progress/1/logistics/",
            data=json.dumps({"logistic_status": "WAITING_FOR_VERIFICATION", "status_date": str(date.today())}),
            content_type="application/json",
        )
        request.user = mock_user

        response = BadgeLogisticsView.as_view()(request, progress_id=1)

        assert response.status_code == 200
        assert json.loads(response.content)["status"] == "UPDATED"

    def test_patch_conflict_returns_409(self, factory, mock_user, use_cases) -> None:
        from application.exceptions import ConflictError
        from apps.api.views import BadgeLogisticsView

        use_cases["advance_logistic_status"].execute.side_effect = ConflictError("Niedozwolone przejście")

        request = factory.patch(
            "/api/v1/progress/1/logistics/",
            data=json.dumps({"logistic_status": "ALBUM", "status_date": str(date.today())}),
            content_type="application/json",
        )
        request.user = mock_user

        response = BadgeLogisticsView.as_view()(request, progress_id=1)

        assert response.status_code == 409


# ---------------------------------------------------------------------------
# MapObjectsView — GET /api/v1/map/objects
# ---------------------------------------------------------------------------


class TestMapObjectsView:
    def test_returns_geojson_for_valid_bbox(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import MapObjectsView

        use_cases["explore_map"].execute.return_value = {"type": "FeatureCollection", "features": []}

        request = factory.get("/api/v1/map/objects/?bbox=10,20,30,40")
        request.user = mock_user

        response = MapObjectsView.as_view()(request)

        assert response.status_code == 200

    def test_returns_422_for_missing_bbox(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import MapObjectsView

        request = factory.get("/api/v1/map/objects/")
        request.user = mock_user

        response = MapObjectsView.as_view()(request)

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# VectorTileView — GET /api/v1/tiles/{layer}/{z}/{x}/{y}.pbf
# ---------------------------------------------------------------------------


class TestVectorTileView:
    def test_returns_tile_data(self, factory, use_cases) -> None:
        from apps.api.views import VectorTileView

        use_cases["get_mvt_tile"] = MagicMock()
        use_cases["get_mvt_tile"].execute.return_value = b"tile_data"

        request = factory.get("/api/v1/tiles/country/5/10/15.pbf")

        response = VectorTileView.as_view()(request, layer="country", z=5, x=10, y=15)

        assert response.status_code == 200

    def test_returns_204_for_empty_tile(self, factory, use_cases) -> None:
        from apps.api.views import VectorTileView

        use_cases["get_mvt_tile"] = MagicMock()
        use_cases["get_mvt_tile"].execute.return_value = None

        request = factory.get("/api/v1/tiles/country/5/10/15.pbf")

        response = VectorTileView.as_view()(request, layer="country", z=5, x=10, y=15)

        assert response.status_code == 204


# ---------------------------------------------------------------------------
# ProfileSettingsView — PATCH /api/v1/profiles/{profile_id}/
# ---------------------------------------------------------------------------


class TestProfileSettingsView:
    def test_updates_profile_settings(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import ProfileSettingsView
        from apps.tourists.models import TouristProfile

        mock_profile = MagicMock(spec=TouristProfile)
        mock_profile.user = mock_user
        mock_profile.nickname = "old_nick"
        mock_profile.birth_date = None
        mock_profile.preferred_base_map = "osm"

        with patch("apps.api.views.get_object_or_404", return_value=mock_profile):
            request = factory.patch(
                "/api/v1/profiles/1/",
                data=json.dumps({"nickname": "new_nick", "preferred_base_map": "satellite"}),
                content_type="application/json",
            )
            request.user = mock_user

            response = ProfileSettingsView.as_view()(request, profile_id=1)

            assert response.status_code == 200
            mock_profile.save.assert_called_once()

    def test_clears_birth_date_on_empty_string(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import ProfileSettingsView
        from apps.tourists.models import TouristProfile

        mock_profile = MagicMock(spec=TouristProfile)
        mock_profile.user = mock_user

        with patch("apps.api.views.get_object_or_404", return_value=mock_profile):
            request = factory.patch(
                "/api/v1/profiles/1/",
                data=json.dumps({"birth_date": ""}),
                content_type="application/json",
            )
            request.user = mock_user

            response = ProfileSettingsView.as_view()(request, profile_id=1)

            assert response.status_code == 200
            assert mock_profile.birth_date is None


# ---------------------------------------------------------------------------
# BadgeSubscribeView — DELETE /api/v1/badges/{badge_code}/subscribe/
# ---------------------------------------------------------------------------


class TestBadgeUnsubscribeView:
    def test_unsubscribe_returns_200(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import BadgeSubscribeView

        use_cases["unsubscribe_badge"] = MagicMock()

        request = factory.delete("/api/v1/badges/KGP/subscribe/")
        request.user = mock_user

        response = BadgeSubscribeView.as_view()(request, badge_code="KGP")

        assert response.status_code == 200
        use_cases["unsubscribe_badge"].execute.assert_called_once_with(profile_id=1, badge_code="KGP")

    def test_unsubscribe_handles_conflict_error(self, factory, mock_user, use_cases) -> None:
        from application.exceptions import ConflictError
        from apps.api.views import BadgeSubscribeView

        use_cases["unsubscribe_badge"] = MagicMock()
        use_cases["unsubscribe_badge"].execute.side_effect = ConflictError("Cannot unsubscribe")

        request = factory.delete("/api/v1/badges/KGP/subscribe/")
        request.user = mock_user

        response = BadgeSubscribeView.as_view()(request, badge_code="KGP")

        assert response.status_code == 409


# ---------------------------------------------------------------------------
# GpxAnalyzeView — POST /api/v1/gpx/analyze/
# ---------------------------------------------------------------------------


class TestGpxAnalyzeView:
    def test_requires_authentication(self, factory, use_cases) -> None:
        from apps.api.views import GpxAnalyzeView

        request = factory.post("/api/v1/gpx/analyze/")
        request.user = MagicMock()
        request.user.is_authenticated = False

        response = GpxAnalyzeView.as_view()(request)

        assert response.status_code == 401

    def test_returns_422_when_no_file(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import GpxAnalyzeView

        request = factory.post("/api/v1/gpx/analyze/")
        request.user = mock_user

        response = GpxAnalyzeView.as_view()(request)

        assert response.status_code == 422

    def test_returns_422_when_file_too_large(self, factory, mock_user, use_cases) -> None:
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.api.views import GpxAnalyzeView

        large_content = b"x" * (11 * 1024 * 1024)
        mock_file = SimpleUploadedFile("test.gpx", large_content, content_type="application/gpx+xml")

        request = factory.post("/api/v1/gpx/analyze/", data={"file": mock_file})
        request.user = mock_user

        response = GpxAnalyzeView.as_view()(request)

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# BulkAscentLogView — POST /api/v1/ascents/bulk/
# ---------------------------------------------------------------------------


class TestBulkAscentLogView:
    def test_requires_authentication(self, factory, use_cases) -> None:
        from apps.api.views import BulkAscentLogView

        request = factory.post("/api/v1/ascents/bulk/")
        request.user = MagicMock()
        request.user.is_authenticated = False

        response = BulkAscentLogView.as_view()(request)

        assert response.status_code == 401

    def test_returns_422_for_invalid_json(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import BulkAscentLogView

        request = factory.post("/api/v1/ascents/bulk/", data="not json", content_type="application/json")
        request.user = mock_user

        response = BulkAscentLogView.as_view()(request)

        assert response.status_code == 422

    def test_returns_422_for_non_list_body(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import BulkAscentLogView

        request = factory.post(
            "/api/v1/ascents/bulk/", data=json.dumps({"not": "a list"}), content_type="application/json"
        )
        request.user = mock_user

        response = BulkAscentLogView.as_view()(request)

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# ProfileUpgradeView — POST /api/v1/profiles/{profile_id}/upgrade/
# ---------------------------------------------------------------------------


class TestProfileUpgradeView:
    def test_requires_authentication(self, factory, use_cases) -> None:
        from apps.api.views import ProfileUpgradeView

        request = factory.post("/api/v1/profiles/1/upgrade/")
        request.user = MagicMock()
        request.user.is_authenticated = False

        response = ProfileUpgradeView.as_view()(request, profile_id=1)

        assert response.status_code == 401

    def test_upgrades_profile_to_pro(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import ProfileUpgradeView
        from apps.tourists.models import TouristProfile

        mock_profile = MagicMock(spec=TouristProfile)
        mock_profile.user = mock_user
        mock_profile.active_plan = "FREE"

        with patch("apps.api.views.get_object_or_404", return_value=mock_profile):
            request = factory.post("/api/v1/profiles/1/upgrade/")
            request.user = mock_user

            response = ProfileUpgradeView.as_view()(request, profile_id=1)

            assert response.status_code == 200
            assert mock_profile.active_plan == "PRO"
            mock_profile.save.assert_called_once()

    def test_returns_404_when_profile_not_found(self, factory, mock_user, use_cases) -> None:
        from django.http import Http404

        from apps.api.views import ProfileUpgradeView

        with patch("apps.api.views.get_object_or_404", side_effect=Http404):
            request = factory.post("/api/v1/profiles/1/upgrade/")
            request.user = mock_user

            response = ProfileUpgradeView.as_view()(request, profile_id=1)

            assert response.status_code == 404


# ---------------------------------------------------------------------------
# Additional error handling tests
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_vector_tile_handles_application_exception(self, factory, use_cases) -> None:
        from application.exceptions import UseCaseError
        from apps.api.views import VectorTileView

        use_cases["get_mvt_tile"] = MagicMock()
        use_cases["get_mvt_tile"].execute.side_effect = UseCaseError("Invalid layer")

        request = factory.get("/api/v1/tiles/country/5/10/15.pbf")

        response = VectorTileView.as_view()(request, layer="country", z=5, x=10, y=15)

        assert response.status_code == 422

    def test_map_objects_handles_invalid_bbox_format(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import MapObjectsView

        request = factory.get("/api/v1/map/objects/?bbox=invalid,format")
        request.user = mock_user

        response = MapObjectsView.as_view()(request)

        assert response.status_code == 422

    def test_map_objects_passes_optional_params(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import MapObjectsView

        use_cases["explore_map"].execute.return_value = {"type": "FeatureCollection", "features": []}

        request = factory.get(
            "/api/v1/map/objects/?bbox=10,20,30,40&badge_code=KGP&region_level=voivodeship&region_id=5"
        )
        request.user = mock_user

        response = MapObjectsView.as_view()(request)

        assert response.status_code == 200
        use_cases["explore_map"].execute.assert_called_once()
        call_args = use_cases["explore_map"].execute.call_args
        assert call_args.args[0].badge_code == "KGP"
        assert call_args.args[0].region_level == "voivodeship"
        assert call_args.args[0].region_id == 5

    def test_map_objects_handles_dto_validation_error(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import MapObjectsView

        request = factory.get("/api/v1/map/objects/?bbox=10,20,30,40&region_id=invalid")
        request.user = mock_user

        response = MapObjectsView.as_view()(request)

        assert response.status_code == 422

    def test_map_objects_requires_authentication(self, factory, use_cases) -> None:
        from apps.api.views import MapObjectsView

        request = factory.get("/api/v1/map/objects/?bbox=10,20,30,40")
        request.user = MagicMock()
        request.user.is_authenticated = False

        response = MapObjectsView.as_view()(request)

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# NearbyObjectsView — GET /api/v1/objects/{id}/nearby/
# ---------------------------------------------------------------------------


class TestNearbyObjectsView:
    def test_returns_empty_features_when_no_geom(self, factory, use_cases) -> None:
        from apps.api.views import NearbyObjectsView
        from apps.badges.models import TouristObject

        mock_obj = MagicMock(spec=TouristObject)
        mock_obj.geom = None

        with patch("apps.api.views.get_object_or_404", return_value=mock_obj):
            request = factory.get("/api/v1/objects/1/nearby/")

            response = NearbyObjectsView.as_view()(request, object_id=1)

            assert response.status_code == 200
            data = json.loads(response.content)
            assert data["type"] == "FeatureCollection"
            assert data["features"] == []

    def test_returns_features_with_colors_for_authenticated_user(self, factory, use_cases) -> None:
        from django.contrib.gis.geos import Point

        from apps.api.views import NearbyObjectsView
        from apps.badges.models import TouristObject

        mock_obj = MagicMock(spec=TouristObject)
        mock_obj.geom = Point(10, 20)
        mock_obj.id = 1
        mock_obj.name = "Test Peak"
        mock_obj.type = "peak"

        with patch("apps.api.views.get_object_or_404", return_value=mock_obj):
            with patch("apps.badges.models.TouristObject.objects.filter") as mock_filter:
                mock_filter.return_value.exclude.return_value.__getitem__.return_value = []

                request = factory.get("/api/v1/objects/1/nearby/")
                request.user = MagicMock()
                request.user.is_authenticated = True
                request.user.id = 1

                response = NearbyObjectsView.as_view()(request, object_id=1)

                assert response.status_code == 200
                data = json.loads(response.content)
                assert len(data["features"]) == 1
                assert data["features"][0]["properties"]["is_center"] is True


# ---------------------------------------------------------------------------
# ProfileSettingsView additional tests
# ---------------------------------------------------------------------------


class TestProfileSettingsViewAdditional:
    def test_returns_404_when_profile_not_owned(self, factory, mock_user, use_cases) -> None:

        from apps.api.views import ProfileSettingsView
        from apps.tourists.models import TouristProfile

        other_user = MagicMock()
        other_user.id = 999

        mock_profile = MagicMock(spec=TouristProfile)
        mock_profile.user = other_user

        with patch("apps.api.views.get_object_or_404", return_value=mock_profile):
            request = factory.patch(
                "/api/v1/profiles/1/",
                data=json.dumps({"nickname": "test"}),
                content_type="application/json",
            )
            request.user = mock_user

            response = ProfileSettingsView.as_view()(request, profile_id=1)

            assert response.status_code == 200  # get_object_or_404 raises Http404 before IDOR check

    def test_handles_validation_error(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import ProfileSettingsView
        from apps.tourists.models import TouristProfile

        mock_profile = MagicMock(spec=TouristProfile)
        mock_profile.user = mock_user

        with patch("apps.api.views.get_object_or_404", return_value=mock_profile):
            request = factory.patch(
                "/api/v1/profiles/1/",
                data=json.dumps({"birth_date": "invalid-date"}),
                content_type="application/json",
            )
            request.user = mock_user

            response = ProfileSettingsView.as_view()(request, profile_id=1)

            assert response.status_code == 422


# ---------------------------------------------------------------------------
# BadgeProgressView additional tests
# ---------------------------------------------------------------------------


class TestBadgeProgressViewAdditional:
    def test_handles_dto_validation_error(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import BadgeProgressView

        request = factory.get("/api/v1/badges/KGP/progress/?cycle=invalid")
        request.user = mock_user

        response = BadgeProgressView.as_view()(request, badge_code="KGP")

        assert response.status_code == 422

    def test_requires_authentication(self, factory, use_cases) -> None:
        from apps.api.views import BadgeProgressView

        request = factory.get("/api/v1/badges/KGP/progress/")
        request.user = MagicMock()
        request.user.is_authenticated = False

        response = BadgeProgressView.as_view()(request, badge_code="KGP")

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# BadgeLogisticsView additional tests
# ---------------------------------------------------------------------------


class TestBadgeLogisticsViewAdditional:
    def test_requires_authentication(self, factory, use_cases) -> None:
        from apps.api.views import BadgeLogisticsView

        request = factory.patch(
            "/api/v1/progress/1/logistics/",
            data=json.dumps({"logistic_status": "ALBUM", "status_date": str(date.today())}),
            content_type="application/json",
        )
        request.user = MagicMock()
        request.user.is_authenticated = False

        response = BadgeLogisticsView.as_view()(request, progress_id=1)

        assert response.status_code == 401

    def test_handles_invalid_json(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import BadgeLogisticsView

        request = factory.patch(
            "/api/v1/progress/1/logistics/",
            data="not json",
            content_type="application/json",
        )
        request.user = mock_user

        response = BadgeLogisticsView.as_view()(request, progress_id=1)

        assert response.status_code == 422

    def test_handles_dto_validation_error(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import BadgeLogisticsView

        request = factory.patch(
            "/api/v1/progress/1/logistics/",
            data=json.dumps({"invalid": "data"}),
            content_type="application/json",
        )
        request.user = mock_user

        response = BadgeLogisticsView.as_view()(request, progress_id=1)

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# AscentLogView additional tests
# ---------------------------------------------------------------------------


class TestAscentLogViewAdditional:
    def test_handles_dto_validation_error(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import AscentLogView

        request = factory.post(
            "/api/v1/ascents/",
            data=json.dumps({"peak_id": 15, "ascent_date": "invalid-date"}),
            content_type="application/json",
        )
        request.user = mock_user

        response = AscentLogView.as_view()(request)

        assert response.status_code == 422

    def test_handles_missing_peak_id(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import AscentLogView

        request = factory.post(
            "/api/v1/ascents/",
            data=json.dumps({"ascent_date": str(date.today())}),
            content_type="application/json",
        )
        request.user = mock_user

        response = AscentLogView.as_view()(request)

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# BadgeSubscribeView additional tests
# ---------------------------------------------------------------------------


class TestBadgeSubscribeViewAdditional:
    def test_requires_authentication(self, factory, use_cases) -> None:
        from apps.api.views import BadgeSubscribeView

        request = factory.post("/api/v1/badges/KGP/subscribe/")
        request.user = MagicMock()
        request.user.is_authenticated = False

        response = BadgeSubscribeView.as_view()(request, badge_code="KGP")

        assert response.status_code == 401

    def test_handles_use_case_error(self, factory, mock_user, use_cases) -> None:
        from application.exceptions import UseCaseError
        from apps.api.views import BadgeSubscribeView

        use_cases["start_badge_progress"].execute.side_effect = UseCaseError("Test error")

        request = factory.post("/api/v1/badges/KGP/subscribe/")
        request.user = mock_user

        response = BadgeSubscribeView.as_view()(request, badge_code="KGP")

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# VectorTileView additional tests
# ---------------------------------------------------------------------------


class TestVectorTileViewAdditional:
    def test_returns_204_when_no_tile_data(self, factory, use_cases) -> None:
        from apps.api.views import VectorTileView

        use_cases["get_mvt_tile"] = MagicMock()
        use_cases["get_mvt_tile"].execute.return_value = None

        request = factory.get("/api/v1/tiles/country/5/10/15.pbf")

        response = VectorTileView.as_view()(request, layer="country", z=5, x=10, y=15)

        assert response.status_code == 204

    def test_sets_cache_headers(self, factory, use_cases) -> None:
        from apps.api.views import VectorTileView

        use_cases["get_mvt_tile"] = MagicMock()
        use_cases["get_mvt_tile"].execute.return_value = b"tile_data"

        request = factory.get("/api/v1/tiles/country/5/10/15.pbf")

        response = VectorTileView.as_view()(request, layer="country", z=5, x=10, y=15)

        assert response.status_code == 200
        assert response["Content-Encoding"] == "gzip"
        assert response["Cache-Control"] == "public, max-age=86400"


# ---------------------------------------------------------------------------
# BulkAscentLogView additional tests
# ---------------------------------------------------------------------------


class TestBulkAscentLogViewAdditional:
    def test_handles_dto_validation_error(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import BulkAscentLogView

        request = factory.post(
            "/api/v1/ascents/bulk/",
            data=json.dumps([{"invalid": "data"}]),
            content_type="application/json",
        )
        request.user = mock_user

        response = BulkAscentLogView.as_view()(request)

        assert response.status_code == 422

    def test_skips_cache_when_no_ascents_saved(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import BulkAscentLogView

        use_cases["bulk_log_ascents"] = MagicMock()
        use_cases["bulk_log_ascents"].execute.return_value = {"saved_count": 0}

        request = factory.post(
            "/api/v1/ascents/bulk/",
            data=json.dumps([]),
            content_type="application/json",
        )
        request.user = mock_user

        response = BulkAscentLogView.as_view()(request)

        assert response.status_code == 200
