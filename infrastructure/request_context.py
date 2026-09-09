"""ContextVar dla request_id — korelacja logów HTTP ↔ Celery (AUDYT-117).

Zgodnie z zasadą Czystej Domeny, identyfikator żądania HTTP nie powinien
przenikać przez warstwy domenowych. Zamiast tego:
- Middleware HTTP zapisuje request_id do ContextVar.
- CeleryEventPublisher odczytuje ContextVar w momencie publikacji.
- Worker Celery propaguje ContextVar poprzez task_primitives.

Dzięki temu `request_id` nigdy nie dotyka:
- application.use_cases.LogAscentUseCase
- domain.events.UserProgressStateChanged

Wzorzec zgodny z Logurą i dokumentacją Celery (context propagation).
"""

from contextvars import ContextVar

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def set_request_id(request_id: str | None) -> None:
    """Ustawia request_id w bieżącym kontekście wątku.

    Zwraca Token nieużywany — w przypadku błędu ContextVar przyjmuje default.
    """
    _request_id_var.set(request_id)


def get_request_id() -> str | None:
    """Odczytuje request_id z bieżącego kontekstu wątku."""
    return _request_id_var.get()
