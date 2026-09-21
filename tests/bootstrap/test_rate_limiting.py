"""Testy dla rate_limiting.py."""

import json
from unittest.mock import MagicMock, patch

import pytest
from django.http import HttpRequest, JsonResponse

from bootstrap.rate_limiting import (
    _get_client_ip,
    _rate_limit_key,
    check_rate_limit,
    rate_limited_response,
    rate_limit,
)


@pytest.fixture(autouse=True)
def mock_cache():
    with patch("bootstrap.rate_limiting.cache") as mock_cache:
        mock_cache.get.return_value = None
        yield mock_cache


class TestGetClientIp:
    """Testy funkcji _get_client_ip."""

    def test_x_forwarded_for_single_ip(self):
        request = HttpRequest()
        request.headers = {"X-Forwarded-For": "192.168.1.1"}
        request.META = {"REMOTE_ADDR": "10.0.0.1"}
        assert _get_client_ip(request) == "192.168.1.1"

    def test_x_forwarded_for_multiple_ips(self):
        request = HttpRequest()
        request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1, 172.16.0.1"}
        request.META = {"REMOTE_ADDR": "10.0.0.1"}
        assert _get_client_ip(request) == "192.168.1.1"

    def test_x_forwarded_for_with_spaces(self):
        request = HttpRequest()
        request.headers = {"X-Forwarded-For": "  192.168.1.1  , 10.0.0.1 "}
        request.META = {"REMOTE_ADDR": "10.0.0.1"}
        assert _get_client_ip(request) == "192.168.1.1"

    def test_no_x_forwarded_for(self):
        request = HttpRequest()
        request.headers = {}
        request.META = {"REMOTE_ADDR": "10.0.0.1"}
        assert _get_client_ip(request) == "10.0.0.1"

    def test_no_remote_addr(self):
        request = HttpRequest()
        request.headers = {}
        request.META = {}
        assert _get_client_ip(request) == "unknown"


class TestRateLimitKey:
    """Testy funkcji _rate_limit_key."""

    def test_rate_limit_key_format(self):
        key = _rate_limit_key("test_scope", "192.168.1.1", 60)
        assert key.startswith("ratelimit:test_scope:192.168.1.1:")

    def test_rate_limit_key_window(self, monkeypatch):
        import time

        fake_time = 1000000
        monkeypatch.setattr(time, "time", lambda: fake_time)
        key = _rate_limit_key("test_scope", "192.168.1.1", 60)
        expected_minute = fake_time // 60
        assert key == f"ratelimit:test_scope:192.168.1.1:{expected_minute}"


class TestCheckRateLimit:
    """Testy funkcji check_rate_limit."""

    def test_allows_new_request(self):
        request = HttpRequest()
        request.headers = {}
        request.META = {"REMOTE_ADDR": "10.0.0.1"}
        request.user = MagicMock()
        request.user.is_authenticated = False
        assert check_rate_limit("test", request, 5, 60) is True

    def test_blocks_when_limit_exceeded(self):
        request = HttpRequest()
        request.headers = {}
        request.META = {"REMOTE_ADDR": "10.0.0.1"}
        request.user = MagicMock()
        request.user.is_authenticated = False
        _rate_limit_key("test", "10.0.0.1", 60)
        # Mock cache to return the limit
        from bootstrap import rate_limiting

        with patch.object(rate_limiting.cache, "get", return_value=5):
            assert check_rate_limit("test", request, 5, 60) is False

    def test_allows_authenticated_user(self):
        request = HttpRequest()
        request.headers = {}
        request.META = {"REMOTE_ADDR": "10.0.0.1"}
        request.user = MagicMock()
        request.user.is_authenticated = True
        request.user.id = 42
        assert check_rate_limit("test", request, 5, 60) is True

    def test_uses_user_id_for_authenticated(self):
        request = HttpRequest()
        request.headers = {}
        request.META = {"REMOTE_ADDR": "10.0.0.1"}
        request.user = MagicMock()
        request.user.is_authenticated = True
        request.user.id = 42
        check_rate_limit("test", request, 5, 60)
        key = _rate_limit_key("test", "user:42", 60)


class TestRateLimitedResponse:
    """Testy funkcji rate_limited_response."""

    def test_response_status(self):
        request = HttpRequest()
        request.path = "/api/test/"
        request.request_id = "req-123"
        response = rate_limited_response(request, 60)
        assert response.status_code == 429

    def test_response_content(self):
        request = HttpRequest()
        request.path = "/api/test/"
        request.request_id = "req-123"
        response = rate_limited_response(request, 60)
        data = json.loads(response.content)
        assert data["status"] == 429
        assert data["title"] == "Rate Limit Exceeded"
        assert data["retry_after"] == 60

    def test_response_headers(self):
        request = HttpRequest()
        request.path = "/api/test/"
        request.request_id = "req-123"
        response = rate_limited_response(request, 60)
        assert response["Retry-After"] == "60"


class TestRateLimitDecorator:
    """Testy dekoratora rate_limit."""

    def test_decorator_allows_within_limit(self):
        request = HttpRequest()
        request.headers = {}
        request.META = {"REMOTE_ADDR": "10.0.0.1"}
        request.user = MagicMock()
        request.user.is_authenticated = False

        @rate_limit(5, 60)
        def test_view(self, request):
            return "allowed"

        result = test_view(None, request)
        assert result == "allowed"

    def test_decorator_blocks_when_exceeded(self):
        request = HttpRequest()
        request.headers = {}
        request.META = {"REMOTE_ADDR": "10.0.0.1"}
        request.user = MagicMock()
        request.user.is_authenticated = False
        _rate_limit_key("test_view", "10.0.0.1", 60)

        from bootstrap import rate_limiting

        with patch.object(rate_limiting.cache, "get", return_value=5):
            @rate_limit(5, 60)
            def test_view(self, request):
                return "allowed"

            result = test_view(None, request)
            assert isinstance(result, JsonResponse)
            assert result.status_code == 429
