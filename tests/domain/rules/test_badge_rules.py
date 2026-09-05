"""Testy jednostkowe dla reguł biznesowych odznak."""

from datetime import UTC, date, datetime

import pytest

from domain.rules.badge_rules import (
    DateWindowRule,
    GroupedAlternativesRule,
    MandatoryObjectsRule,
    MaxAgeRule,
    MinAgeRule,
    MultiPoolRequirementRule,
    PrerequisiteBadgeRule,
    RegionCountRule,
    RequiresClubJoinDateRule,
    StartDateRule,
    SubPoolRequirement,
    TimeLimitRule,
)
from domain.value_objects.ascent import Ascent
from domain.value_objects.verification_context import VerificationContext


@pytest.fixture
def ctx() -> VerificationContext:
    """Standardowy kontekst weryfikacyjny dla testów."""
    return VerificationContext(
        evaluation_time=datetime(2026, 6, 1, tzinfo=UTC),
        tourist_birth_date=date(2010, 1, 1),
        club_join_dates={"PTTK": date(2020, 1, 1)},
        completed_badge_codes=frozenset(["KGP"]),
    )


def test_time_limit_rule(ctx: VerificationContext) -> None:
    """Weryfikuje regułę limitu czasowego wejść."""
    rule = TimeLimitRule(limit_in_years=2)
    valid_ascents = [
        Ascent(object_id=1, ascent_date=date(2020, 1, 1)),
        Ascent(object_id=2, ascent_date=date(2021, 12, 31)),
    ]
    invalid_ascents = [
        Ascent(object_id=1, ascent_date=date(2020, 1, 1)),
        Ascent(object_id=2, ascent_date=date(2022, 1, 2)),
    ]
    assert not rule.validate(valid_ascents, ctx)
    assert len(rule.validate(invalid_ascents, ctx)) == 1


def test_requires_club_join_date_rule(ctx: VerificationContext) -> None:
    """Weryfikuje regułę wymaganego członkostwa w klubie."""
    rule = RequiresClubJoinDateRule()
    valid_ascent = Ascent(object_id=1, ascent_date=date(2020, 1, 2))
    invalid_ascent = Ascent(object_id=1, ascent_date=date(2019, 12, 31))
    assert not rule.validate([valid_ascent], ctx)
    assert len(rule.validate([invalid_ascent], ctx)) == 1


def test_min_age_rule(ctx: VerificationContext) -> None:
    """Weryfikuje regułę minimalnego wieku."""
    rule = MinAgeRule(min_age=10)
    valid_ascent = Ascent(object_id=1, ascent_date=date(2021, 1, 1))  # 11 lat
    invalid_ascent = Ascent(object_id=1, ascent_date=date(2019, 1, 1))  # 9 lat
    assert not rule.validate([valid_ascent], ctx)
    assert len(rule.validate([invalid_ascent], ctx)) == 1


def test_max_age_rule(ctx: VerificationContext) -> None:
    """Weryfikuje regułę maksymalnego wieku."""
    rule = MaxAgeRule(max_age=15)
    valid_ascent = Ascent(object_id=1, ascent_date=date(2024, 1, 1))  # 14 lat
    invalid_ascent = Ascent(object_id=1, ascent_date=date(2026, 1, 1))  # 16 lat
    assert not rule.validate([valid_ascent], ctx)
    assert len(rule.validate([invalid_ascent], ctx)) == 1


def test_start_date_rule(ctx: VerificationContext) -> None:
    """Weryfikuje regułę daty rozpoczęcia."""
    rule = StartDateRule(start_date=date(2000, 1, 1))
    valid_ascent = Ascent(object_id=1, ascent_date=date(2001, 1, 1))
    invalid_ascent = Ascent(object_id=1, ascent_date=date(1999, 1, 1))
    assert not rule.validate([valid_ascent], ctx)
    assert len(rule.validate([invalid_ascent], ctx)) == 1


def test_mandatory_objects_rule(ctx: VerificationContext) -> None:
    """Weryfikuje regułę obowiązkowych szczytów."""
    rule = MandatoryObjectsRule(mandatory_peak_ids=frozenset([1, 2]))
    valid_ascents = [Ascent(object_id=1, ascent_date=date(2024, 6, 15)), Ascent(object_id=2, ascent_date=date(2024, 6, 15))]
    invalid_ascents = [Ascent(object_id=1, ascent_date=date(2024, 6, 15))]
    assert not rule.validate(valid_ascents, ctx)
    assert len(rule.validate(invalid_ascents, ctx)) == 1


