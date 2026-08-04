"""Port dla Wzorca Unit of Work (Granice Transakcji)."""

from __future__ import annotations

from typing import Any, Protocol


class UnitOfWorkPort(Protocol):
    """Abstrakcja zarządzania transakcjami bazy danych w Use Case'ach."""

    def __enter__(self) -> UnitOfWorkPort:
        """Rozpocznij transakcję."""
        ...

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Zakończ transakcję."""
        ...
