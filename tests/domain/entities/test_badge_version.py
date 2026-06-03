"""Testy dla agregatów domenowych."""

from datetime import date
from unittest.mock import Mock

import pytest

from domain.entities.badge_version import BadgeVersionDomain
from domain.exceptions import ValidationError
from domain.rules.badge_rules import TimeLimitRule
from domain.value_objects.ascent import Ascent


class TestBadgeVersionDomain:
    """Testy klasy BadgeVersionDomain."""

    def test_evaluate_success_with_valid_ascents(self):
        """Test pomyślnej ewaluacji z poprawnymi wejściami."""
        rules = [
            TimeLimitRule(limit_in_years=2),
        ]
        pool_peak_ids = {1, 2, 3}
        badge_version = BadgeVersionDomain(
            version_id="v1",
            rules=rules,
            pool_peak_ids=pool_peak_ids,
            required_count=2,
        )

        ascents = [
            Ascent(peak_id=1, ascent_date=date(2023, 1, 1)),
            Ascent(peak_id=2, ascent_date=date(2023, 6, 1)),
        ]

        # Should not raise any exception
        badge_version.evaluate(ascents)

    def test_evaluate_fails_with_insufficient_peaks(self):
        """Test błędu przy niewystarczającej liczbie szczytów."""
        rules = [Mock()]
        rules[0].validate.return_value = []

        badge_version = BadgeVersionDomain(
            version_id="v1",
            rules=rules,
            pool_peak_ids={1, 2, 3},
            required_count=3,
        )

        ascents = [
            Ascent(peak_id=1, ascent_date=date(2023, 1, 1)),
            Ascent(peak_id=2, ascent_date=date(2023, 6, 1)),
        ]

        with pytest.raises(ValidationError, match="Wymagano 3 szczytów, masz 2"):
            badge_version.evaluate(ascents)

    def test_evaluate_ignores_peaks_outside_pool(self):
        """Test ignorowania szczytów spoza puli."""
        rules = []
        badge_version = BadgeVersionDomain(
            version_id="v1",
            rules=rules,
            pool_peak_ids={1, 2},
            required_count=1,
        )

        ascents = [
            Ascent(peak_id=1, ascent_date=date(2023, 1, 1)),
            Ascent(peak_id=99, ascent_date=date(2023, 6, 1)),
        ]

        # Should not raise because only peak_id=1 is in the pool and has valid activity
        badge_version.evaluate(ascents)

    def test_evaluate_with_multiple_rule_errors(self):
        """Test akumulacji wielu błędów reguł."""
        rules = [
            TimeLimitRule(limit_in_years=1),
        ]
        badge_version = BadgeVersionDomain(
            version_id="v1",
            rules=rules,
            pool_peak_ids={1, 2},
            required_count=2,
        )

        ascents = [
            Ascent(peak_id=1, ascent_date=date(2022, 1, 1)),
            Ascent(peak_id=2, ascent_date=date(2023, 6, 1)),
        ]

        with pytest.raises(ValidationError) as exc_info:
            badge_version.evaluate(ascents)

        error_message = str(exc_info.value)
        assert "Przekroczono limit czasu" in error_message

    def test_evaluate_with_empty_ascents_list(self):
        """Test ewaluacji z pustą listą wejść."""
        rules = [Mock()]
        rules[0].validate.return_value = []

        badge_version = BadgeVersionDomain(
            version_id="v1",
            rules=rules,
            pool_peak_ids={1, 2, 3},
            required_count=1,
        )

        with pytest.raises(ValidationError, match="Wymagano 1 szczytów, masz 0"):
            badge_version.evaluate([])

    def test_evaluate_with_duplicate_peaks(self):
        """Test ewaluacji z duplikatami szczytów."""
        rules = []
        badge_version = BadgeVersionDomain(
            version_id="v1",
            rules=rules,
            pool_peak_ids={1, 2},
            required_count=2,
        )

        ascents = [
            Ascent(peak_id=1, ascent_date=date(2023, 1, 1)),
            Ascent(peak_id=1, ascent_date=date(2023, 6, 1)),
            Ascent(peak_id=2, ascent_date=date(2023, 9, 1)),
        ]

        # Should succeed because we have both required peaks (1 and 2)
        badge_version.evaluate(ascents)
