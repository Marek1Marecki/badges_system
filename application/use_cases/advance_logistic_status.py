"""Przypadek użycia: Osobisty Tracker Logistyki (Kanban).

Zgodnie z US-C07, US-C08 i Invariantem S-03: Zarządza wyłącznie stanem logistycznym odznaki, pod warunkiem że
matematyczny stan z Czystej Domeny to COMPLETED.
"""

from datetime import date

from application.exceptions import ConflictError, UseCaseError
from application.ports.user_progress_port import UserProgressRepositoryPort

# Definicja dozwolonych przejść (Maszyna stanów Trackera B2C)
VALID_TRANSITIONS = {
    None: ["WAITING_FOR_SEND", "WAITING_FOR_VERIFICATION"],
    "WAITING_FOR_SEND": ["WAITING_FOR_VERIFICATION"],
    # Turysta może cofnąć pomyłkowe kliknięcie "Wysłano"
    "WAITING_FOR_VERIFICATION": ["WAITING_FOR_RECEIVING", "WAITING_FOR_SEND"],
    # Turysta może cofnąć pomyłkowe kliknięcie "Odebrano z PTTK"
    "WAITING_FOR_RECEIVING": ["ALBUM", "WAITING_FOR_VERIFICATION"],
    "ALBUM": ["WAITING_FOR_RECEIVING"],  # Opcjonalne wycofanie z albumu
}


class AdvanceLogisticStatusUseCase:
    """Zarządza logistyką fizycznych książeczek i blach (B2C Tracker)."""

    def __init__(self, progress_repository: UserProgressRepositoryPort) -> None:
        """Wstrzyknięty adapter do zarządzania postępowi turysty."""
        self._progress_repo = progress_repository

    def execute(self, profile_id: int, progress_id: int, new_logistic_status: str, status_date: date) -> None:
        """Przesuwa status logistyczny zdobytej odznaki.

        Args:
          profile_id: int:
          progress_id: int:
          new_logistic_status: str:
          status_date: date:
          profile_id: int:
          progress_id: int:
          new_logistic_status: str:
          status_date: date:

        Returns:

        Raises:
          UseCaseError: Gdy postęp nie istnieje lub nie należy do turysty.
          ConflictError: Gdy domena nie jest COMPLETED lub przejście FSM jest nielegalne.
        """
        # 1. Weryfikacja tożsamości i istnienia zasobu
        progress = self._progress_repo.get_progress_by_id(profile_id=profile_id, progress_id=progress_id)
        if not progress:
            raise UseCaseError(f"Postęp odznaki (ID: {progress_id}) nie istnieje lub brak dostępu.")

        # 2. Invariant S-03: Logistyka dostępna TYLKO dla matematycznie zdobytych odznak
        if progress.domain_status != "COMPLETED":
            raise ConflictError(
                "Nie można aktualizować logistyki dla odznaki, "
                "która nie spełniła jeszcze wymagań regulaminowych (Czysta Domena)."
            )

        # 3. Walidacja FSM (Maszyny Stanów)
        allowed_next = VALID_TRANSITIONS.get(progress.logistic_status, [])
        if new_logistic_status not in allowed_next:
            raise ConflictError(
                f"Niedozwolone przejście stanu logistycznego. "
                f"Nie można zmienić [{progress.logistic_status}] na [{new_logistic_status}]."
            )

        # 4. Zapis do bazy
        self._progress_repo.update_logistic_status(
            progress_id=progress.progress_id,
            logistic_status=new_logistic_status,
            status_date=status_date,
        )
