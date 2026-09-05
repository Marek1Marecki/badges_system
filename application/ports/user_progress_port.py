"""Porty (Kontrakty) zarządzania użytkownikiem i jego wejściami.

Zgodnie z 22-ports-adapters-dto-contract.md: Porty te są implementowane w infrastructure/adapters/, a wywoływane w
application/use_cases/. Nie zawierają importów z Django.
"""

from datetime import date
from typing import Protocol

from application.dto.ascent_dto import AscentDTO, AscentRequestDTO
from application.dto.user_context_dto import BadgeProgressDTO, TouristProfileDTO


class TouristProfileRepositoryPort(Protocol):
    """Port dostarczający dane o wieku i limitach turysty."""

    def get_profile(self, profile_id: int) -> TouristProfileDTO | None:
        """Pobiera pełen, połączony profil (z limitami).

        Zwraca None, jeśli nie istnieje.
        """


class AscentLogRepositoryPort(Protocol):
    """Port obsługujący fizyczny dziennik wejść w oparciu o bitemporalność."""

    def get_object_lifespan(self, object_id: int) -> tuple[date | None, date | None] | None:
        """Pobiera okno istnienia obiektu turystycznego.

        Zwraca `(existence_start, existence_end)`. `None` w dacie oznacza brak ograniczenia czasowego, a `None` jako
        wynik oznacza brak obiektu.
        """

    def ascent_exists(self, profile_id: int, object_id: int, ascent_date: date) -> bool:
        """Sprawdza, czy turysta posiada już log wejścia na ten obiekt w tym dniu (Upsert)."""

    def get_oldest_ascent_date(self, profile_id: int, badge_code: str) -> date | None:
        """Zwraca datę najstarszego wpisu dla danej odznaki (potrzebne do Praw Nabytych)."""

    def save_ascent(self, profile_id: int, object_id: int, ascent_date: date) -> int:
        """Zapisuje wejście."""

    def get_unconsumed_ascents(self, profile_id: int, badge_code: str, cutoff_date: date | None) -> list[AscentDTO]:
        """Pobiera wejścia turysty.

        Jeśli podano cutoff_date (data zamknięcia poprzedniego cyklu odznaki), odfiltrowuje wejścia 'zużyte' (starsze
        lub równe tej dacie). Zwrócone AscentDTO może posiadać wstrzyknięte regiony CQRS (Dla Wildcard Rules).
        """

    def get_all_ascents_for_user(self, profile_id: int) -> list[AscentDTO]:
        """Pobiera całą, niefiltrowaną historię wejść turysty na potrzeby oceny kolorów."""

    def get_objects_lifespans(self, object_ids: set[int]) -> dict[int, tuple[date | None, date | None]]:
        """Pobiera bitemporalne ramy życia dla wielu obiektów naraz (Optymalizacja N+1).

        Zwraca słownik: {object_id: (existence_start, existence_end)}
        """

    def bulk_save_ascents(self, profile_id: int, ascents: list[AscentRequestDTO]) -> int:
        """Masowo zapisuje wejścia.

        Ignoruje duplikaty (Idempotentność D-04). Zwraca liczbę faktycznie dodanych nowych rekordów.
        """


class UserProgressRepositoryPort(Protocol):
    """Port obsługujący subskrypcje, Prawa Nabyte i Osobisty Kanban."""

    def get_active_progresses(self, profile_id: int) -> list[BadgeProgressDTO]:
        """Zwraca listę wszystkich aktualnie subskrybowanych (śledzonych) odznak."""

    def get_progress(self, profile_id: int, badge_code: str, cycle_number: int = 1) -> BadgeProgressDTO | None:
        """Pobiera konkretny snapshot postępu."""

    def start_progress(self, profile_id: int, badge_code: str, version_id: int, cycle_number: int = 1) -> int:
        """Rozpoczyna zdobywanie (subskrypcję).

        Trwale zakotwicza turystę w wersji (Prawa Nabyte).
        """

    def update_domain_status(self, progress_id: int, status: str) -> None:
        """Zapisuje wynik wyliczony przez Czystą Domenę (np.

        IN_PROGRESS -> COMPLETED).
        """

    def update_logistic_status(self, progress_id: int, logistic_status: str, status_date: date) -> None:
        """Zapisuje przesunięcie odznaki w Osobistym Trackerze (np.

        WAITING_FOR_SEND).
        """

    def get_completed_badge_codes(self, profile_id: int) -> frozenset[str]:
        """Zwraca kody odznak ze statusem COMPLETED (optymalizacja dla PrerequisiteBadgeRule)."""

    def get_progress_by_id(self, profile_id: int, progress_id: int) -> BadgeProgressDTO | None:
        """Pobiera konkretny snapshot postępu po jego ID (weryfikując właściciela)."""

    def delete_progress(self, profile_id: int, badge_code: str) -> None:
        """Trwale usuwa subskrypcję odznaki (możliwe tylko dla niezakończonych)."""
