"""Testy dla error handling middleware."""

from django.http import HttpRequest, JsonResponse

from infrastructure.middleware.error_handling import RFC7807ErrorMiddleware, _problem_detail


class TestProblemDetail:
    """Testy funkcji _problem_detail."""

    def test_problem_detail_response_structure(self):
        """Test struktury odpowiedzi RFC 7807."""
        request = HttpRequest()
        request.path = "/test/path"
        request.request_id = "req_12345678"

        response = _problem_detail(
            request=request,
            error_type="test-error",
            title="Test Error",
            status=400,
            detail="Test detail message",
        )

        assert isinstance(response, JsonResponse)
        assert response.status_code == 400

    def test_problem_detail_response_content(self):
        """Test zawartości odpowiedzi RFC 7807."""
        import json

        request = HttpRequest()
        request.path = "/test/path"
        request.request_id = "req_12345678"

        response = _problem_detail(
            request=request,
            error_type="test-error",
            title="Test Error",
            status=400,
            detail="Test detail message",
        )

        data = json.loads(response.content)
        assert data["type"] == "https://api.pttk-badges.pl/errors/test-error"
        assert data["title"] == "Test Error"
        assert data["status"] == 400
        assert data["detail"] == "Test detail message"
        assert data["instance"] == "/test/path"
        assert data["request_id"] == "req_12345678"

    def test_problem_detail_without_request_id(self):
        """Test odpowiedzi bez request_id."""
        import json

        request = HttpRequest()
        request.path = "/test/path"

        response = _problem_detail(
            request=request,
            error_type="test-error",
            title="Test Error",
            status=400,
            detail="Test detail message",
        )

        data = json.loads(response.content)
        assert data["request_id"] == "unknown"


class TestRFC7807ErrorMiddleware:
    """Testy klasy RFC7807ErrorMiddleware."""

    def test_init(self):
        """Test inicjalizacji middleware."""
        get_response = lambda request: None
        middleware = RFC7807ErrorMiddleware(get_response)
        assert middleware.get_response == get_response

    def test_call_injects_request_id(self):
        """Test że __call__ wstrzykuje request_id."""
        request = HttpRequest()
        request.path = "/test/path"

        def get_response(req):
            return req

        middleware = RFC7807ErrorMiddleware(get_response)
        result = middleware(request)

        assert hasattr(result, "request_id")
        assert result.request_id.startswith("req_")
        assert len(result.request_id) == 12  # req_ + 8 hex chars

    def test_call_returns_get_response_result(self):
        """Test że __call__ zwraca wynik get_response."""
        request = HttpRequest()
        request.path = "/test/path"

        def get_response(req):
            return JsonResponse({"test": "data"})

        middleware = RFC7807ErrorMiddleware(get_response)
        result = middleware(request)

        assert isinstance(result, JsonResponse)

    def test_process_exception_returns_problem_detail(self):
        """Test że process_exception zwraca odpowiedź RFC 7807."""
        import json

        request = HttpRequest()
        request.path = "/test/path"
        request.request_id = "req_12345678"

        exception = Exception("Test exception")

        middleware = RFC7807ErrorMiddleware(lambda r: None)
        response = middleware.process_exception(request, exception)

        assert isinstance(response, JsonResponse)
        assert response.status_code == 500

        data = json.loads(response.content)
        assert data["type"] == "https://api.pttk-badges.pl/errors/internal-error"
        assert data["title"] == "Wewnętrzny Błąd Serwera"
        assert data["status"] == 500
        assert data["instance"] == "/test/path"
        assert data["request_id"] == "req_12345678"

    def test_process_exception_with_various_exceptions(self):
        """Test process_exception z różnymi typami wyjątków."""
        request = HttpRequest()
        request.path = "/test/path"
        request.request_id = "req_12345678"

        exceptions = [
            ValueError("Test value error"),
            RuntimeError("Test runtime error"),
            KeyError("Test key error"),
        ]

        middleware = RFC7807ErrorMiddleware(lambda r: None)

        for exc in exceptions:
            response = middleware.process_exception(request, exc)
            assert isinstance(response, JsonResponse)
            assert response.status_code == 500
