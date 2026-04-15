"""Agregaty domenowe dla systemu odznak."""

from dataclasses import dataclass

from domain.exceptions import ValidationError
from domain.rules.badge_rules import BadgeRule
from domain.value_objects.ascent import Ascent


@dataclass
class BadgeVersionDomain:
    """Reprezentuje konkretny regulamin odznaki obowiązujący w czasie."""

    version_id: str
    rules: list[BadgeRule]
    pool_peak_ids: set[int]
    required_count: int

    def evaluate(self, ascents: list[Ascent]) -> None:
        """Waliduje listę wejść względem szczytów i reguł.

        Raises a `ValidationError` if any rules or peak conditions are not met.

        Args:
            ascents: Lista wejść do zweryfikowania.

        Raises:
            ValidationError: Jeśli jakakolwiek reguła lub warunek szczytów nie są spełnione.
        """
        climbed_peak_ids = {a.peak_id for a in ascents}
        valid_climbed_peaks = climbed_peak_ids.intersection(self.pool_peak_ids)

        if len(valid_climbed_peaks) < self.required_count:
            raise ValidationError(f"Wymagano {self.required_count} szczytów, masz {len(valid_climbed_peaks)}.")

        ascents_to_validate = [a for a in ascents if a.peak_id in self.pool_peak_ids]
        errors: list[str] = []

        for rule in self.rules:
            errors.extend(rule.validate(ascents_to_validate))

        if errors:
            raise ValidationError(" | ".join(errors))
