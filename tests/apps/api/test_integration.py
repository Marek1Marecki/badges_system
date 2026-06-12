"""Testy integracyjne dla REST API turysty (Faza C).

Strategia: RequestFactory + MagicMock user + patch na get_container.
Zero dostępu do bazy — PostGIS nie jest wymagany.
"""

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def factory():
    from django.test import RequestFactory

    return RequestFactory()


@pytest.fixture
def mock_user():
    """Fake authenticated user — bez zapisu do bazy."""
    user = MagicMock()
    user.is_authenticated = True
    user.id = 1
    user.username = "turysta"
    return user


@pytest.fixture
def use_cases():
    """Zwraca dict mocków Use Case'ów i patch na get_container."""
    cases = {
        "log_ascent": MagicMock(),
        "start_badge_progress": MagicMock(),
        "verify_badge": MagicMock(),
        "explore_map": MagicMock(),
        "advance_logistic_status": MagicMock(),
    }
    with patch("apps.api.views.get_container", return_value=cases):
        yield cases


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

    def test_user_id_from_session_not_body(self, factory, mock_user, use_cases) -> None:
        """SECURITY: user_id musi pochodzić z request.user.id, nie z payloadu."""
        from apps.api.views import AscentLogView

        use_cases["log_ascent"].execute.return_value = 1

        request = factory.post(
            "/api/v1/ascents/",
            data=json.dumps({"peak_id": 15, "ascent_date": str(date.today()), "user_id": 999}),
            content_type="application/json",
        )
        request.user = mock_user  # id=1

        AscentLogView.as_view()(request)

        call_kwargs = use_cases["log_ascent"].execute.call_args
        assert call_kwargs.kwargs["user_id"] == 1

    def test_conflict_error_returns_409_rfc7807(self, factory, mock_user, use_cases) -> None:
        """ConflictError (D-04) → 409 Conflict RFC 7807."""
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
        assert data["title"] == "Konflikt Danych"
        assert "duplikatem" in data["detail"]

    def test_bitemporal_error_returns_422(self, factory, mock_user, use_cases) -> None:
        """BitemporalTimeError (T-01) → 422 Unprocessable Entity."""
        from application.exceptions import BitemporalTimeError
        from apps.api.views import AscentLogView

        use_cases["log_ascent"].execute.side_effect = BitemporalTimeError("Obiekt powstał po podanej dacie wejścia")

        request = factory.post(
            "/api/v1/ascents/",
            data=json.dumps({"peak_id": 15, "ascent_date": "1800-01-01"}),
            content_type="application/json",
        )
        request.user = mock_user

        response = AscentLogView.as_view()(request)

        assert response.status_code == 422
        assert json.loads(response.content)["status"] == 422

    def test_future_date_returns_422(self, factory, mock_user, use_cases) -> None:
        """UseCaseError (T-03) → 422."""
        from application.exceptions import UseCaseError
        from apps.api.views import AscentLogView

        use_cases["log_ascent"].execute.side_effect = UseCaseError("Data z przyszłości")

        request = factory.post(
            "/api/v1/ascents/",
            data=json.dumps({"peak_id": 15, "ascent_date": "2099-01-01"}),
            content_type="application/json",
        )
        request.user = mock_user

        response = AscentLogView.as_view()(request)

        assert response.status_code == 422

    def test_invalid_json_returns_422(self, factory, mock_user, use_cases) -> None:
        """Niepoprawny JSON → 422 bez rzucania wyjątku."""
        from apps.api.views import AscentLogView

        request = factory.post(
            "/api/v1/ascents/",
            data="to nie jest json {{{",
            content_type="application/json",
        )
        request.user = mock_user

        response = AscentLogView.as_view()(request)

        assert response.status_code == 422

    def test_unauthenticated_returns_401(self, factory, use_cases) -> None:
        """Brak autentykacji → 401."""
        from django.contrib.auth.models import AnonymousUser

        from apps.api.views import AscentLogView

        request = factory.post(
            "/api/v1/ascents/",
            data=json.dumps({"peak_id": 15, "ascent_date": str(date.today())}),
            content_type="application/json",
        )
        request.user = AnonymousUser()

        response = AscentLogView.as_view()(request)

        assert response.status_code == 401


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

        # ZMIANA: Musimy wymusić zwrócenie liczby całkowitej (int),
        # inaczej JsonResponse wybuchnie próbując formatować MagicMocka!
        use_cases["start_badge_progress"].execute.return_value = 42

        request = factory.post("/api/v1/badges/KGP/subscribe/")
        request.user = mock_user

        BadgeSubscribeView.as_view()(request, badge_code="KGP")

        use_cases["start_badge_progress"].execute.assert_called_once_with(user_id=1, badge_code="KGP")

    def test_no_regulation_returns_422(self, factory, mock_user, use_cases) -> None:
        from application.exceptions import UseCaseError
        from apps.api.views import BadgeSubscribeView

        use_cases["start_badge_progress"].execute.side_effect = UseCaseError("Brak regulaminu")

        request = factory.post("/api/v1/badges/KGP/subscribe/")
        request.user = mock_user

        response = BadgeSubscribeView.as_view()(request, badge_code="KGP")

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# BadgeProgressView — GET /api/v1/badges/{badge_code}/progress/
# ---------------------------------------------------------------------------


class TestBadgeProgressView:
    def test_progress_200_returns_evaluation_result(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import BadgeProgressView

        domain_result = {
            "verified": False,
            "status": "IN_PROGRESS",
            "errors": [],
            "valid_ascents_count": 12,
        }
        use_cases["verify_badge"].execute.return_value = domain_result

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
        data = json.loads(response.content)
        assert data["type"] == "https://api.pttk-badges.pl/errors/resource-not-found"
        assert "Nie subskrybuje" in data["detail"]

    def test_cycle_param_passed_to_use_case(self, factory, mock_user, use_cases) -> None:
        from apps.api.views import BadgeProgressView

        use_cases["verify_badge"].execute.return_value = {"status": "COMPLETED"}

        request = factory.get("/api/v1/badges/KGP/progress/?cycle=2")
        request.user = mock_user

        BadgeProgressView.as_view()(request, badge_code="KGP")

        call_args = use_cases["verify_badge"].execute.call_args
        assert call_args.args[0].cycle_number == 2


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
