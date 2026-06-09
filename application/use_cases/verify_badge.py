"""Przypadek użycia: Weryfikacja wejść na poczet odznaki."""

from application.dto.verify_badge_dto import VerifyBadgeRequestDTO
from application.exceptions import UseCaseError
from application.ports.badge_repository_port import BadgeRepositoryPort
from domain.exceptions import ValidationError


class VerifyBadgeUseCase:
    """Orkiestruje proces sprawdzania logów turysty względem regulaminu."""

    def __init__(self, repository: BadgeRepositoryPort) -> None:
        """Inicjalizuje przypadek użycia.

        Args:
            repository: Wstrzyknięty adapter komunikujący się z bazą danych.
        """
        self._repository = repository

    def execute(self, request: VerifyBadgeRequestDTO) -> dict[str, str | bool]:
        """Uruchamia weryfikację.

        Zwraca status weryfikacji lub informacje o błędach.
        """
        badge_version = self._repository.get_badge_version(request.badge_code, request.version_code)

        if not badge_version:
            raise UseCaseError(f"Nie znaleziono odznaki: {request.badge_code} ({request.version_code})")

        domain_ascents = [dto.to_domain() for dto in request.ascents]

        try:
            badge_version.evaluate(domain_ascents)
        except ValidationError as e:
            # Tłumaczymy błąd domenowy na bezpieczny wynik biznesowy
            return {"verified": False, "message": str(e)}

        return {"verified": True, "message": "Gratulacje! Odznaka przyznana."}
