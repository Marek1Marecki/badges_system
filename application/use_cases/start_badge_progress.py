"""Przypadek użycia: Rozpoczęcie zdobywania odznaki (Subskrypcja).

Zgodnie z US-C05 (Prawa Nabyte) oraz Invariantem P-01: System automatycznie wyszukuje najstarszy log wejścia turysty dla
danej odznaki. Jeśli turysta wchodził na szczyty np. w 2018 roku, zostaje "zakotwiczony" w regulaminie z 2018 roku,
niezależnie od tego, że dzisiaj mamy nowszą wersję.
"""

from datetime import date

from application.exceptions import UseCaseError
from application.ports.badge_repository_port import BadgeRepositoryPort
from application.ports.clock_port import ClockPort
from application.ports.event_publisher_port import DomainEventPublisherPort
from application.ports.uow_port import UnitOfWorkPort
from application.ports.user_progress_port import (
    AscentLogRepositoryPort,
    TouristProfileRepositoryPort,
    UserProgressRepositoryPort,
)
from domain.events import UserProgressStateChanged


class StartBadgeProgressUseCase:
    """Zakotwicza turystę w odpowiedniej wersji regulaminu odznaki."""

    def __init__(
        self,
        progress_repository: UserProgressRepositoryPort,
        ascent_repository: AscentLogRepositoryPort,
        badge_repository: BadgeRepositoryPort,
        profile_repository: TouristProfileRepositoryPort,
        clock: ClockPort,
        uow: UnitOfWorkPort,
        event_publisher: DomainEventPublisherPort,
    ) -> None:
        """Inicjuje przypadek użycia usuwający subskrypcję odznaki."""
        self._progress_repo = progress_repository
        self._ascent_repo = ascent_repository
        self._badge_repo = badge_repository
        self._profile_repo = profile_repository
        self._clock = clock
        self._uow = uow
        self._event_publisher = event_publisher

    def execute(self, profile_id: int, badge_code: str, cycle_number: int = 1) -> int:
        """Rozpoczyna śledzenie postępu odznaki w 100% transakcyjnie.

        Args:
          profile_id: int:
          badge_code: str:
          cycle_number: int:  (Default value = 1)
          profile_id: int:
          badge_code: str:
          cycle_number: int:  (Default value = 1)

        Returns:

        """
        # 1. Walidacja Limitów (US-C01c)
        profile_dto = self._profile_repo.get_profile(profile_id)
        if not profile_dto:
            raise UseCaseError(f"Nie znaleziono profilu o ID {profile_id}.")

        active_progresses = self._progress_repo.get_active_progresses(profile_id)
        active_count = len(active_progresses)
        if active_count >= profile_dto.max_active_badges:
            raise UseCaseError(
                f"Przekroczono limit pakietu ({profile_dto.active_plan}). "
                f"Możesz zdobywać maksymalnie {profile_dto.max_active_badges} odznak jednocześnie."
            )

        # 2. Prawa Nabyte
        oldest_ascent_date = self._ascent_repo.get_oldest_ascent_date(profile_id, badge_code)
        anchor_date: date = oldest_ascent_date if oldest_ascent_date else self._clock.now().date()

        version_id = self._badge_repo.get_version_id_for_date(badge_code, anchor_date)
        if version_id is None:
            raise UseCaseError(
                f"Brak opublikowanej wersji regulaminu dla odznaki '{badge_code}' "
                f"w wyznaczonym dniu zakotwiczenia ({anchor_date})."
            )

        # 3. Transakcja Bazy i Publikacja Zdarzenia
        with self._uow:
            progress_id = self._progress_repo.start_progress(
                profile_id=profile_id,
                badge_code=badge_code,
                version_id=version_id,
                cycle_number=cycle_number,
            )
            self._event_publisher.publish(UserProgressStateChanged(profile_id=profile_id))

        return progress_id
