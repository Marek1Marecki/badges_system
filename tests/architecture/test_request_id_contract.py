"""Testy architektury: kontrakt request_id / correlation ID."""


from django.test import RequestFactory, SimpleTestCase

from infrastructure.middleware.error_handling import RFC7807ErrorMiddleware


class TestRequestIdContract(SimpleTestCase):
    """Middleware musi ustanawiać i propagować request_id."""

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = RFC7807ErrorMiddleware(lambda req: None)

    def test_middleware_generates_request_id(self):
        """Middleware generuje unikalne request_id, jeśli brak nagłówka."""
        request = self.factory.get("/")
        assert not hasattr(request, "request_id")

        self.middleware(request)

        assert hasattr(request, "request_id")
        assert request.request_id.startswith("req_")
        assert len(request.request_id) == len("req_") + 8

    def test_middleware_honors_x_request_id_header(self):
        """Middleware honoruje X-Request-ID z zewnątrz (korelacja między systemami)."""
        request = self.factory.get("/", HTTP_X_REQUEST_ID="ext-abc-123")
        self.middleware(request)

        assert request.request_id == "ext-abc-123"

    def test_request_id_is_propagated_to_response(self):
        """request_id musi być dostępny na obiekcie request podczas przetwarzania."""
        captured = {}

        def get_response(request):
            captured["request_id"] = getattr(request, "request_id", None)
            from django.http import JsonResponse

            return JsonResponse({"ok": True})

        middleware = RFC7807ErrorMiddleware(get_response)
        request = self.factory.get("/", HTTP_X_REQUEST_ID="corr-456")
        middleware(request)

        assert captured["request_id"] == "corr-456"

    def test_request_id_is_unique_per_request(self):
        """Każde żądanie powinno otrzymać inny request_id."""
        req1 = self.factory.get("/")
        req2 = self.factory.get("/")
        self.middleware(req1)
        self.middleware(req2)

        assert req1.request_id != req2.request_id