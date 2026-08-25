"""Porty (Kontrakty) zarządzania użytkownikiem i jego wejściami.

Zgodnie z 22-ports-adapters-dto-contract.md: Porty te są implementowane w infrastructure/adapters/, a wywoływane w
application/use_cases/. Nie zawierają importów z Django.
"""

from datetime import date
from typing import Protocol

from application.dto.ascent_dto import AscentDTO, AscentInputDTO
from application.dto.user_context_dto import BadgeProgressDTO, TouristProfileDTO


class TouristProfileRepositoryPort(Protocol):
    """Port dostarczający dane o wieku i limitach turysty."""

    def get_profile(self, profile_id: int) -> TouristProfileDTO | None:
        """Pobiera pełen, połączony profil (z limitami).

        Zwraca None, jeśli nie istnieje.
                Args:
                  profile_id: int:
                  profile_id: int:

                Returns:
        """
        ...


class AscentLogRepositoryPort(Protocol):
    """Port obsługujący fizyczny dziennik wejść w oparciu o bitemporalność."""

    def get_object_lifespan(self, peak_id: int) -> tuple[date | None, date | None] | None:
        """Pobiera okno istnienia obiektu turystycznego.

        Zwraca `(existence_start, existence_end)`. `None` w dacie oznacza brak
        ograniczenia czasowego, a `None` jako wynik oznacza brak obiektu.

        Args:
          peak_id: int:
          peak_id: int:

        Returns:
        """
        ...

    def ascent_exists(self, profile_id: int, peak_id: int, ascent_date: date) -> bool:
        """Sprawdza, czy turysta posiada już log wejścia na ten obiekt w tym dniu (Upsert).

        Args:
          profile_id: int:
          peak_id: int:
          ascent_date: date:
          profile_id: int:
          peak_id: int:
          ascent_date: date:

        Returns:
        """
        ...

    def get_oldest_ascent_date(self, profile_id: int, badge_code: str) -> date | None:
        """Zwraca datę najstarszego wpisu dla danej odznaki (potrzebne do Praw Nabytych).

        Args:
          profile_id: int:
          badge_code: str:
          profile_id: int:
          badge_code: str:

        Returns:
        """
        ...

    def save_ascent(self, profile_id: int, peak_id: int, ascent_date: date) -> int:
        """Zapisuje wejście.

        Args:
          profile_id: int:
          peak_id: int:
          ascent_date: date:
          profile_id: int:
          peak_id: int:
          ascent_date: date:

        Returns:
        """
        ...

    def get_unconsumed_ascents(self, profile_id: int, badge_code: str, cutoff_date: date | None) -> list[AscentDTO]:
        """Pobiera wejścia turysty.

        Jeśli podano cutoff_date (data zamknięcia poprzedniego cyklu odznaki),
        odfiltrowuje wejścia 'zużyte' (starsze lub równe tej dacie).
        Zwrócone AscentDTO może posiadać wstrzyknięte regiony CQRS (Dla Wildcard Rules).

        Args:
          profile_id: int:
          badge_code: str:
          cutoff_date: date | None:
          profile_id: int:
          badge_code: str:
          cutoff_date: date | None:

        Returns:
        """
        ...

    def get_all_ascents_for_user(self, profile_id: int) -> list[AscentDTO]:
        """Pobiera całą, niefiltrowaną historię wejść turysty na potrzeby oceny kolorów.

        Args:
          profile_id: int:
          profile_id: int:

        Returns:
        """
        ...

    def get_objects_lifespans(self, peak_ids: set[int]) -> dict[int, tuple[date | None, date | None]]:
        """Pobiera bitemporalne ramy życia dla wielu obiektów naraz (Optymalizacja N+1).

        Zwraca słownik: {peak_id: (existence_start, existence_end)}

        Args:
          peak_ids: set[int]:
          peak_ids: set[int]:

        Returns:
        """
        ...

    def bulk_save_ascents(self, profile_id: int, ascents: list[AscentInputDTO]) -> int:
        """Masowo zapisuje wejścia.

        Ignoruje duplikaty (Idempotentność D-04).
        Zwraca liczbę faktycznie dodanych nowych rekordów.

        Args:
          profile_id: int:
          ascents: list[AscentInputDTO]:
          profile_id: int:
          ascents: list[AscentInputDTO]:

        Returns:
        """
        ...


class UserProgressRepositoryPort(Protocol):
    """Port obsługujący subskrypcje, Prawa Nabyte i Osobisty Kanban."""

    def get_active_progresses(self, profile_id: int) -> list[BadgeProgressDTO]:
        """Zwraca listę wszystkich aktualnie subskrybowanych (śledzonych) odznak.

        Args:
          profile_id: int:
          profile_id: int:

        Returns:
        """
        ...

    def get_progress(self, profile_id: int, badge_code: str, cycle_number: int = 1) -> BadgeProgressDTO | None:
        """Pobiera konkretny snapshot postępu.

        Args:
          profile_id: int:
          badge_code: str:
          cycle_number: int:  (Default value = 1)
          profile_id: int:
          badge_code: str:
          cycle_number: int:  (Default value = 1)

        Returns:

        """
        ...

    def start_progress(self, profile_id: int, badge_code: str, version_id: int, cycle_number: int = 1) -> int:
        """Rozpoczyna zdobywanie (subskrypcję). Trwale zakotwicza turystę w wersji (Prawa Nabyte).

        Args:
          profile_id: int:
          badge_code: str:
          version_id: int:
          cycle_number: int:  (Default value = 1)
          profile_id: int:
          badge_code: str:
          version_id: int:
          cycle_number: int:  (Default value = 1)

        Returns:

        """
        ...

    def update_domain_status(self, progress_id: int, status: str) -> None:
        """Zapisuje wynik wyliczony przez Czystą Domenę (np.

        IN_PROGRESS -> COMPLETED).
                Args:
                  progress_id: int:
                  status: str:
                  progress_id: int:
                  status: str:

                Returns:
        """
        ...

    def update_logistic_status(self, progress_id: int, logistic_status: str, status_date: date) -> None:
        """Zapisuje przesunięcie odznaki w Osobistym Trackerze (np.

        WAITING_FOR_SEND).
                Args:
                  progress_id: int:
                  logistic_status: str:
                  status_date: date:
                  progress_id: int:
                  logistic_status: str:
                  status_date: date:

                Returns:
        """
        ...

    def get_completed_badge_codes(self, profile_id: int) -> frozenset[str]:
        """Zwraca kody odznak ze statusem COMPLETED (optymalizacja dla PrerequisiteBadgeRule).

        Args:
          profile_id: int:
          profile_id: int:

        Returns:
        """
        ...

    def get_progress_by_id(self, profile_id: int, progress_id: int) -> BadgeProgressDTO | None:
        """Pobiera konkretny snapshot postępu po jego ID (weryfikując właściciela).

        Args:
          profile_id: int:
          progress_id: int:
          profile_id: int:
          progress_id: int:

        Returns:
        """
        ...

    def delete_progress(self, profile_id: int, badge_code: str) -> None:
        """Trwale usuwa subskrypcję odznaki (możliwe tylko dla niezakończonych).

        Args:
          profile_id: int:
          badge_code: str:
          profile_id: int:
          badge_code: str:

        Returns:
        """
        ...