def test_grouped_alternatives_rule(ctx: VerificationContext) -> None:
    """Weryfikuje regułę grupowanych alternatyw."""
    rule = GroupedAlternativesRule(groups=(frozenset([1, 2]), frozenset([3, 4])), min_groups_required=2)
    valid_ascents = [Ascent(object_id=1, ascent_date=date(2024, 6, 15)), Ascent(object_id=3, ascent_date=date(2024, 6, 15))]
    invalid_ascents = [
        Ascent(object_id=1, ascent_date=date(2024, 6, 15)),
        Ascent(object_id=2, ascent_date=date(2024, 6, 15)),
    ]
    assert not rule.validate(valid_ascents, ctx)
    assert len(rule.validate(invalid_ascents, ctx)) == 1


def test_multi_pool_requirement_rule(ctx: VerificationContext) -> None:
    """Weryfikuje regułę wymagań z wielu pul."""
    pool1 = SubPoolRequirement(required_count=2, peak_ids=frozenset([1, 2, 3]))
    pool2 = SubPoolRequirement(required_count=1, peak_ids=frozenset([4, 5]))
    rule = MultiPoolRequirementRule(pools=(pool1, pool2))

    valid_ascents = [
        Ascent(object_id=1, ascent_date=date(2024, 6, 15)),
        Ascent(object_id=2, ascent_date=date(2024, 6, 15)),
        Ascent(object_id=4, ascent_date=date(2024, 6, 15)),
    ]
    invalid_ascents = [
        Ascent(object_id=1, ascent_date=date(2024, 6, 15)),
        Ascent(object_id=4, ascent_date=date(2024, 6, 15)),
    ]
    assert not rule.validate(valid_ascents, ctx)
    assert len(rule.validate(invalid_ascents, ctx)) == 1


def test_prerequisite_badge_rule(ctx: VerificationContext) -> None:
    """Weryfikuje regułę wymaganej odznaki wstępnej."""
    rule = PrerequisiteBadgeRule(required_badge_code="KGP")
    rule_invalid = PrerequisiteBadgeRule(required_badge_code="INNA")

    assert not rule.validate([], ctx)
    assert len(rule_invalid.validate([], ctx)) == 1


def test_region_count_rule(ctx: VerificationContext) -> None:
    """Weryfikuje regułę liczby wejść w regionie."""
    rule = RegionCountRule(region_id=42, required_count=2)
    valid_ascents = [
        Ascent(object_id=1, ascent_date=date(2024, 6, 15), region_ids=frozenset([42, 10])),
        Ascent(object_id=2, ascent_date=date(2024, 6, 15), region_ids=frozenset([42])),
    ]
    invalid_ascents = [
        Ascent(object_id=1, ascent_date=date(2024, 6, 15), region_ids=frozenset([42, 10])),
        Ascent(object_id=3, ascent_date=date(2024, 6, 15), region_ids=frozenset([99])),
    ]
    assert not rule.validate(valid_ascents, ctx)
    assert len(rule.validate(invalid_ascents, ctx)) == 1


def test_date_window_rule(ctx: VerificationContext) -> None:
    """Weryfikuje regułę okna czasowego."""
    rule = DateWindowRule(start_date=date(2020, 1, 1), end_date=date(2020, 12, 31))
    valid_ascent = Ascent(object_id=1, ascent_date=date(2020, 6, 1))
    invalid_ascent = Ascent(object_id=1, ascent_date=date(2021, 1, 1))
    assert not rule.validate([valid_ascent], ctx)
    assert len(rule.validate([invalid_ascent], ctx)) == 1


def test_time_limit_rule_feb29_leap_year_edge_case() -> None:
    """Weryfikuje regułę limitu czasu dla 29 lutego w roku przestępnym."""
    rule = TimeLimitRule(limit_in_years=1)
    ascents = [Ascent(object_id=1, ascent_date=date(2020, 2, 29))]
    result = rule.validate(ascents, VerificationContext(evaluation_time=datetime(2020, 2, 29, tzinfo=UTC)))
    assert result == []
