"""Agregat domenowy Wersji Odznaki.

Odpowiada za ewaluację zgłoszonych wejść (Sito Domenowe) względem puli, reguł biznesowych zdefiniowanych w tej wersji
regulaminu oraz progów stopni.
"""

from dataclasses import dataclass
from typing import cast

from domain.enums import AscentLifecycle, DomainStatus
from domain.rules.badge_rules import BadgeRule
from domain.value_objects.ascent import Ascent
from domain.value_objects.ascent_status import AscentStatus
from domain.value_objects.verification_context import VerificationContext
from domain.value_objects.verification_result import TierResult, VerificationResult


@dataclass(frozen=True)
class BadgeTierDomain:
    """Definicja stopnia odznaki (Kamień Milowy) wewnątrz domeny."""

    tier_id: int
    name: str
    required_count: int
    order: int

    def status_for(self, climbed_count: int) -> DomainStatus:
        """Ocenia status tego stopnia dla danej liczby wejść.

        Chronologiczna ścieżka: NOT_STARTED → IN_PROGRESS → COMPLETED.
        """
        if climbed_count >= self.required_count:
            return DomainStatus.COMPLETED
        if climbed_count > 0:
            return DomainStatus.IN_PROGRESS
        return DomainStatus.NOT_STARTED


@dataclass(frozen=True)
class BadgeVersionDomain:
    """Sito weryfikacyjne dla konkretnego rocznika regulaminu."""

    version_id: str | int
    rules: list[BadgeRule]
    pool_peak_ids: frozenset[int]
    tiers: list[BadgeTierDomain]  # <--- ZMIANA: Lista stopni zamiast jednego inta

    def evaluate(self, ascents: list[Ascent], context: VerificationContext) -> VerificationResult:
        """Ocenia matematyczny postęp turysty w tej wersji odznaki.

        Zwraca ogólny status oraz szczegółową listę postępów dla każdego stopnia.

        Args:
          ascents: Lista wejść turysty na szczyty.
          context: Kontekst weryfikacyjny.

        Returns:
          Wynik weryfikacji ze statusem i szczegółami stopni.
        """
        # Sito przestrzeni (Odrzucenie szczytów spoza Menu)
        if self.pool_peak_ids:
            valid_ascents = [a for a in ascents if a.object_id in self.pool_peak_ids]
        else:
            valid_ascents = ascents.copy()

        # Zabezpieczenie przed duplikatami wejść na ten sam szczyt
        unique_ascents: list[Ascent] = []
        seen_peaks: set[int] = set()
        for a in sorted(valid_ascents, key=lambda x: x.ascent_date):
            if a.object_id not in seen_peaks:
                unique_ascents.append(a)
                seen_peaks.add(a.object_id)

        # AUDYT-099: Raport każdego wejścia + status (ACTIVE / ORPHANED)
        ascents_with_status: list[AscentStatus] = []
        valid_obj_ids: set[int] = set()
        for a in unique_ascents:
            ascents_with_status.append(
                AscentStatus(
                    object_id=a.object_id,
                    ascent_date=a.ascent_date,
                    lifecycle=AscentLifecycle.ACTIVE,
                    points=1,
                )
            )
            valid_obj_ids.add(a.object_id)

        # Wejścia poza pulą (ORPHANED) — AUDYT-099 Opcja C (Grandfather's Bin)
        for a in ascents:
            if a.object_id not in valid_obj_ids:
                ascents_with_status.append(
                    AscentStatus(
                        object_id=a.object_id,
                        ascent_date=a.ascent_date,
                        lifecycle=AscentLifecycle.ORPHANED,
                        points=0,
                    )
                )

        errors: list[str] = []

        # Sito Reguł Biznesowych (Wzorzec Strategii)
        for rule in self.rules:
            rule_errors = rule.validate(unique_ascents, context)
            errors.extend(rule_errors)

        climbed_count = len(unique_ascents)

        # Ewaluacja Stopni (Tiers)
        sorted_tiers = sorted(self.tiers, key=lambda t: t.order)
        evaluated_tiers: list[dict] = []
        all_completed = True

        if sorted_tiers:
            for t in sorted_tiers:
                t_status = t.status_for(climbed_count)
                if t_status != DomainStatus.COMPLETED:
                    all_completed = False

                evaluated_tiers.append(
                    {
                        "tier_id": t.tier_id,
                        "name": t.name,
                        "status": t_status,
                        "required_count": t.required_count,
                    }
                )
        else:
            # Fallback bezpieczeństwa: jeśli admin zapomniał dodać stopnie, wymaga 100% puli
            target = len(self.pool_peak_ids)
            all_completed = climbed_count >= target

        global_status = (
            DomainStatus.COMPLETED
            if all_completed
            else (DomainStatus.IN_PROGRESS if climbed_count > 0 else DomainStatus.NOT_STARTED)
        )

        # Transformacja wyników stopni na nowe obiekty
        tier_results = []
        for tier_dict in evaluated_tiers:
            # Wymuszamy typowanie dla poszczególnych elementów przed przekazaniem
            t_id = int(str(tier_dict["tier_id"]))
            t_name = str(tier_dict["name"])
            t_status = cast(DomainStatus, tier_dict["status"])
            t_req = int(str(tier_dict["required_count"]))

            tier_results.append(TierResult(tier_id=t_id, name=t_name, status=t_status, required_count=t_req))

        return VerificationResult(
            verified=all_completed,
            status=global_status,
            valid_ascents_count=climbed_count,
            errors=errors,
            tiers=tier_results,
            ascents_with_status=ascents_with_status,
        )
