"""Interfejsy (Porty) dla komunikacji z bazą danych."""

from typing import Protocol

from domain.entities.badge_version import BadgeVersionDomain


class BadgeRepositoryPort(Protocol):
    """Port repozytorium do zarządzania odznakami.

    Infrastruktura (Django) musi zaimplementować ten interfejs.
    """

    def get_badge_version(self, badge_code: str, version_code: str) -> BadgeVersionDomain | None:
        """Pobiera konkretną wersję odznaki z bazy i rekonstruuje obiekt domenowy."""
        ...
