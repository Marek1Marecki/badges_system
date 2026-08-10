"""Testy bezpieczeństwa dla warstwy API (RFC 7807).

Weryfikują, że wyjątki aplikacyjne nie ujawniają wrażliwych danych
w odpowiedziach HTTP, a nieoczekiwane błędy są logowane z pełnym tracebackiem.
"""

import json
from unittest.mock import patch

import pytest

from application.exceptions import ApplicationException, ConflictError, ResourceNotFoundError, UseCaseError
from apps.api.views import _handle_application_exception, _problem_detail

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

        mock_logger.info.assert_called_once_with(
            "resource_not_found", extra={"request_id": "security-test-123"}
        )

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

        mock_logger.warning.assert_called_once_with(
            "conflict", extra={"request_id": "security-test-123"}
        )

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

        mock_logger.info.assert_called_once_with(
            "validation_failed", extra={"request_id": "security-test-123"}
        )

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

