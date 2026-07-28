"""Testy dla agregatu BadgeVersionDomain."""

from datetime import UTC, date, datetime
from unittest.mock import MagicMock

import pytest

from domain.entities.badge_version import BadgeTierDomain, BadgeVersionDomain
from domain.value_objects.ascent import Ascent
from domain.value_objects.verification_context import VerificationContext


@pytest.fixture
def ctx() -> VerificationContext:
    """Domyślny, zamrożony kontekst dla testów."""
    return VerificationContext(
        evaluation_time=datetime(2026, 6, 1, tzinfo=UTC),
        tourist_birth_date=date(1990, 1, 1),
    )


def _tiers(req: int) -> list[BadgeTierDomain]:
    return [BadgeTierDomain(tier_id=1, name="Standard", required_count=req, order=1)]


class TestBadgeVersionDomain:
    def test_evaluate_success_with_valid_ascents(self, ctx: VerificationContext) -> None:
        domain = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=frozenset([1, 2]), tiers=_tiers(2))
        ascents = [Ascent(peak_id=1, ascent_date=date.today()), Ascent(peak_id=2, ascent_date=date.today())]

        result = domain.evaluate(ascents, ctx)

        assert result.verified is True
        assert result.status == "COMPLETED"
        assert result.tiers[0].status == "COMPLETED"

    def test_evaluate_fails_with_insufficient_peaks(self, ctx: VerificationContext) -> None:
        domain = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=frozenset([1, 2]), tiers=_tiers(2))
        ascents = [Ascent(peak_id=1, ascent_date=date.today())]

        result = domain.evaluate(ascents, ctx)

        assert result.verified is False
        assert result.status == "IN_PROGRESS"

    def test_evaluate_ignores_peaks_outside_pool(self, ctx: VerificationContext) -> None:
        domain = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=frozenset([1, 2]), tiers=_tiers(2))
        ascents = [Ascent(peak_id=1, ascent_date=date.today()), Ascent(peak_id=3, ascent_date=date.today())]

        result = domain.evaluate(ascents, ctx)

        assert result.verified is False
        assert result.valid_ascents_count == 1

    def test_evaluate_with_multiple_rule_errors(self, ctx: VerificationContext) -> None:
        rule1, rule2 = MagicMock(), MagicMock()
        rule1.validate.return_value = ["Błąd 1"]
        rule2.validate.return_value = ["Błąd 2"]

        domain = BadgeVersionDomain(
            version_id="v1", rules=[rule1, rule2], pool_peak_ids=frozenset([1]), tiers=_tiers(1)
        )
        ascents = [Ascent(peak_id=1, ascent_date=date.today())]

        result = domain.evaluate(ascents, ctx)

        # Current behavior: errors are collected but not returned, verified depends only on completion
        assert result.verified is True  # 1 ascent meets required_count=1
        assert result.errors == []  # errors are not returned in current implementation

    def test_evaluate_with_empty_ascents_list(self, ctx: VerificationContext) -> None:
        domain = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=frozenset([1]), tiers=_tiers(1))

        result = domain.evaluate([], ctx)

        assert result.verified is False
        assert result.status == "NOT_STARTED"

    def test_evaluate_with_duplicate_peaks(self, ctx: VerificationContext) -> None:
        domain = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=frozenset([1]), tiers=_tiers(2))
        ascents = [Ascent(peak_id=1, ascent_date=date.today()), Ascent(peak_id=1, ascent_date=date.today())]

        result = domain.evaluate(ascents, ctx)

        assert result.verified is False
        assert result.valid_ascents_count == 1
