"""Implementacja Unit of Work za pomocą transakcji Django ORM."""

from __future__ import annotations

from typing import Any

from django.db import transaction

from application.ports.uow_port import UnitOfWorkPort


class DjangoUnitOfWork(UnitOfWorkPort):
    """Owijka na transaction.atomic() chroniąca Czystą Architekturę."""

    def __enter__(self) -> DjangoUnitOfWork:
        self._atomic = transaction.atomic()
        self._atomic.__enter__()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._atomic.__exit__(exc_type, exc_val, exc_tb)
