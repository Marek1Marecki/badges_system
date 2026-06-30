"""Przypadek użycia: Weryfikacja zdobycia odznaki (Silnik Postępu).

Zgodnie z US-C06: Oblicza postęp On-Demand.
Zgodnie z P-02 (EC-030): Odfiltrowuje zużyte wejścia z poprzednich cykli.
Zgodnie z TD-02: Wstrzykuje wiek i kluby turysty do Czystej Domeny.
"""

from typing import Any

from application.dto.verify_badge_dto import VerifyBadgeRequestDTO
from application.exceptions import ResourceNotFoundError, UseCaseError
from application.ports.badge_repository_port import BadgeRepositoryPort
from application.ports.clock_port import ClockPort
from application.ports.user_progress_port import (
    AscentLogRepositoryPort,
    TouristProfileRepositoryPort,
    UserProgressRepositoryPort,
)
from domain.value_objects.verification_context import VerificationContext


class VerifyBadgeUseCase:
    """Orkiestruje ostateczny proces weryfikacji odznaki w oparciu o stan bazy."""

    def __init__(
        self,
        progress_repository: UserProgressRepositoryPort,
        ascent_repository: AscentLogRepositoryPort,
        profile_repository: TouristProfileRepositoryPort,
        badge_repository: BadgeRepositoryPort,
        clock: ClockPort,
    ) -> None:
        """Wstrzykuje repozytoria portów oraz deterministyczny zegar."""
        self._progress_repo = progress_repository
        self._ascent_repo = ascent_repository
        self._profile_repo = profile_repository
        self._badge_repo = badge_repository
        self._clock = clock

    def execute(self, request: VerifyBadgeRequestDTO) -> dict[str, Any]:
        """Przeprowadza weryfikację logów wejść z bazy danych."""
        # 1. Pobieramy "Zakotwiczenie" turysty (Prawa Nabyte)
        progress = self._progress_repo.get_progress(
            profile_id=request.profile_id, badge_code=request.badge_code, cycle_number=request.cycle_number
        )
        if not progress:
            # ResourceNotFoundError → 404 przez middleware
            raise ResourceNotFoundError(f"Turysta nie subskrybuje odznaki {request.badge_code}.")

        if not progress.version_id:
            return {"verified": False, "status": "NOT_STARTED", "errors": [], "valid_ascents_count": 0}

        # 2. Pobieramy Czystą Domenę z bazy
        badge_version = self._badge_repo.get_badge_version_by_id(progress.version_id)
        if not badge_version:
            raise UseCaseError("Regulamin przypisany do tej odznaki nie istnieje w bazie.")

        # 3. Pobieramy profil turysty (Wiek, Kluby)
        profile = self._profile_repo.get_profile(request.profile_id)
        birth_date = profile.birth_date if profile else None
        club_dates = profile.club_join_dates if profile else {}

        # 4. Ustalamy "Ocięcie" logów dla Pętli Prestiżu (Invariant P-02)
        cutoff_date = None
        if request.cycle_number > 1:
            prev_cycle = self._progress_repo.get_progress(
                request.profile_id, request.badge_code, request.cycle_number - 1
            )
            # Jeśli poprzedni cykl jest zamknięty, odcinamy stare logi po dacie zamknięcia
            if prev_cycle and prev_cycle.logistic_status_date:
                cutoff_date = prev_cycle.logistic_status_date

        # 5. Pobieramy "Niezużyte" logi z bazy
        ascents_dto = self._ascent_repo.get_unconsumed_ascents(
            profile_id=request.profile_id,
            badge_code=request.badge_code,
            cutoff_date=cutoff_date,
        )
        domain_ascents = [dto.to_domain() for dto in ascents_dto]

        # 6. Budujemy kontekst weryfikacyjny (Wstrzyknięcie Czasu i Stanu)
        context = VerificationContext(
            evaluation_time=self._clock.now(),
            tourist_birth_date=birth_date,
            club_join_dates=club_dates,
            completed_badge_codes=self._get_completed_badges(request.profile_id),
        )

        # 7. EWALUACJA W CZYSTEJ DOMENIE
        result = badge_version.evaluate(domain_ascents, context)

        # =========================================================
        # 7b. PRAWA NABYTE: Retroaktywne odbieranie odznak (Dylemat 2)
        # =========================================================
        # Jeśli turysta w przeszłości zdobył odznakę, a zmiana profilu
        # (np. dodanie daty urodzenia) nagle spowodowała błąd reguły wieku,
        # system szanuje historię i wymusza zachowanie statusu COMPLETED.
        if progress.domain_status == "COMPLETED":
            result["status"] = "COMPLETED"
            result["verified"] = True
            result["errors"] = []
            for tier in result.get("tiers", []):
                tier["status"] = "COMPLETED"

        # 8. Zapisujemy zmaterializowany wynik w bazie
        new_status = result["status"]
        if new_status != progress.domain_status:
            self._progress_repo.update_domain_status(progress.progress_id, new_status)

        return result

    def _get_completed_badges(self, profile_id: int) -> frozenset[str]:
        """Pobiera kody odznak, które turysta ukończył."""
        progresses = self._progress_repo.get_active_progresses(profile_id)
        return frozenset(p.badge_code for p in progresses if p.domain_status == "COMPLETED")
