"""Przypadek użycia: Rezygnacja ze zdobywania odznaki (Unsubscribe)."""

from application.exceptions import ConflictError, ResourceNotFoundError
from application.ports.user_progress_port import UserProgressRepositoryPort


class UnsubscribeBadgeUseCase:
    """Pozwala na usunięcie subskrypcji i zwolnienie limitu Freemium."""

    def __init__(self, progress_repository: UserProgressRepositoryPort) -> None:
        """Inicjalizuje use case z repozytorium postępu."""
        self._progress_repo = progress_repository

    def execute(self, profile_id: int, badge_code: str) -> None:
        """Usuwa postęp, trwale kasując Prawa Nabyte do przypisanego regulaminu."""
        progress = self._progress_repo.get_progress(profile_id, badge_code)
        if not progress:
            raise ResourceNotFoundError(f"Turysta nie subskrybuje odznaki {badge_code}.")

        # OCHRONA HISTORII: Jeśli odznaka ma status COMPLETED, jest już zablokowana.
        # Nawet jeśli turysta nie ma jeszcze blachy (jest w kanbanie), nie pozwalamy tego zniszczyć.
        if progress.domain_status == "COMPLETED":
            raise ConflictError(
                "Nie można porzucić odznaki, która została już w pełni skompletowana. "
                "Czeka na Ciebie w Osobistym Kanbanie Logistycznym!"
            )

        self._progress_repo.delete_progress(profile_id, badge_code)
