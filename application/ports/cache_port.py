"""Port dla mechanizmu buforowania (Cache).

Zgodnie z ADR-015 chroni usługi aplikacyjne przed bezpośrednim zależeniem od konkretnych implementacji (np. Redis,
Memcached).
"""

from typing import Any, Protocol


class CachePort(Protocol):
    """Interfejs dostępu do globalnej pamięci podręcznej."""

    def set(self, key: str, value: Any, timeout_seconds: int) -> None:
        """Zapisuje wartość pod kluczem z określonym czasem wygaśnięcia."""
        ...

    def get(self, key: str) -> Any | None:
        """Pobiera wartość.

        Zwraca None, jeśli klucz nie istnieje.
        """
        ...

    def delete(self, key: str) -> None:
        """Usuwa klucz z pamięci."""
        ...
