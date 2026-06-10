"""Agregat domenowy Wersji Odznaki.

Odpowiada za ewaluację zgłoszonych wejść (Sito Domenowe) względem puli
oraz reguł biznesowych zdefiniowanych w tej wersji regulaminu.
"""

from dataclasses import dataclass
from typing import Any

from domain.rules.badge_rules import BadgeRule
from domain.value_objects.ascent import Ascent
from domain.value_objects.verification_context import VerificationContext


@dataclass(frozen=True)
class BadgeVersionDomain:
    """Sito weryfikacyjne dla konkretnego rocznika regulaminu."""

    version_id: str | int
    rules: list[BadgeRule]
    pool_peak_ids: frozenset[int]
    required_count: int | None = None

    def evaluate(self, ascents: list[Ascent], context: VerificationContext) -> dict[str, Any]:
        """Ocenia matematyczny postęp turysty w tej wersji odznaki.

        Args:
            ascents: Historia wejść turysty (przefiltrowana z już zużytych cykli).
            context: Kontekst z wiekiem turysty i datą ewaluacji.

        Returns:
            Słownik ze statusem weryfikacji.
        """
        # 1. Sito przestrzenne (Odrzucenie szczytów spoza Menu)
        if self.pool_peak_ids:
            valid_ascents = [a for a in ascents if a.peak_id in self.pool_peak_ids]
        else:
            valid_ascents = ascents.copy()

        # Zabezpieczenie przed duplikatami wejść na ten sam szczyt
        unique_ascents = []
        seen_peaks = set()
        for a in sorted(valid_ascents, key=lambda x: x.ascent_date):
            if a.peak_id not in seen_peaks:
                unique_ascents.append(a)
                seen_peaks.add(a.peak_id)

        errors = []

        # 2. Sito Reguł Biznesowych (Wzorzec Strategii + Wstrzyknięty Kontekst!)
        for rule in self.rules:
            rule_errors = rule.validate(unique_ascents, context)
            errors.extend(rule_errors)

        if errors:
            return {
                "verified": False,
                "status": "NOT_STARTED" if not unique_ascents else "IN_PROGRESS",
                "errors": errors,
                "valid_ascents_count": len(unique_ascents),
            }

        # 3. Ewaluacja Ilościowa (Stopnie)
        climbed_count = len(unique_ascents)
        target = self.required_count if self.required_count is not None else len(self.pool_peak_ids)
        is_completed = climbed_count >= target

        return {
            "verified": is_completed,
            "status": "COMPLETED" if is_completed else ("IN_PROGRESS" if climbed_count > 0 else "NOT_STARTED"),
            "errors": [],
            "valid_ascents_count": climbed_count,
            "required_count": target,
        }
