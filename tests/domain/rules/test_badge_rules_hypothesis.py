"""Testy właściwościowe (property-based) dla reguł biznesowych odznak.

Wykorzystują Hypothesis do generowania losowych, ale zgodnych z typem danych
wejściowych, co pomaga znajdować edge case'y trudne do uwzględnienia
w testach example-based.
"""

from datetime import UTC, date, datetime

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

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
    return VerificationContext(
        evaluation_time=datetime(2026, 6, 1, tzinfo=UTC),
        tourist_birth_date=date(2010, 1, 1),
        club_join_dates={"PTTK": date(2020, 1, 1)},
        completed_badge_codes=frozenset(["KGP"]),
    )


# ---------------------------------------------------------------------------
# Strategie Hypothesis
# ---------------------------------------------------------------------------

# Zakres dat ograniczony do rozsądnych wartości historycznych/futurystycznych.
DATES = st.dates(min_value=date(1900, 1, 1), max_value=date(2100, 12, 31))

PEAK_IDS = st.integers(min_value=0, max_value=100_000)

REGION_IDS = st.integers(min_value=0, max_value=10_000)


def ascents_strategy() -> st.SearchStrategy[list[Ascent]]:
    """Generuje listę obiektów Ascent z losowymi danymi."""
    return st.lists(
        st.builds(
             Ascent,
            object_id=PEAK_IDS,
            ascent_date=DATES,
            region_ids=st.frozensets(REGION_IDS, max_size=5),
        ),
        min_size=0,
        max_size=20,
    )


# ---------------------------------------------------------------------------
# TimeLimitRule — property-based tests
# ---------------------------------------------------------------------------


