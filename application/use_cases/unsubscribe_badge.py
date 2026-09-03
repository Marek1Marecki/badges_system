"""Przypadek użycia: Porzucenie odznaki (US-C01b)."""

from application.exceptions import ConflictError, UseCaseError
from application.ports.event_publisher_port import DomainEventPublisherPort
from application.ports.uow_port import UnitOfWorkPort
from application.ports.user_progress_port import UserProgressRepositoryPort
from domain.enums import DomainStatus
from domain.events import UserProgressStateChanged


class UnsubscribeBadgeUseCase:
    """Pozwala na usunięcie subskrypcji odznaki przez turystę."""

    def __init__(
        self,
        progress_repository: UserProgressRepositoryPort,
        uow: UnitOfWorkPort,
        event_publisher: DomainEventPublisherPort,
    ) -> None:
        """Inicjuje przypadek użycia usuwania subskrypcji odznaki z bazy danych."""
        self._progress_repo = progress_repository
        self._uow = uow
        self._event_publisher = event_publisher

    def execute(self, profile_id: int, badge_code: str) -> None:
        """Kasuje subskrypcję i inwaliduje cache mapy.

        Args:
          profile_id: ID profilu turysty.
          badge_code: Kod odznaki do usunięcia.

        Returns:
          None.
        """
        progress = self._progress_repo.get_progress(profile_id, badge_code, 1)
        if not progress:
            raise UseCaseError(f"Nie subskrybujesz odznaki {badge_code}.")

        if progress.domain_status == DomainStatus.COMPLETED or progress.logistic_status is not None:
            raise ConflictError("Nie można porzucić odznaki, która została ukończona.")

        # Atomowa transakcja
        with self._uow:
            self._progress_repo.delete_progress(profile_id, badge_code)
            # System sam dowie się, że postęp się zmienił (zniknął) i wyczyści kolory
            self._event_publisher.publish(UserProgressStateChanged(profile_id=profile_id))
