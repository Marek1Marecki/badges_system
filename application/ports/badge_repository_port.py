"""Interfejsy (Porty) dla komunikacji z bazą danych."""

from datetime import date
from typing import Protocol

from domain.entities.badge_version import BadgeVersionDomain


class BadgeRepositoryPort(Protocol):
    """Port repozytorium do zarządzania odznakami.

    Infrastruktura (Django) musi zaimplementować ten interfejs.
    """

    def get_badge_version(self, badge_code: str, version_code: str) -> BadgeVersionDomain | None:
        """Pobiera konkretną wersję odznaki z bazy i rekonstruuje obiekt domenowy."""
        ...

    def get_version_id_for_date(self, badge_code: str, target_date: date) -> int | None:
        """Pobiera ID wersji odznaki obowiązującej w podanym dniu.

        Wyszukuje najnowszą wersję, której valid_from <= target_date.
        """
        ...

    def get_badge_version_by_id(self, version_id: int) -> BadgeVersionDomain | None:
        """Pobiera Wersję Odznaki po jej wewnętrznym ID."""
        ...

    def get_latest_badge_version(self, badge_code: str) -> BadgeVersionDomain | None:
        """Pobiera najnowszą opublikowaną (oficjalną) wersję regulaminu dla odznaki."""
        ...
