"""Przypadek użycia: Osobisty Tracker Logistyki (Kanban).

Zgodnie z US-C07, US-C08 i Invariantem S-03: Zarządza wyłącznie stanem logistycznym odznaki, pod warunkiem że
matematyczny stan z Czystej Domeny to COMPLETED.
"""

from datetime import date

from application.exceptions import IllegalStateTransitionError, UseCaseError
from application.ports.event_publisher_port import DomainEventPublisherPort
from application.ports.user_progress_port import UserProgressRepositoryPort
from domain.enums import DomainStatus, LogisticStatus
from domain.events import BadgeStatusChanged

# Definicja dozwolonych przejść (Maszyna stanów Trackera B2C)
# Klucze i wartości używają centralnych Enumów (AUDYT-136: brak magic strings)
VALID_TRANSITIONS: dict[LogisticStatus | None, list[LogisticStatus]] = {
    None: [LogisticStatus.WAITING_FOR_SEND, LogisticStatus.WAITING_FOR_VERIFICATION],
    LogisticStatus.WAITING_FOR_SEND: [LogisticStatus.WAITING_FOR_VERIFICATION],
    LogisticStatus.WAITING_FOR_VERIFICATION: [
        LogisticStatus.WAITING_FOR_RECEIVING,
        LogisticStatus.WAITING_FOR_SEND,
    ],
    LogisticStatus.WAITING_FOR_RECEIVING: [LogisticStatus.ALBUM, LogisticStatus.WAITING_FOR_VERIFICATION],
    LogisticStatus.ALBUM: [LogisticStatus.WAITING_FOR_RECEIVING],
}


class AdvanceLogisticStatusUseCase:
    """Zarządza logistyką fizycznych książeczek i blach (B2C Tracker)."""

    def __init__(
        self,
        progress_repository: UserProgressRepositoryPort,
        event_publisher: DomainEventPublisherPort,
    ) -> None:
        """Inicjalizuje przypadek użycia logistyki Kanban."""
        self._progress_repo = progress_repository
        self._event_publisher = event_publisher

    def execute(
        self,
        profile_id: int,
        progress_id: int,
        new_logistic_status: LogisticStatus,
        status_date: date,
        actor_user_id: int,
    ) -> None:
        """Przesuwa status logistyczny zdobytej odznaki.

        Args:
          profile_id: ID profilu turysty.
          progress_id: ID postępu odznaki.
          new_logistic_status: Nowy status logistyczny (enum).
          status_date: Data zmiany statusu.
          actor_user_id: ID użytkownika (User) wykonującego akcję — dla audit trailu.

        Returns:
          None.

        Raises:
          UseCaseError: Gdy postęp nie istnieje lub nie należy do turysty.
          IllegalStateTransitionError: Gdy domena nie jest COMPLETED (S-03)
            lub przejście FSM jest nielegalne (Kanban). AUDYT-018.
        """
        progress = self._progress_repo.get_progress_by_id(profile_id=profile_id, progress_id=progress_id)
        if not progress:
            raise UseCaseError(f"Postęp odznaki (ID: {progress_id}) nie istnieje lub brak dostępu.")

        # 2. Invariant S-03: Logistyka dostępna TYLKO dla matematycznie zdobytych odznak
        if progress.domain_status != DomainStatus.COMPLETED:
            raise IllegalStateTransitionError(
                "Nie można aktualizować logistyki dla odznaki, "
                "która nie spełniła jeszcze wymagań regulaminowych (Czysta Domena)."
            )

        # 3. Walidacja FSM (Maszyny Stanów)
        current_status = LogisticStatus(progress.logistic_status) if progress.logistic_status else None
        allowed_next = VALID_TRANSITIONS.get(current_status, [])
        if new_logistic_status not in allowed_next:
            raise IllegalStateTransitionError(
                f"Niedozwolone przejście stanu logistycznego. "
                f"Nie można zmienić [{progress.logistic_status}] na [{new_logistic_status}]."
            )

        # 4. Zapis do bazy + audit trail (AUDYT-051)
        self._progress_repo.update_logistic_status(
            progress_id=progress.progress_id,
            logistic_status=new_logistic_status,
            status_date=status_date,
        )
        self._event_publisher.publish(
            BadgeStatusChanged(
                actor_user_id=actor_user_id,
                badge_code=progress.badge_code,
                version_code=str(progress.version_id),
                new_status=new_logistic_status,
                reason="Kanban transition",
            )
        )