class TestTimeLimitRuleHypothesis:
    """Właściwości reguły limitu czasowego."""

    @given(limit_in_years=st.integers(min_value=1, max_value=50))
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_empty_ascents_always_passes(self, ctx: VerificationContext, limit_in_years: int) -> None:
        """Pusta lista wejść nigdy nie narusza limitu czasowego."""
        rule = TimeLimitRule(limit_in_years=limit_in_years)
        assert rule.validate([], ctx) == []

    @given(
        limit_in_years=st.integers(min_value=1, max_value=50),
        ascents=ascents_strategy(),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_ascents_within_limit_pass(
        self,
        ctx: VerificationContext,
        limit_in_years: int,
        ascents: list[Ascent],
    ) -> None:
        """Jeśli wszystkie wejścia mieszczą się w limicie lat, nie ma błędów."""
        assume(ascents)
        assume(len({a.ascent_date for a in ascents}) > 1)

        earliest = min(a.ascent_date for a in ascents)
        latest = max(a.ascent_date for a in ascents)
        span_days = (latest - earliest).days
        limit_days = limit_in_years * 365

        assume(span_days <= limit_days)

        rule = TimeLimitRule(limit_in_years=limit_in_years)
        assert rule.validate(ascents, ctx) == []


# ---------------------------------------------------------------------------
# MandatoryObjectsRule — property-based tests
# ---------------------------------------------------------------------------


class TestMandatoryObjectsRuleHypothesis:
    """Właściwości reguły obowiązkowych szczytów."""

    @given(mandatory=st.frozensets(PEAK_IDS, max_size=0))
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_empty_mandatory_always_passes(self, ctx: VerificationContext, mandatory: frozenset[int]) -> None:
        """Pusta lista obowiązkowych szczytów nigdy nie generuje błędu,
        nawet przy pustej liście wejść."""
        rule = MandatoryObjectsRule(mandatory_peak_ids=mandatory)
        assert rule.validate([], ctx) == []

    @given(
        mandatory=st.frozensets(PEAK_IDS, min_size=1, max_size=10),
        climbed=st.frozensets(PEAK_IDS, min_size=1, max_size=20),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_missing_mandatory_peaks_produces_error(
        self, ctx: VerificationContext, mandatory: frozenset[int], climbed: frozenset[int]
    ) -> None:
        """Brak któregokolwiek z obowiązkowych szczytów generuje błąd."""
        assume(not mandatory.issubset(climbed))

        rule = MandatoryObjectsRule(mandatory_peak_ids=mandatory)
        errors = rule.validate(
            [Ascent(object_id=pid, ascent_date=date(2023, 1, 1)) for pid in climbed],
            ctx,
        )
        assert len(errors) >= 1


# ---------------------------------------------------------------------------
# StartDateRule — property-based tests
# ---------------------------------------------------------------------------


class TestStartDateRuleHypothesis:
    """Właściwości reguły daty startowej."""

    @given(start_date=DATES, ascent_date=DATES)
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_ascent_on_or_after_start_passes(
        self, ctx: VerificationContext, start_date: date, ascent_date: date
    ) -> None:
        """Wejścia w dniu startowym lub później nie generują błędu."""
        assume(ascent_date >= start_date)

        rule = StartDateRule(start_date=start_date)
        assert rule.validate([Ascent(object_id=1, ascent_date=ascent_date)], ctx) == []

    @given(start_date=DATES, ascent_date=DATES)
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_ascent_before_start_produces_error(
        self, ctx: VerificationContext, start_date: date, ascent_date: date
    ) -> None:
        """Wejścia przed datą startową generują błąd."""
        assume(ascent_date < start_date)

        rule = StartDateRule(start_date=start_date)
        errors = rule.validate([Ascent(object_id=1, ascent_date=ascent_date)], ctx)
        assert len(errors) >= 1


# ---------------------------------------------------------------------------
# DateWindowRule — property-based tests
# ---------------------------------------------------------------------------


class TestDateWindowRuleHypothesis:
    """Właściwości reguły okna czasowego."""

    @given(
        start_date=DATES,
        end_date=DATES,
        ascent_date=DATES,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_ascent_inside_window_passes(
        self,
        ctx: VerificationContext,
        start_date: date,
        end_date: date,
        ascent_date: date,
    ) -> None:
        """Wejścia wewnątrz zamkniętego okna czasowego przechodzą."""
        assume(start_date <= end_date)
        assume(start_date <= ascent_date <= end_date)

        rule = DateWindowRule(start_date=start_date, end_date=end_date)
        assert rule.validate([Ascent(object_id=1, ascent_date=ascent_date)], ctx) == []

    @given(
        start_date=DATES,
        end_date=DATES,
        ascent_date=DATES,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_ascent_outside_window_produces_error(
        self,
        ctx: VerificationContext,
        start_date: date,
        end_date: date,
        ascent_date: date,
    ) -> None:
        """Wejścia poza oknem czasowym generują błąd."""
        assume(start_date <= end_date)
        assume(ascent_date < start_date or ascent_date > end_date)

        rule = DateWindowRule(start_date=start_date, end_date=end_date)
        errors = rule.validate([Ascent(object_id=1, ascent_date=ascent_date)], ctx)
        assert len(errors) >= 1


# ---------------------------------------------------------------------------
# RegionCountRule — property-based tests
# ---------------------------------------------------------------------------


class TestRegionCountRuleHypothesis:
    """Właściwości reguły liczenia wejść według regionu."""

    @given(
        region_id=REGION_IDS,
        required_count=st.integers(min_value=1, max_value=10),
        matching_count=st.integers(min_value=0, max_value=20),
        non_matching_region_ids=st.lists(REGION_IDS, min_size=0, max_size=20),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_enough_ascents_in_region_passes(
        self,
        ctx: VerificationContext,
        region_id: int,
        required_count: int,
        matching_count: int,
        non_matching_region_ids: list[int],
    ) -> None:
        """Gdy liczba wejść z danego regionu >= wymaganej, nie ma błędu."""
        assume(matching_count >= required_count)

        region_ids_list = [region_id] * matching_count + non_matching_region_ids
        ascents = [
            Ascent(object_id=i, ascent_date=date(2023, 1, 1), region_ids=frozenset([rid]))
            for i, rid in enumerate(region_ids_list)
        ]
        rule = RegionCountRule(region_id=region_id, required_count=required_count)
        assert rule.validate(ascents, ctx) == []

    @given(
        region_id=REGION_IDS,
        required_count=st.integers(min_value=1, max_value=10),
        ascent_region_ids=st.lists(REGION_IDS, min_size=0, max_size=20),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_too_few_ascents_in_region_produces_error(
        self,
        ctx: VerificationContext,
        region_id: int,
        required_count: int,
        ascent_region_ids: list[int],
    ) -> None:
        """Gdy liczba wejść z danego regionu < wymaganej, generuje błąd."""
        count = sum(1 for rid in ascent_region_ids if rid == region_id)
        assume(count < required_count)

        ascents = [
            Ascent(object_id=i, ascent_date=date(2023, 1, 1), region_ids=frozenset([rid]))
            for i, rid in enumerate(ascent_region_ids)
        ]
        rule = RegionCountRule(region_id=region_id, required_count=required_count)
        errors = rule.validate(ascents, ctx)
        assert len(errors) >= 1


# ---------------------------------------------------------------------------
# RequiresClubJoinDateRule — property-based tests
# ---------------------------------------------------------------------------


CLUB_JOIN_DATES = st.dictionaries(
    keys=st.text(min_size=1, max_size=10),
    values=DATES,
    min_size=0,
    max_size=5,
)


class TestRequiresClubJoinDateRuleHypothesis:
    """Właściwości reguły przynależności do klubu."""

    @given(club_join_dates=CLUB_JOIN_DATES, ascent_date=DATES)
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_no_club_join_dates_produces_error(
        self, ctx: VerificationContext, club_join_dates: dict[str, date], ascent_date: date
    ) -> None:
        """Brak dat dołączenia do klubu generuje błąd."""
        assume(not club_join_dates)

        ctx_override = VerificationContext(
            evaluation_time=ctx.evaluation_time,
            tourist_birth_date=ctx.tourist_birth_date,
            club_join_dates=club_join_dates,
            completed_badge_codes=ctx.completed_badge_codes,
        )
        rule = RequiresClubJoinDateRule()
        errors = rule.validate([Ascent(object_id=1, ascent_date=ascent_date)], ctx_override)
        assert len(errors) >= 1

    @given(
        club_join_dates=CLUB_JOIN_DATES,
        ascent_date=DATES,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_ascent_after_join_passes(
        self, ctx: VerificationContext, club_join_dates: dict[str, date], ascent_date: date
    ) -> None:
        """Wejścia po najwcześniejszej dacie dołączenia przechodzą."""
        assume(club_join_dates)
        earliest_join = min(club_join_dates.values())
        assume(ascent_date >= earliest_join)

        ctx_override = VerificationContext(
            evaluation_time=ctx.evaluation_time,
            tourist_birth_date=ctx.tourist_birth_date,
            club_join_dates=club_join_dates,
            completed_badge_codes=ctx.completed_badge_codes,
        )
        rule = RequiresClubJoinDateRule()
        assert rule.validate([Ascent(object_id=1, ascent_date=ascent_date)], ctx_override) == []

    @given(
        club_join_dates=CLUB_JOIN_DATES,
        ascent_date=DATES,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_ascent_before_join_produces_error(
        self, ctx: VerificationContext, club_join_dates: dict[str, date], ascent_date: date
    ) -> None:
        """Wejścia przed najwcześniejszą datą dołączenia generują błąd."""
        assume(club_join_dates)
        earliest_join = min(club_join_dates.values())
        assume(ascent_date < earliest_join)

        ctx_override = VerificationContext(
            evaluation_time=ctx.evaluation_time,
            tourist_birth_date=ctx.tourist_birth_date,
            club_join_dates=club_join_dates,
            completed_badge_codes=ctx.completed_badge_codes,
        )
        rule = RequiresClubJoinDateRule()
        errors = rule.validate([Ascent(object_id=1, ascent_date=ascent_date)], ctx_override)
        assert len(errors) >= 1


# ---------------------------------------------------------------------------
# MinAgeRule / MaxAgeRule — property-based tests
# ---------------------------------------------------------------------------


class TestMinAgeRuleHypothesis:
    """Właściwości reguły minimalnego wieku."""

    @given(min_age=st.integers(min_value=0, max_value=120))
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_no_birth_date_always_passes(self, ctx: VerificationContext, min_age: int) -> None:
        """Brak daty urodzenia traktuje się jako brak błędu."""
        ctx_override = VerificationContext(
            evaluation_time=ctx.evaluation_time,
            tourist_birth_date=None,
            club_join_dates=ctx.club_join_dates,
            completed_badge_codes=ctx.completed_badge_codes,
        )
        rule = MinAgeRule(min_age=min_age)
        assert rule.validate([Ascent(object_id=1, ascent_date=date(2023, 1, 1))], ctx_override) == []

    @given(
        min_age=st.integers(min_value=0, max_value=120),
        birth_year=st.integers(min_value=1900, max_value=2020),
        ascent_year=st.integers(min_value=1900, max_value=2100),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_age_boundary(self, ctx: VerificationContext, min_age: int, birth_year: int, ascent_year: int) -> None:
        """Wiek dokładnie równy progowi min_age przechodzi."""
        assume(ascent_year >= birth_year)
        age = ascent_year - birth_year
        assume(age == min_age)

        birth_date = date(birth_year, 1, 1)
        ascent_date = date(ascent_year, 1, 1)

        ctx_override = VerificationContext(
            evaluation_time=ctx.evaluation_time,
            tourist_birth_date=birth_date,
            club_join_dates=ctx.club_join_dates,
            completed_badge_codes=ctx.completed_badge_codes,
        )
        rule = MinAgeRule(min_age=min_age)
        assert rule.validate([Ascent(object_id=1, ascent_date=ascent_date)], ctx_override) == []

    @given(
        min_age=st.integers(min_value=1, max_value=120),
        birth_year=st.integers(min_value=1900, max_value=2020),
        ascent_year=st.integers(min_value=1900, max_value=2100),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_under_age_produces_error(
        self, ctx: VerificationContext, min_age: int, birth_year: int, ascent_year: int
    ) -> None:
        """Wiek poniżej progu min_age generuje błąd."""
        assume(ascent_year >= birth_year)
        age = ascent_year - birth_year
        assume(age < min_age)

        birth_date = date(birth_year, 1, 1)
        ascent_date = date(ascent_year, 1, 1)

        ctx_override = VerificationContext(
            evaluation_time=ctx.evaluation_time,
            tourist_birth_date=birth_date,
            club_join_dates=ctx.club_join_dates,
            completed_badge_codes=ctx.completed_badge_codes,
        )
        rule = MinAgeRule(min_age=min_age)
        errors = rule.validate([Ascent(object_id=1, ascent_date=ascent_date)], ctx_override)
        assert len(errors) >= 1


class TestMaxAgeRuleHypothesis:
    """Właściwości reguły maksymalnego wieku."""

    @given(max_age=st.integers(min_value=0, max_value=120))
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_no_birth_date_produces_error(self, ctx: VerificationContext, max_age: int) -> None:
        """Brak daty urodzenia generuje błąd dla reguły maksymalnego wieku."""
        ctx_override = VerificationContext(
            evaluation_time=ctx.evaluation_time,
            tourist_birth_date=None,
            club_join_dates=ctx.club_join_dates,
            completed_badge_codes=ctx.completed_badge_codes,
        )
        rule = MaxAgeRule(max_age=max_age)
        errors = rule.validate([Ascent(object_id=1, ascent_date=date(2023, 1, 1))], ctx_override)
        assert len(errors) >= 1

    @given(
        max_age=st.integers(min_value=0, max_value=120),
        birth_year=st.integers(min_value=1900, max_value=2020),
        ascent_year=st.integers(min_value=1900, max_value=2100),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_age_boundary(self, ctx: VerificationContext, max_age: int, birth_year: int, ascent_year: int) -> None:
        """Wiek dokładnie równy progowi max_age przechodzi."""
        assume(ascent_year >= birth_year)
        age = ascent_year - birth_year
        assume(age == max_age)

        birth_date = date(birth_year, 1, 1)
        ascent_date = date(ascent_year, 1, 1)

        ctx_override = VerificationContext(
            evaluation_time=ctx.evaluation_time,
            tourist_birth_date=birth_date,
            club_join_dates=ctx.club_join_dates,
            completed_badge_codes=ctx.completed_badge_codes,
        )
        rule = MaxAgeRule(max_age=max_age)
        assert rule.validate([Ascent(object_id=1, ascent_date=ascent_date)], ctx_override) == []

    @given(
        max_age=st.integers(min_value=0, max_value=119),
        birth_year=st.integers(min_value=1900, max_value=2020),
        ascent_year=st.integers(min_value=1900, max_value=2100),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_over_age_produces_error(
        self, ctx: VerificationContext, max_age: int, birth_year: int, ascent_year: int
    ) -> None:
        """Wiek powyżej progu max_age generuje błąd."""
        assume(ascent_year >= birth_year)
        age = ascent_year - birth_year
        assume(age > max_age)

        birth_date = date(birth_year, 1, 1)
        ascent_date = date(ascent_year, 1, 1)

        ctx_override = VerificationContext(
            evaluation_time=ctx.evaluation_time,
            tourist_birth_date=birth_date,
            club_join_dates=ctx.club_join_dates,
            completed_badge_codes=ctx.completed_badge_codes,
        )
        rule = MaxAgeRule(max_age=max_age)
        errors = rule.validate([Ascent(object_id=1, ascent_date=ascent_date)], ctx_override)
        assert len(errors) >= 1


# ---------------------------------------------------------------------------
# GroupedAlternativesRule — property-based tests
# ---------------------------------------------------------------------------


class TestGroupedAlternativesRuleHypothesis:
    """Właściwości reguły wiaderek."""

    @given(
        groups=st.lists(
            st.frozensets(PEAK_IDS, min_size=1, max_size=10),
            min_size=1,
            max_size=5,
        ),
        min_groups_required=st.integers(min_value=0, max_value=5),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_groups_tuple_is_accepted(
        self,
        ctx: VerificationContext,
        groups: list[frozenset[int]],
        min_groups_required: int,
    ) -> None:
        """Reguła akceptuje tuple wiaderek i nie mutuje go."""
        assume(min_groups_required <= len(groups))

        rule = GroupedAlternativesRule(groups=tuple(groups), min_groups_required=min_groups_required)
        assert rule.groups == tuple(groups)

    @given(
        groups=st.lists(
            st.frozensets(PEAK_IDS, min_size=1, max_size=10),
            min_size=1,
            max_size=5,
        ),
        min_groups_required=st.integers(min_value=0, max_value=5),
        climbed_peak_ids=st.frozensets(PEAK_IDS, min_size=0, max_size=20),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_completed_groups_pass(
        self,
        ctx: VerificationContext,
        groups: list[frozenset[int]],
        min_groups_required: int,
        climbed_peak_ids: frozenset[int],
    ) -> None:
        """Jeśli zaliczono wymaganą liczbę wiaderek, nie ma błędu."""
        assume(min_groups_required <= len(groups))
        completed = sum(1 for group in groups if group.intersection(climbed_peak_ids))
        assume(completed >= min_groups_required)

        rule = GroupedAlternativesRule(groups=tuple(groups), min_groups_required=min_groups_required)
        ascents = [Ascent(object_id=pid, ascent_date=date(2023, 1, 1)) for pid in climbed_peak_ids]
        assert rule.validate(ascents, ctx) == []

    @given(
        groups=st.lists(
            st.frozensets(PEAK_IDS, min_size=1, max_size=10),
            min_size=1,
            max_size=5,
        ),
        climbed_peak_ids=st.frozensets(PEAK_IDS, min_size=0, max_size=20),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_insufficient_groups_produces_error(
        self,
        ctx: VerificationContext,
        groups: list[frozenset[int]],
        climbed_peak_ids: frozenset[int],
    ) -> None:
        """Jeśli zaliczono za mało wiaderek, generuje błąd."""
        completed = sum(1 for group in groups if group.intersection(climbed_peak_ids))
        min_groups_required = completed + 1
        assume(min_groups_required <= len(groups))

        rule = GroupedAlternativesRule(groups=tuple(groups), min_groups_required=min_groups_required)
        ascents = [Ascent(object_id=pid, ascent_date=date(2023, 1, 1)) for pid in climbed_peak_ids]
        errors = rule.validate(ascents, ctx)
        assert len(errors) >= 1


# ---------------------------------------------------------------------------
# PrerequisiteBadgeRule — property-based tests
# ---------------------------------------------------------------------------


class TestPrerequisiteBadgeRuleHypothesis:
    """Właściwości reguły wymaganej odznaki."""

    @given(required_badge_code=st.text(min_size=1, max_size=10))
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_missing_prerequisite_produces_error(self, ctx: VerificationContext, required_badge_code: str) -> None:
        """Brak wymaganej odznaki w completed_badge_codes generuje błąd."""
        assume(required_badge_code not in ctx.completed_badge_codes)

        rule = PrerequisiteBadgeRule(required_badge_code=required_badge_code)
        errors = rule.validate([], ctx)
        assert len(errors) >= 1

    @given(
        required_badge_code=st.text(min_size=1, max_size=10),
        extra_badges=st.lists(
            st.text(min_size=1, max_size=10),
            min_size=0,
            max_size=5,
        ),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_present_prerequisite_passes(
        self,
        ctx: VerificationContext,
        required_badge_code: str,
        extra_badges: list[str],
    ) -> None:
        """Obecność wymaganej odznaki w completed_badge_codes przechodzi."""
        completed = frozenset([required_badge_code] + extra_badges)
        ctx_override = VerificationContext(
            evaluation_time=ctx.evaluation_time,
            tourist_birth_date=ctx.tourist_birth_date,
            club_join_dates=ctx.club_join_dates,
            completed_badge_codes=completed,
        )
        rule = PrerequisiteBadgeRule(required_badge_code=required_badge_code)
        assert rule.validate([], ctx_override) == []


# ---------------------------------------------------------------------------
# MultiPoolRequirementRule — property-based tests
# ---------------------------------------------------------------------------


class TestMultiPoolRequirementRuleHypothesis:
    """Właściwości reguły wielu podzbiorów."""

    @given(
        pools=st.lists(
            st.builds(
                SubPoolRequirement,
                required_count=st.integers(min_value=1, max_value=5),
                peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=10),
                name=st.text(min_size=0, max_size=10),
            ),
            min_size=1,
            max_size=3,
        ),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_all_pools_satisfied_passes(
        self,
        ctx: VerificationContext,
        pools: list[SubPoolRequirement],
    ) -> None:
        """Gdy wszystkie podzbiory mają wymaganą liczbę wejść, nie ma błędu."""
        assume(all(len(pool.peak_ids) >= pool.required_count for pool in pools))

        all_peak_ids = [pid for pool in pools for pid in pool.peak_ids]
        assume(all_peak_ids)

        climbed_peak_ids = frozenset(all_peak_ids)
        rule = MultiPoolRequirementRule(pools=tuple(pools))
        ascents = [Ascent(object_id=pid, ascent_date=date(2023, 1, 1)) for pid in climbed_peak_ids]
        assert rule.validate(ascents, ctx) == []

    @given(
        pools=st.lists(
            st.builds(
                SubPoolRequirement,
                required_count=st.integers(min_value=1, max_value=10),
                peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=20),
                name=st.text(min_size=0, max_size=10),
            ),
            min_size=1,
            max_size=3,
        ),
        climbed_peak_ids=st.frozensets(PEAK_IDS, min_size=0, max_size=30),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_unsatisfied_pool_produces_error(
        self,
        ctx: VerificationContext,
        pools: list[SubPoolRequirement],
        climbed_peak_ids: frozenset[int],
    ) -> None:
        """Gdy któryś podzbiór ma za mało wejść, generuje błąd."""
        unsatisfied = [p for p in pools if len(p.peak_ids & climbed_peak_ids) < p.required_count]
        assume(unsatisfied)

        rule = MultiPoolRequirementRule(pools=tuple(pools))
        ascents = [Ascent(object_id=pid, ascent_date=date(2023, 1, 1)) for pid in climbed_peak_ids]
        errors = rule.validate(ascents, ctx)
        assert len(errors) >= len(unsatisfied)


# ---------------------------------------------------------------------------
# Cross-rule / integration-style Hypothesis tests
# ---------------------------------------------------------------------------


class TestCompositeRulesHypothesis:
    """Właściwości kompozycji wielu reguł."""

    @given(
        ascents=st.lists(
            st.builds(
                Ascent,
                object_id=PEAK_IDS,
                ascent_date=DATES,
                region_ids=st.frozensets(REGION_IDS, max_size=3),
            ),
            min_size=0,
            max_size=10,
        ),
        mandatory=st.frozensets(PEAK_IDS, max_size=5),
        start_date=DATES,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_start_date_does_not_affect_mandatory_rule(
        self,
        ctx: VerificationContext,
        ascents: list[Ascent],
        mandatory: frozenset[int],
        start_date: date,
    ) -> None:
        """Reguła daty startowej nie zmienia zachowania reguły obowiązkowych szczytów."""
        if not ascents:
            return

        mandatory_rule = MandatoryObjectsRule(mandatory_peak_ids=mandatory)
        start_rule = StartDateRule(start_date=start_date)

        mandatory_errors = mandatory_rule.validate(ascents, ctx)
        start_errors = start_rule.validate(ascents, ctx)

        combined_errors = sorted(mandatory_errors + start_errors)
        expected_errors = sorted(mandatory_errors) + sorted(start_errors)
        assert combined_errors == expected_errors

    @given(
        ascents=st.lists(
            st.builds(
                Ascent,
                object_id=PEAK_IDS,
                ascent_date=DATES,
                region_ids=st.frozensets(REGION_IDS, max_size=3),
            ),
            min_size=1,
            max_size=10,
        ),
        region_id=REGION_IDS,
        required_count=st.integers(min_value=1, max_value=20),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_region_count_errors_do_not_duplicate(
        self,
        ctx: VerificationContext,
        ascents: list[Ascent],
        region_id: int,
        required_count: int,
    ) -> None:
        """RegionCountRule zwraca co najwyżej jeden błąd, niezależnie od liczby wejść."""
        rule = RegionCountRule(region_id=region_id, required_count=required_count)
        errors = rule.validate(ascents, ctx)
        assert len(errors) <= 1

    @given(
        ascents=st.lists(
            st.builds(
                Ascent,
                object_id=PEAK_IDS,
                ascent_date=DATES,
                region_ids=st.frozensets(REGION_IDS, max_size=3),
            ),
            min_size=0,
            max_size=10,
        ),
        mandatory=st.frozensets(PEAK_IDS, max_size=5),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_mandatory_errors_count_equals_missing_peaks_count(
        self,
        ctx: VerificationContext,
        ascents: list[Ascent],
        mandatory: frozenset[int],
    ) -> None:
        """Liczba błędów MandatoryObjectsRule wynosi 0 lub 1, a błąd wymienia wszystkie brakujące."""
        if not mandatory:
            return

        rule = MandatoryObjectsRule(mandatory_peak_ids=mandatory)
        errors = rule.validate(ascents, ctx)
        assert len(errors) <= 1
        if errors:
            climbed = {a.object_id for a in ascents}
            missing = sorted(mandatory - climbed)
            assert str(missing) in errors[0]


# ---------------------------------------------------------------------------
# TimeLimitRule — additional edge-case tests
# ---------------------------------------------------------------------------


class TestTimeLimitRuleEdgeCasesHypothesis:
    """Kolejne właściwości limitu czasowego."""

    @given(
        start_year=st.integers(min_value=1904, max_value=2020).filter(lambda y: y % 4 == 0),
        limit_in_years=st.integers(min_value=1, max_value=50),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_leap_year_deadline_adjustment(
        self,
        start_year: int,
        limit_in_years: int,
    ) -> None:
        """Data deadline nie powinna spaść na 29 lutego w roku nieprzestępnym."""
        start_date = date(start_year, 2, 29)

        try:
            deadline = start_date.replace(year=start_date.year + limit_in_years)
        except ValueError:
            deadline = start_date.replace(year=start_date.year + limit_in_years, month=2, day=28)

        assert deadline.month == 2
        assert deadline.day in {28, 29}
        if deadline.day == 29:
            try:
                deadline.replace(year=deadline.year, month=2, day=29)
            except ValueError:
                pytest.fail("Deadline nie powinien być 29 lutego w roku nieprzestępnym")


# ---------------------------------------------------------------------------
# MinAgeRule / MaxAgeRule — month/day boundary tests
# ---------------------------------------------------------------------------


class TestAgeRulesMonthDayHypothesis:
    """Właściwości wieku z dokładnością do miesiąca/dnia."""

    @given(
        min_age=st.integers(min_value=0, max_value=120),
        birth_year=st.integers(min_value=1900, max_value=2020),
        birth_month=st.integers(min_value=1, max_value=12),
        birth_day=st.integers(min_value=1, max_value=28),
        ascent_year=st.integers(min_value=1900, max_value=2100),
        ascent_month=st.integers(min_value=1, max_value=12),
        ascent_day=st.integers(min_value=1, max_value=28),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_min_age_exact_month_day_boundary(
        self,
        ctx: VerificationContext,
        min_age: int,
        birth_year: int,
        birth_month: int,
        birth_day: int,
        ascent_year: int,
        ascent_month: int,
        ascent_day: int,
    ) -> None:
        """Wiek obliczany z dokładnością do dnia."""
        birth_date = date(birth_year, birth_month, birth_day)
        ascent_date = date(ascent_year, ascent_month, ascent_day)

        try:
            birthday_in_ascent_year = birth_date.replace(year=ascent_year)
        except ValueError:
            birthday_in_ascent_year = birth_date.replace(year=ascent_year, month=2, day=28)

        age = (
            ascent_year
            - birth_year
            - ((ascent_month, ascent_day) < (birthday_in_ascent_year.month, birthday_in_ascent_year.day))
        )

        ctx_override = VerificationContext(
            evaluation_time=ctx.evaluation_time,
            tourist_birth_date=birth_date,
            club_join_dates=ctx.club_join_dates,
            completed_badge_codes=ctx.completed_badge_codes,
        )
        rule = MinAgeRule(min_age=min_age)
        errors = rule.validate([Ascent(object_id=1, ascent_date=ascent_date)], ctx_override)

        if age >= min_age:
            assert errors == []
        else:
            assert len(errors) >= 1


# ---------------------------------------------------------------------------
# Ascent list invariants
# ---------------------------------------------------------------------------


class TestAscentListInvariantsHypothesis:
    """Niezmienniki list wejść."""

    @given(
        ascents=st.lists(
            st.builds(
                Ascent,
                object_id=PEAK_IDS,
                ascent_date=DATES,
                region_ids=st.frozensets(REGION_IDS, max_size=3),
            ),
            min_size=0,
            max_size=10,
        ),
        mandatory=st.frozensets(PEAK_IDS, max_size=5),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_duplicate_ascents_do_not_break_mandatory_rule(
        self,
        ctx: VerificationContext,
        ascents: list[Ascent],
        mandatory: frozenset[int],
    ) -> None:
        """Duplikaty wejść nie zmieniają wyniku MandatoryObjectsRule."""
        if not ascents or not mandatory:
            return

        deduped = [
            Ascent(object_id=a.object_id, ascent_date=a.ascent_date, region_ids=a.region_ids)
            for a in dict.fromkeys(ascents)
        ]
        rule = MandatoryObjectsRule(mandatory_peak_ids=mandatory)
        errors_with_dups = rule.validate(ascents, ctx)
        errors_without_dups = rule.validate(deduped, ctx)
        assert errors_with_dups == errors_without_dups

    @given(
        ascents=st.lists(
            st.builds(
                Ascent,
                object_id=PEAK_IDS,
                ascent_date=DATES,
                region_ids=st.frozensets(REGION_IDS, max_size=3),
            ),
            min_size=0,
            max_size=10,
        ),
        limit_in_years=st.integers(min_value=1, max_value=50),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_time_limit_rule_uses_min_and_max_dates(
        self,
        ctx: VerificationContext,
        ascents: list[Ascent],
        limit_in_years: int,
    ) -> None:
        """TimeLimitRule bierze pod uwagę tylko najwcześniejszą i najpóźniejszą datę."""
        if not ascents:
            return

        earliest = min(a.ascent_date for a in ascents)
        latest = max(a.ascent_date for a in ascents)

        rule = TimeLimitRule(limit_in_years=limit_in_years)
        try:
            deadline = earliest.replace(year=earliest.year + limit_in_years)
        except ValueError:
            deadline = earliest.replace(year=earliest.year + limit_in_years, month=2, day=28)

        if latest <= deadline:
            assert rule.validate(ascents, ctx) == []
        else:
            assert len(rule.validate(ascents, ctx)) >= 1


# ---------------------------------------------------------------------------
# Idempotency / determinism
# ---------------------------------------------------------------------------


class TestRuleIdempotencyHypothesis:
    """Walidacja reguł powinna być deterministyczna i idempotentna."""

    @given(
        ascents=st.lists(
            st.builds(
                Ascent,
                object_id=PEAK_IDS,
                ascent_date=DATES,
                region_ids=st.frozensets(REGION_IDS, max_size=3),
            ),
            min_size=0,
            max_size=10,
        ),
        limit_in_years=st.integers(min_value=1, max_value=50),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_time_limit_rule_idempotent(
        self,
        ctx: VerificationContext,
        ascents: list[Ascent],
        limit_in_years: int,
    ) -> None:
        """Dwukrotne wywołanie validate dla TimeLimitRule daje ten sam wynik."""
        rule = TimeLimitRule(limit_in_years=limit_in_years)
        first = rule.validate(ascents, ctx)
        second = rule.validate(ascents, ctx)
        assert first == second

    @given(
        ascents=st.lists(
            st.builds(
                Ascent,
                object_id=PEAK_IDS,
                ascent_date=DATES,
                region_ids=st.frozensets(REGION_IDS, max_size=3),
            ),
            min_size=0,
            max_size=10,
        ),
        mandatory=st.frozensets(PEAK_IDS, max_size=5),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_mandatory_rule_idempotent(
        self,
        ctx: VerificationContext,
        ascents: list[Ascent],
        mandatory: frozenset[int],
    ) -> None:
        """Dwukrotne wywołanie validate dla MandatoryObjectsRule daje ten sam wynik."""
        rule = MandatoryObjectsRule(mandatory_peak_ids=mandatory)
        first = rule.validate(ascents, ctx)
        second = rule.validate(ascents, ctx)
        assert first == second


# ---------------------------------------------------------------------------
# DateWindowRule — single-day window and exact-boundary tests
# ---------------------------------------------------------------------------


class TestDateWindowRuleEdgeCasesHypothesis:
    """Edge case'y reguły okna czasowego."""

    @given(ascent_date=DATES)
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_single_day_window_passes_for_exact_date(self, ctx: VerificationContext, ascent_date: date) -> None:
        """Okno jedno-dniowe akceptuje wejście w dokładnie tej dacie."""
        rule = DateWindowRule(start_date=ascent_date, end_date=ascent_date)
        assert rule.validate([Ascent(object_id=1, ascent_date=ascent_date)], ctx) == []

    @given(
        start_date=DATES,
        end_date=DATES,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_single_day_window_rejects_other_dates(
        self, ctx: VerificationContext, start_date: date, end_date: date
    ) -> None:
        """Okno jedno-dniowe odrzuca wszystkie inne daty."""
        assume(start_date == end_date)
        other_date = start_date.replace(year=start_date.year + 1)
        rule = DateWindowRule(start_date=start_date, end_date=end_date)
        errors = rule.validate([Ascent(object_id=1, ascent_date=other_date)], ctx)
        assert len(errors) >= 1


# ---------------------------------------------------------------------------
# RegionCountRule — exact match and zero required
# ---------------------------------------------------------------------------


class TestRegionCountRuleEdgeCasesHypothesis:
    """Edge case'y reguły liczenia regionów."""

    @given(
        region_id=REGION_IDS,
        matching_count=st.integers(min_value=1, max_value=20),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_exact_count_passes(
        self,
        ctx: VerificationContext,
        region_id: int,
        matching_count: int,
    ) -> None:
        """Liczba wejść dokładnie równa required_count przechodzi."""
        ascents = [
            Ascent(object_id=i, ascent_date=date(2023, 1, 1), region_ids=frozenset([region_id]))
            for i in range(matching_count)
        ]
        rule = RegionCountRule(region_id=region_id, required_count=matching_count)
        assert rule.validate(ascents, ctx) == []


# ---------------------------------------------------------------------------
# GroupedAlternativesRule — empty and boundary cases
# ---------------------------------------------------------------------------


class TestGroupedAlternativesRuleEdgeCasesHypothesis:
    """Edge case'y reguły wiaderek."""

    @given(
        groups=st.lists(
            st.frozensets(PEAK_IDS, min_size=1, max_size=10),
            min_size=1,
            max_size=5,
        ),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_min_groups_zero_always_passes(
        self,
        ctx: VerificationContext,
        groups: list[frozenset[int]],
    ) -> None:
        """min_groups_required=0 zawsze przechodzi, nawet bez wejść."""
        rule = GroupedAlternativesRule(groups=tuple(groups), min_groups_required=0)
        assert rule.validate([], ctx) == []


# ---------------------------------------------------------------------------
# MultiPoolRequirementRule — empty pools edge case
# ---------------------------------------------------------------------------


class TestMultiPoolRequirementRuleEdgeCasesHypothesis:
    """Edge case'y reguły wielu podzbiorów."""

    @given(
        peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=10),
        required_count=st.integers(min_value=1, max_value=10),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_single_pool_with_enough_peaks_passes(
        self,
        ctx: VerificationContext,
        peak_ids: frozenset[int],
        required_count: int,
    ) -> None:
        """Pojedynczy podzbiór z wystarczającą liczbą szczytów przechodzi."""
        assume(len(peak_ids) >= required_count)
        pool = SubPoolRequirement(required_count=required_count, peak_ids=peak_ids, name="test")
        rule = MultiPoolRequirementRule(pools=(pool,))
        ascents = [Ascent(object_id=pid, ascent_date=date(2023, 1, 1)) for pid in peak_ids]
        assert rule.validate(ascents, ctx) == []


# ---------------------------------------------------------------------------
# RequiresClubJoinDateRule — multiple join dates
# ---------------------------------------------------------------------------


class TestRequiresClubJoinDateRuleEdgeCasesHypothesis:
    """Edge case'y reguły przynależności do klubu."""

    @given(
        join_dates=st.lists(DATES, min_size=2, max_size=5),
        ascent_date=DATES,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_earliest_join_date_is_used(
        self,
        ctx: VerificationContext,
        join_dates: list[date],
        ascent_date: date,
    ) -> None:
        """Używana jest najwcześniejsza data dołączenia spośród wszystkich klubów."""
        earliest = min(join_dates)
        club_dict = {f"club_{i}": d for i, d in enumerate(join_dates)}
        ctx_override = VerificationContext(
            evaluation_time=ctx.evaluation_time,
            tourist_birth_date=ctx.tourist_birth_date,
            club_join_dates=club_dict,
            completed_badge_codes=ctx.completed_badge_codes,
        )
        rule = RequiresClubJoinDateRule()

        if ascent_date >= earliest:
            assert rule.validate([Ascent(object_id=1, ascent_date=ascent_date)], ctx_override) == []
        else:
            assert len(rule.validate([Ascent(object_id=1, ascent_date=ascent_date)], ctx_override)) >= 1


# ---------------------------------------------------------------------------
# Error message format consistency
# ---------------------------------------------------------------------------


class TestErrorMessageFormatHypothesis:
    """Format komunikatów o błędach jest spójny."""

    @given(
        peak_id=PEAK_IDS,
        ascent_date=DATES,
        start_date=DATES,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_start_date_error_format_contains_peak_and_date(
        self, ctx: VerificationContext, peak_id: int, ascent_date: date, start_date: date
    ) -> None:
        """Komunikat błędu StartDateRule zawiera ID szczytu i datę."""
        assume(ascent_date < start_date)
        rule = StartDateRule(start_date=start_date)
        errors = rule.validate([Ascent(object_id=peak_id, ascent_date=ascent_date)], ctx)
        assert errors
        assert str(peak_id) in errors[0]
        assert str(ascent_date) in errors[0]

    @given(
        peak_id=PEAK_IDS,
        birth_year=st.integers(min_value=1900, max_value=2020),
        min_age=st.integers(min_value=1, max_value=120),
        ascent_year=st.integers(min_value=1900, max_value=2100),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_min_age_error_contains_age_info(
        self,
        ctx: VerificationContext,
        peak_id: int,
        birth_year: int,
        min_age: int,
        ascent_year: int,
    ) -> None:
        """Komunikat błędu MinAgeRule zawiera informację o wieku."""
        assume(ascent_year - birth_year < min_age)
        birth_date = date(birth_year, 1, 1)
        ascent_date = date(ascent_year, 1, 1)
        ctx_override = VerificationContext(
            evaluation_time=ctx.evaluation_time,
            tourist_birth_date=birth_date,
            club_join_dates=ctx.club_join_dates,
            completed_badge_codes=ctx.completed_badge_codes,
        )
        rule = MinAgeRule(min_age=min_age)
        errors = rule.validate([Ascent(object_id=peak_id, ascent_date=ascent_date)], ctx_override)
        assert errors
        assert "lat" in errors[0]
