"""Przypadek użycia: Weryfikacja zdobycia odznaki (Silnik Postępu).

Zgodnie z US-C06: Oblicza postęp On-Demand.
Zgodnie z P-02 (EC-030): Odfiltrowuje zużyte wejścia z poprzednich cykli.
Zgodnie z TD-02: Wstrzykuje wiek i kluby turysty do Czystej Domeny.

Zawiera rozdzielone ścieżki (Command/Query Responsibility Segregation):
1. EvaluateBadgeProgressQuery - Tylko odczyt z pamięci RAM (bezpieczny dla GET).
2. UpdateBadgeProgressCommand - Wymuszenie fizycznego zapisu do bazy.
"""

from typing import Any

from application.exceptions import ResourceNotFoundError
from application.ports.badge_repository_port import BadgeRepositoryPort
from application.ports.clock_port import ClockPort
from application.ports.user_progress_port import (
    AscentLogRepositoryPort,
    TouristProfileRepositoryPort,
    UserProgressRepositoryPort,
)
from domain.value_objects.verification_context import VerificationContext
from domain.value_objects.verification_result import VerificationResult


class EvaluateBadgeProgressQuery:
    """Odczytuje aktualny stan i ewaluuje postęp matematyczny w locie bez zapisu do bazy."""

    def __init__(
        self,
        progress_repository: UserProgressRepositoryPort,
        ascent_repository: AscentLogRepositoryPort,
        profile_repository: TouristProfileRepositoryPort,
        badge_repository: BadgeRepositoryPort,
        clock: ClockPort,
    ) -> None:
        """Inicjalizuje serwis odczytu i oceny postępów turysty."""
        self._progress_repo = progress_repository
        self._ascent_repo = ascent_repository
        self._profile_repo = profile_repository
        self._badge_repo = badge_repository
        self._clock = clock

    def execute(self, profile_id: int, badge_code: str, cycle_number: int = 1) -> dict[str, Any]:
        """Weryfikuje status matematyczny w locie.

        Args:
          profile_id: int:
          badge_code: str:
          cycle_number: int:  (Default value = 1)
          profile_id: int:
          badge_code: str:
          cycle_number: int:  (Default value = 1)

        Returns:

        """
        # 1. Pobieramy postęp by mieć referencję do zakotwiczonej wersji (P-01)
        progress = self._progress_repo.get_progress(profile_id, badge_code, cycle_number)
        if not progress:
            raise ResourceNotFoundError(f"Turysta nie subskrybuje odznaki '{badge_code}'.")

        # 2. Jeśli nie ma wersji, próbujemy podpiąć najnowszą (do podglądu UI)
        target_version_id = progress.version_id
        if not target_version_id:
            # Używamy portu zwracającego bezpośrednio czysty INT z bazy
            today = self._clock.now().date()
            target_version_id = self._badge_repo.get_version_id_for_date(badge_code, today)

        # Upewniamy się, że version_id jest typu int przed wyszukaniem
        if not isinstance(target_version_id, int):
            raise ResourceNotFoundError("Brak zdefiniowanego regulaminu dla tej odznaki.")

        # 3. Pobieramy pełną domenę (regulaminy + stopnie)
        domain_badge_version = self._badge_repo.get_badge_version_by_id(target_version_id)
        if not domain_badge_version:
            raise ResourceNotFoundError("Nie udało się odtworzyć struktury odznaki.")

        # 4. Pobieramy logi (odcinając zużyte w poprzednich cyklach P-02)
        cutoff_date = None
        if cycle_number > 1:
            previous_progress = self._progress_repo.get_progress(profile_id, badge_code, cycle_number - 1)
            # Używamy poprawnego pola z DTO
            cutoff_date = previous_progress.logistic_status_date if previous_progress else None

        ascents_dto = self._ascent_repo.get_unconsumed_ascents(profile_id, badge_code, cutoff_date=cutoff_date)
        domain_ascents = [dto.to_domain() for dto in ascents_dto]

        # 5. Kontekst Weryfikacyjny
        profile_dto = self._profile_repo.get_profile(profile_id)
        context = VerificationContext(
            evaluation_time=self._clock.now(),
            tourist_birth_date=profile_dto.birth_date if profile_dto else None,
            club_join_dates=profile_dto.club_join_dates if profile_dto else {},
            completed_badge_codes=self._progress_repo.get_completed_badge_codes(profile_id),
        )

        # 6. Matematyka w Czystej Domenie (Bez Side Effectów!)
        domain_result: VerificationResult = domain_badge_version.evaluate(ascents=domain_ascents, context=context)

        # 7. Ochrona Praw Nabytych (Jeśli w bazie ma COMPLETED, nic mu tego nie zabierze)
        final_status = "COMPLETED" if progress.domain_status == "COMPLETED" else domain_result.status

        return {
            "verified": domain_result.verified if final_status != "COMPLETED" else True,
            "status": final_status,
            "valid_ascents_count": domain_result.valid_ascents_count,
            "errors": domain_result.errors,
            "tiers": [
                {
                    "tier_id": t.tier_id,
                    "name": t.name,
                    "status": t.status,
                    "required_count": t.required_count,
                }
                for t in domain_result.tiers
            ],
        }


class UpdateBadgeProgressCommand:
    """Aktualizuje stan odznaki w bazie na podstawie wyliczeń domeny."""

    def __init__(
        self, query_service: EvaluateBadgeProgressQuery, progress_repository: UserProgressRepositoryPort
    ) -> None:
        """Inicjalizuje komendę wymuszającą weryfikację i zapis postępów w bazie danych."""
        self._query_service = query_service
        self._progress_repo = progress_repository

    def execute(self, profile_id: int, badge_code: str, cycle_number: int = 1) -> None:
        """Przelicza i wymusza twardy zapis do bazy.

        Args:
          profile_id: int:
          badge_code: str:
          cycle_number: int:  (Default value = 1)
          profile_id: int:
          badge_code: str:
          cycle_number: int:  (Default value = 1)

        Returns:

        """
        progress = self._progress_repo.get_progress(profile_id, badge_code, cycle_number)
        if not progress:
            return

        result = self._query_service.execute(profile_id, badge_code, cycle_number)

        if result["status"] != progress.domain_status:
            self._progress_repo.update_domain_status(progress.progress_id, result["status"])
