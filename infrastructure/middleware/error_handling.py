"""Globalny strażnik błędów zgodny z RFC 7807 Problem Details.

Zgodnie z ERROR_HANDLING.md, znane błędy domenowe są łapane bezpośrednio
w views.py (wymóg testów RequestFactory). Ten middleware odpowiada za:
1. Wstrzykiwanie unikalnego request_id do logów.
2. Przechwytywanie krytycznych, nieoczekiwanych wyjątków (500 Internal Error),
   które wymknęły się z widoków (np. błędy bazy danych, bugi w kodzie).
"""

import uuid
from collections.abc import Callable
from typing import Any

from django.http import HttpRequest, JsonResponse
from loguru import logger


def _problem_detail(
    request: HttpRequest,
    error_type: str,
    title: str,
    status: int,
    detail: str,
) -> JsonResponse:
    """Buduje odpowiedź RFC 7807 Problem Details.

    Args:
      request: HttpRequest:
      error_type: str:
      title: str:
      status: int:
      detail: str:
      request: HttpRequest:
      error_type: str:
      title: str:
      status: int:
      detail: str:

    Returns:
    """
    return JsonResponse(
        {
            "type": f"https://api.pttk-badges.pl/errors/{error_type}",
            "title": title,
            "status": status,
            "detail": detail,
            "instance": request.path,
            "request_id": getattr(request, "request_id", "unknown"),
        },
        status=status,
    )


class RFC7807ErrorMiddleware:
    """Wychwytuje twarde awarie serwera i formatuje je w bezpieczny JSON."""

    def __init__(self, get_response: Callable[[HttpRequest], Any]) -> None:
        """Inicjalizuje middleware obsługi błędów."""
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> Any:
        """Przetwarza żądanie i obsługuje błędy w formacie RFC 7807."""
        # Propagacja request_id: preferuj X-Request-ID z zewnątrz, w przeciwnym razie wygeneruj nowy.
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:8]}"  # type: ignore[attr-defined]
        request.request_id = request_id  # type: ignore[attr-defined]

        # Loguru kontekst owija całe żądanie
        with logger.contextualize(request_id=request.request_id):  # type: ignore[attr-defined]
            return self.get_response(request)

    def process_exception(self, request: HttpRequest, exception: Exception) -> JsonResponse | None:
        """Django wywołuje tę metodę tylko, gdy widok rzuci nieobsłużony wyjątek.

        Args:
          request: HttpRequest
          request: HttpRequest:
          exception: Exception:

        Returns:
        """
        # Jeśli tu dotarliśmy, oznacza to, że aplikacja wybuchła w sposób niekontrolowany
        # (np. padła baza, literówka w kodzie). Wyjątki domenowe są łapane w views.py.

        # ZASADA 500: Twarda izolacja stacktrace'a przed wyciekiem na front!
        logger.exception("Nieobsłużony błąd serwera podczas przetwarzania żądania HTTP.", extra={"path": request.path})

        return _problem_detail(
            request=request,
            error_type="internal-error",
            title="Wewnętrzny Błąd Serwera",
            status=500,
            detail="Wystąpił nieoczekiwany problem z przetworzeniem zapytania.",
        )
