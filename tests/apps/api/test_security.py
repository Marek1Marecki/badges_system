"""Testy bezpieczeństwa dla warstwy API (RFC 7807).

Weryfikują, że wyjątki aplikacyjne nie ujawniają wrażliwych danych
w odpowiedziach HTTP, a nieoczekiwane błędy są logowane z pełnym tracebackiem.
"""

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from application.exceptions import ApplicationException, ConflictError, ResourceNotFoundError, UseCaseError
from apps.api.views import (
    AscentLogView,
    BadgeLogisticsView,
    BulkAscentLogView,
    MapObjectsView,
    ProfileSettingsView,
    _handle_application_exception,
    _problem_detail,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def factory():
    from django.test import RequestFactory

    class SessionRequestFactory(RequestFactory):
        def generic(self, *args, **kwargs):
            req = super().generic(*args, **kwargs)
            req.session = {}
            return req

    return SessionRequestFactory()


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.is_authenticated = True
    user.id = 1
    user.username = "turysta"

    mock_profile = MagicMock()
    mock_profile.id = 1
    user.profiles.first.return_value = mock_profile

    return user


@pytest.fixture
def request_with_id(factory):
    req = factory.get("/api/v1/test")
    req.request_id = "security-test-123"
    req.path = "/api/v1/test"
    return req


class TestProblemDetailDoesNotLeakStackTrace:
    """Werytuje, że _problem_detail nie ujawnia śladu stosu."""

    def test_response_does_not_contain_traceback_keywords(self, request_with_id):
        response = _problem_detail(
            request_with_id,
            error_type="internal-error",
            title="Wewnętrzny Błąd Serwera",
            status=500,
            detail="Wystąpił wewnętrzny błąd serwera.",
        )

        assert response.status_code == 500
        data = json.loads(response.content)
        assert "Traceback" not in data["detail"]
        assert "File " not in data["detail"]
        assert "line " not in data["detail"]

    def test_response_contains_request_id(self, request_with_id):
        response = _problem_detail(
            request_with_id,
            error_type="internal-error",
            title="Wewnętrzny Błąd Serwera",
            status=500,
            detail="Wystąpił wewnętrzny błąd serwera.",
        )

        data = json.loads(response.content)
        assert data["request_id"] == "security-test-123"


class TestHandleApplicationExceptionDoesNotLeakSecrets:
    """Werytuje, że nieoczekiwane ApplicationException nie ujawniają szczegółów."""

    def test_unexpected_application_exception_does_not_leak_message(self, request_with_id):
        """Fallback dla nieznanych podklas ApplicationException zwraca generic message."""
        secret_exc = ApplicationException("SECRET_DATABASE_PASSWORD")

        with patch("apps.api.views.logger") as mock_logger:
            response = _handle_application_exception(request_with_id, secret_exc)

        assert response.status_code == 500
        data = json.loads(response.content)
        assert data["status"] == 500
        assert data["title"] == "Wewnętrzny Błąd Serwera"
        assert "SECRET_DATABASE_PASSWORD" not in data["detail"]
        assert "SECRET" not in data["detail"]
        assert data["detail"] == "Wystąpił wewnętrzny błąd serwera."
        assert data["request_id"] == "security-test-123"

        mock_logger.error.assert_called_once()
        mock_logger.error.assert_called_with(
            "unhandled_application_exception",
            extra={"request_id": "security-test-123"},
            exc_info=True,
        )

    def test_known_exceptions_still_pass_controlled_messages(self, request_with_id):
        """Znane wyjątki biznesowe nadal przekazują bezpieczne komunikaty."""
        exc = ResourceNotFoundError("Profil o podanym identyfikatorze nie istnieje.")

        with patch("apps.api.views.logger") as mock_logger:
            response = _handle_application_exception(request_with_id, exc)

        assert response.status_code == 404
        data = json.loads(response.content)
        assert data["detail"] == "Zasób nie istnieje."
        assert "Profil o podanym identyfikatorze nie istnieje." not in data["detail"]
        assert "SECRET" not in data["detail"]

        mock_logger.info.assert_called_once_with("resource_not_found", extra={"request_id": "security-test-123"})

    def test_conflict_error_does_not_leak_internal_details(self, request_with_id):
        """ConflictError nie powinien ujawniać szczegółów technicznych."""
        exc = ConflictError("Duplicate entry for key 'ascent'")

        with patch("apps.api.views.logger") as mock_logger:
            response = _handle_application_exception(request_with_id, exc)

        assert response.status_code == 409
        data = json.loads(response.content)
        assert data["detail"] == "Konflikt danych."
        assert "Duplicate entry for key 'ascent'" not in data["detail"]
        assert "Traceback" not in data["detail"]

        mock_logger.warning.assert_called_once_with("conflict", extra={"request_id": "security-test-123"})

    def test_use_case_error_does_not_leak_stack_trace(self, request_with_id):
        """UseCaseError nie powinien przekazywać tracebacku do klienta."""
        exc = UseCaseError("Brak regulaminu dla daty 2024-01-01")

        with patch("apps.api.views.logger") as mock_logger:
            response = _handle_application_exception(request_with_id, exc)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert data["detail"] == "Błąd walidacji."
        assert "Brak regulaminu dla daty 2024-01-01" not in data["detail"]
        assert "Traceback" not in data["detail"]
        assert "File " not in data["detail"]

        mock_logger.info.assert_called_once_with("validation_failed", extra={"request_id": "security-test-123"})

    def test_logger_exc_info_is_called_only_for_unexpected(self, request_with_id):
        """exc_info=True powinno być używane tylko dla nieoczekiwanych wyjątków."""
        secret_exc = ApplicationException("SECRET_DATABASE_PASSWORD")

        with patch("apps.api.views.logger") as mock_logger:
            _handle_application_exception(request_with_id, secret_exc)

        call_kwargs = mock_logger.error.call_args.kwargs
        assert call_kwargs["exc_info"] is True

    def test_business_exceptions_do_not_log_exc_info(self, request_with_id):
        """Błędy biznesowe nie powinien logować exc_info (nie są błędami)."""
        exc = ResourceNotFoundError("Profil nie istnieje.")

        with patch("apps.api.views.logger") as mock_logger:
            _handle_application_exception(request_with_id, exc)

        call_kwargs = mock_logger.info.call_args.kwargs
        assert "exc_info" not in call_kwargs


class TestValidationErrorDoesNotLeakParserDetails:
    """Werytuje, że błędy parsowania JSON/ValueError nie ujawniają szczegółów."""

    def test_json_decode_error_returns_safe_message(self, factory, mock_user):
        request = factory.post(
            "/api/v1/ascents/",
            data="nieprawidłowy json",
            content_type="application/json",
        )
        request.user = mock_user
        request.session = {}
        request.request_id = "sec-json-1"
        request.path = "/api/v1/ascents/"

        with patch("apps.api.views.logger") as mock_logger:
            response = AscentLogView.as_view()(request)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert data["detail"] == "Nieprawidłowe dane wejściowe."
        assert "Expecting value" not in data["detail"]
        assert "JSONDecodeError" not in data["detail"]

        mock_logger.warning.assert_called_once_with(
            "invalid_ascent_payload",
            extra={"request_id": "sec-json-1"},
        )

    def test_value_error_does_not_leak_internal_details(self, factory, mock_user):
        request = factory.post(
            "/api/v1/ascents/",
            data=json.dumps({"peak_id": "not_a_number"}),
            content_type="application/json",
        )
        request.user = mock_user
        request.session = {}
        request.request_id = "sec-val-1"
        request.path = "/api/v1/ascents/"

        with patch("apps.api.views.logger") as mock_logger:
            response = AscentLogView.as_view()(request)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert data["detail"] == "Nieprawidłowe dane wejściowe."
        assert "not_a_number" not in data["detail"]
        assert "ValueError" not in data["detail"]

        mock_logger.warning.assert_called_once_with(
            "invalid_ascent_payload",
            extra={"request_id": "sec-val-1"},
        )


class TestMapObjectsViewValidation:
    """Werytuje, że MapObjectsView nie ujawnia szczegółów wyjątków walidacji."""

    def test_invalid_region_id_returns_safe_422(self, factory, mock_user):
        request = factory.get(
            "/api/v1/map/objects?bbox=1.0,2.0,3.0,4.0&region_id=abc",
        )
        request.user = mock_user
        request.session = {}
        request.request_id = "sec-map-1"
        request.path = "/api/v1/map/objects"

        response = MapObjectsView.as_view()(request)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert data["detail"] == "Nieprawidłowe dane wejściowe."
        assert "abc" not in data["detail"]
        assert "ValueError" not in data["detail"]

    def test_invalid_pydantic_dto_returns_safe_422(self, factory, mock_user):
        request = factory.get(
            "/api/v1/map/objects?bbox=1.0,2.0,3.0,4.0",
        )
        request.user = mock_user
        request.session = {}
        request.request_id = "sec-map-2"
        request.path = "/api/v1/map/objects"

        with patch("apps.api.views.MapExploreRequestDTO", side_effect=ValueError("pydantic boom")):
            response = MapObjectsView.as_view()(request)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert data["detail"] == "Nieprawidłowe dane wejściowe."
        assert "pydantic boom" not in data["detail"]
        assert "ValueError" not in data["detail"]

    def test_unexpected_exception_is_not_masked_as_422(self, factory, mock_user):
        request = factory.get(
            "/api/v1/map/objects?bbox=1.0,2.0,3.0,4.0",
        )
        request.user = mock_user
        request.session = {}
        request.request_id = "sec-map-3"
        request.path = "/api/v1/map/objects"

        with patch("apps.api.views.MapExploreRequestDTO", side_effect=RuntimeError("DTO boom")):
            with pytest.raises(RuntimeError, match="DTO boom"):
                MapObjectsView.as_view()(request)


class TestBadgeLogisticsViewValidation:
    """Werytuje, że BadgeLogisticsView nie ujawnia szczegółów wyjątków walidacji."""

    def test_validation_error_returns_safe_422(self, factory, mock_user):
        request = factory.patch(
            "/api/v1/progress/1/logistics/",
            data=json.dumps({"logistic_status": "INVALID_STATUS", "status_date": "not-a-date"}),
            content_type="application/json",
        )
        request.user = mock_user
        request.session = {}
        request.request_id = "sec-log-1"
        request.path = "/api/v1/progress/1/logistics/"

        response = BadgeLogisticsView.as_view()(request, progress_id=1)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert data["detail"] == "Nieprawidłowe dane wejściowe."
        assert "not-a-date" not in data["detail"]
        assert "ValidationError" not in data["detail"]

    def test_unexpected_exception_is_not_masked_as_422(self, factory, mock_user):
        request = factory.patch(
            "/api/v1/progress/1/logistics/",
            data=json.dumps({"logistic_status": "WAITING_FOR_VERIFICATION", "status_date": str(date.today())}),
            content_type="application/json",
        )
        request.user = mock_user
        request.session = {}
        request.request_id = "sec-log-2"
        request.path = "/api/v1/progress/1/logistics/"

        with patch("apps.api.views.LogisticStatusUpdateDTO", side_effect=RuntimeError("DTO boom")):
            with pytest.raises(RuntimeError, match="DTO boom"):
                BadgeLogisticsView.as_view()(request, progress_id=1)


class TestBulkAscentLogViewValidation:
    """Werytuje, że BulkAscentLogView nie ujawnia szczegółów wyjątków walidacji."""

    def test_non_list_payload_returns_safe_422(self, factory, mock_user):
        request = factory.post(
            "/api/v1/ascents/bulk/",
            data=json.dumps("not-a-list"),
            content_type="application/json",
        )
        request.user = mock_user
        request.session = {}
        request.request_id = "sec-bulk-1"
        request.path = "/api/v1/ascents/bulk/"

        response = BulkAscentLogView.as_view()(request)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert data["detail"] == "Nieprawidłowe dane wejściowe."
        assert "not-a-list" not in data["detail"]
        assert "ValueError" not in data["detail"]

    def test_invalid_ascent_item_returns_safe_422(self, factory, mock_user):
        request = factory.post(
            "/api/v1/ascents/bulk/",
            data=json.dumps([{"peak_id": "not_a_number", "ascent_date": str(date.today())}]),
            content_type="application/json",
        )
        request.user = mock_user
        request.session = {}
        request.request_id = "sec-bulk-2"
        request.path = "/api/v1/ascents/bulk/"

        response = BulkAscentLogView.as_view()(request)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert data["detail"] == "Nieprawidłowe dane wejściowe."
        assert "not_a_number" not in data["detail"]
        assert "ValidationError" not in data["detail"]

    def test_unexpected_exception_is_not_masked_as_422(self, factory, mock_user):
        request = factory.post(
            "/api/v1/ascents/bulk/",
            data=json.dumps([{"peak_id": 1, "ascent_date": str(date.today())}]),
            content_type="application/json",
        )
        request.user = mock_user
        request.session = {}
        request.request_id = "sec-bulk-3"
        request.path = "/api/v1/ascents/bulk/"

        with patch("apps.api.views.AscentInputDTO", side_effect=RuntimeError("DTO boom")):
            with pytest.raises(RuntimeError, match="DTO boom"):
                BulkAscentLogView.as_view()(request)


class TestProfileSettingsViewValidation:
    """Werytuje, że ProfileSettingsView nie ujawnia szczegółów wyjątków walidacji."""

    def test_validation_error_returns_safe_422(self, factory, mock_user):
        request = factory.patch(
            "/api/v1/profiles/1/",
            data=json.dumps({"birth_date": "not-a-date"}),
            content_type="application/json",
        )
        request.user = mock_user
        request.session = {}
        request.request_id = "sec-prof-1"
        request.path = "/api/v1/profiles/1/"

        mock_profile = MagicMock()
        mock_profile.id = 1

        with patch("apps.api.views.get_object_or_404", return_value=mock_profile):
            response = ProfileSettingsView.as_view()(request, profile_id=1)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert data["detail"] == "Nieprawidłowe dane wejściowe."
        assert "not-a-date" not in data["detail"]
        assert "ValidationError" not in data["detail"]

    def test_unexpected_exception_is_not_masked_as_422(self, factory, mock_user):
        request = factory.patch(
            "/api/v1/profiles/1/",
            data=json.dumps({"nickname": "test"}),
            content_type="application/json",
        )
        request.user = mock_user
        request.session = {}
        request.request_id = "sec-prof-2"
        request.path = "/api/v1/profiles/1/"

        mock_profile = MagicMock()
        mock_profile.id = 1

        with patch("apps.api.views.get_object_or_404", return_value=mock_profile):
            with patch("apps.api.views.UpdateProfileRequestDTO", side_effect=RuntimeError("DTO boom")):
                with pytest.raises(RuntimeError, match="DTO boom"):
                    ProfileSettingsView.as_view()(request, profile_id=1)
