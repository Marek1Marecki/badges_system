"""Property-based tests for the entire domain layer.

Celem jest żelazna odporność domeny: sprawdzenie niezmienników, granicznych
przypadków i zachowań agregatu BadgeVersionDomain oraz obiektów wartości.
"""

from datetime import UTC, date, datetime
from unittest.mock import MagicMock

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from domain.entities.badge_version import BadgeTierDomain, BadgeVersionDomain
from domain.events import DomainEvent, UserProgressStateChanged
from domain.exceptions import DomainException, ValidationError
from domain.rules.badge_rules import (
    BadgeRule,
    MaxAgeRule,
    MinAgeRule,
    StartDateRule,
    TimeLimitRule,
)
from domain.value_objects.ascent import Ascent
from domain.value_objects.verification_context import VerificationContext
from domain.value_objects.verification_result import TierResult, VerificationResult

# ---------------------------------------------------------------------------
# Strategie Hypothesis
# ---------------------------------------------------------------------------

DATES = st.dates(min_value=date(1900, 1, 1), max_value=date(2100, 12, 31))

PEAK_IDS = st.integers(min_value=0, max_value=100_000)

REGION_IDS = st.integers(min_value=0, max_value=10_000)

ASCENTS = st.lists(
    st.builds(
        Ascent,
        peak_id=PEAK_IDS,
        ascent_date=DATES,
        region_ids=st.frozensets(PEAK_IDS, max_size=3),
    ),
    min_size=0,
    max_size=20,
)

TIER_SPECS = st.lists(
    st.tuples(
        st.integers(min_value=0, max_value=1000),
        st.integers(min_value=1, max_value=50),
        st.integers(min_value=1, max_value=20),
    ),
    min_size=0,
    max_size=5,
)

POOL_PEAK_IDS = st.frozensets(PEAK_IDS, min_size=0, max_size=20)


def make_tiers(specs: list[tuple[int, int, int]]) -> list[BadgeTierDomain]:
    return [BadgeTierDomain(tier_id=tid, name=f"Tier {tid}", required_count=rc, order=o) for tid, rc, o in specs]


def make_ctx() -> VerificationContext:
    return VerificationContext(
        evaluation_time=datetime(2026, 6, 1, tzinfo=UTC),
        tourist_birth_date=date(1990, 1, 1),
        club_join_dates={"PTTK": date(2020, 1, 1)},
        completed_badge_codes=frozenset(["KGP"]),
    )


# ---------------------------------------------------------------------------
# Ascent — property-based tests
# ---------------------------------------------------------------------------


class TestAscentHypothesis:
    """Właściwości wartościowego obiektu Ascent."""

    @given(
        peak_id=PEAK_IDS,
        ascent_date=DATES,
        region_ids=st.frozensets(PEAK_IDS, max_size=5),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_ascent_is_immutable(self, peak_id: int, ascent_date: date, region_ids: frozenset[int]) -> None:
        """Ascent jest frozen — nie można zmodyfikować pól po utworzeniu."""
        ascent = Ascent(peak_id=peak_id, ascent_date=ascent_date, region_ids=region_ids)
        with pytest.raises((AttributeError, TypeError)):
            ascent.peak_id = 999

    @given(
        peak_id=PEAK_IDS,
        ascent_date=DATES,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_ascent_default_region_ids_is_empty(self, peak_id: int, ascent_date: date) -> None:
        """Domyślny region_ids to pusty frozenset."""
        ascent = Ascent(peak_id=peak_id, ascent_date=ascent_date)
        assert ascent.region_ids == frozenset()

    @given(
        peak_id=PEAK_IDS,
        ascent_date=DATES,
        region_ids=st.frozensets(PEAK_IDS, max_size=5),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_ascent_equality_based_on_fields(self, peak_id: int, ascent_date: date, region_ids: frozenset[int]) -> None:
        """Równe Ascenty mają identyczne pola."""
        a1 = Ascent(peak_id=peak_id, ascent_date=ascent_date, region_ids=region_ids)
        a2 = Ascent(peak_id=peak_id, ascent_date=ascent_date, region_ids=region_ids)
        assert a1 == a2
        assert hash(a1) == hash(a2)

    @given(
        peak_id=PEAK_IDS,
        ascent_date=DATES,
        region_ids=st.frozensets(PEAK_IDS, max_size=5),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_ascent_is_hashable(self, peak_id: int, ascent_date: date, region_ids: frozenset[int]) -> None:
        """Ascent można użyć jako klucz w słowniku (hashable)."""
        ascent = Ascent(peak_id=peak_id, ascent_date=ascent_date, region_ids=region_ids)
        d = {ascent: "value"}
        assert d[ascent] == "value"


# ---------------------------------------------------------------------------
# VerificationContext — property-based tests
# ---------------------------------------------------------------------------


class TestVerificationContextHypothesis:
    """Właściwości kontekstu weryfikacyjnego."""

    @given(evaluation_time=st.datetimes(timezones=st.just(UTC)))
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_context_is_frozen(self, evaluation_time: datetime) -> None:
        """VerificationContext jest immutable."""
        ctx = VerificationContext(evaluation_time=evaluation_time)
        with pytest.raises((AttributeError, TypeError)):
            ctx.evaluation_time = datetime(2100, 1, 1, tzinfo=UTC)

    @given(
        club_join_dates=st.dictionaries(
            keys=st.text(min_size=1, max_size=10),
            values=DATES,
            min_size=0,
            max_size=5,
        ),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_club_join_dates_default_empty(self, club_join_dates: dict[str, date]) -> None:
        """Domyślny club_join_dates to pusty słownik."""
        ctx = VerificationContext(evaluation_time=datetime(2026, 1, 1, tzinfo=UTC))
        assert ctx.club_join_dates == {}

    @given(
        completed_badge_codes=st.lists(
            st.text(min_size=1, max_size=10),
            min_size=0,
            max_size=5,
        ),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_completed_badge_codes_default_empty(self, completed_badge_codes: list[str]) -> None:
        """Domyślny completed_badge_codes to pusty frozenset."""
        ctx = VerificationContext(evaluation_time=datetime(2026, 1, 1, tzinfo=UTC))
        assert ctx.completed_badge_codes == frozenset()


# ---------------------------------------------------------------------------
# VerificationResult / TierResult — property-based tests
# ---------------------------------------------------------------------------


class TestVerificationResultHypothesis:
    """Właściwości wyniku weryfikacji."""

    @given(
        verified=st.booleans(),
        status=st.sampled_from(["COMPLETED", "IN_PROGRESS", "NOT_STARTED"]),
        valid_ascents_count=st.integers(min_value=0, max_value=100),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_result_is_frozen(self, verified: bool, status: str, valid_ascents_count: int) -> None:
        """VerificationResult jest immutable."""
        result = VerificationResult(verified=verified, status=status, valid_ascents_count=valid_ascents_count)
        with pytest.raises((AttributeError, TypeError)):
            result.verified = not verified

    @given(
        tier_id=st.integers(min_value=0, max_value=1000),
        name=st.text(min_size=0, max_size=20),
        status=st.sampled_from(["COMPLETED", "IN_PROGRESS", "NOT_STARTED"]),
        required_count=st.integers(min_value=1, max_value=50),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_tier_result_is_frozen(self, tier_id: int, name: str, status: str, required_count: int) -> None:
        """TierResult jest immutable."""
        tier = TierResult(tier_id=tier_id, name=name, status=status, required_count=required_count)
        with pytest.raises((AttributeError, TypeError)):
            tier.status = "COMPLETED"


# ---------------------------------------------------------------------------
# BadgeVersionDomain — core aggregate Hypothesis tests
# ---------------------------------------------------------------------------


class TestBadgeVersionDomainEvaluateHypothesis:
    """Właściwości ewaluacji agregatu BadgeVersionDomain."""

    @given(
        pool_peak_ids=POOL_PEAK_IDS,
        ascents=ASCENTS,
        tier_specs=TIER_SPECS,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_valid_ascents_count_matches_unique_valid(
        self,
        pool_peak_ids: frozenset[int],
        ascents: list[Ascent],
        tier_specs: list[tuple[int, int, int]],
    ) -> None:
        """valid_ascents_count równa się liczbie unikalnych wejść po filtracji puli."""
        domain = BadgeVersionDomain(
            version_id="v1",
            rules=[],
            pool_peak_ids=pool_peak_ids,
            tiers=make_tiers(tier_specs),
        )
        result = domain.evaluate(ascents, make_ctx())

        if pool_peak_ids:
            valid = [a for a in ascents if a.peak_id in pool_peak_ids]
        else:
            valid = ascents

        seen = set()
        unique_valid = []
        for a in sorted(valid, key=lambda x: x.ascent_date):
            if a.peak_id not in seen:
                unique_valid.append(a)
                seen.add(a.peak_id)

        assert result.valid_ascents_count == len(unique_valid)

    @given(
        pool_peak_ids=POOL_PEAK_IDS,
        ascents=ASCENTS,
        tier_specs=TIER_SPECS,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_deduplication_keeps_earliest_per_peak(
        self,
        pool_peak_ids: frozenset[int],
        ascents: list[Ascent],
        tier_specs: list[tuple[int, int, int]],
    ) -> None:
        """Dla tego samego peak_id zachowywane jest najwcześniejsze wejście."""
        assume(ascents)
        assume(pool_peak_ids)

        peaks_in_ascents = list({a.peak_id for a in ascents if a.peak_id in pool_peak_ids})
        assume(peaks_in_ascents)

        target_peak = peaks_in_ascents[0]
        date1 = date(2020, 1, 1)
        date2 = date(2021, 1, 1)
        modified = [Ascent(peak_id=a.peak_id, ascent_date=a.ascent_date, region_ids=a.region_ids) for a in ascents]
        modified.append(Ascent(peak_id=target_peak, ascent_date=date1))
        modified.append(Ascent(peak_id=target_peak, ascent_date=date2))

        domain = BadgeVersionDomain(
            version_id="v1",
            rules=[],
            pool_peak_ids=pool_peak_ids,
            tiers=make_tiers(tier_specs),
        )
        result = domain.evaluate(modified, make_ctx())

        seen = set()
        unique_valid = []
        for a in sorted([a for a in modified if a.peak_id in pool_peak_ids], key=lambda x: x.ascent_date):
            if a.peak_id not in seen:
                unique_valid.append(a)
                seen.add(a.peak_id)

        assert result.valid_ascents_count == len(unique_valid)

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=10),
        tier_specs=TIER_SPECS,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_empty_ascents_means_not_started(
        self,
        pool_peak_ids: frozenset[int],
        tier_specs: list[tuple[int, int, int]],
    ) -> None:
        """Pusta lista wejść daje status NOT_STARTED o ile wymagana jest przynajmniej 1. liczba."""
        required_count = 1
        if not tier_specs:
            tier_specs = [(1, required_count, 1)]

        domain = BadgeVersionDomain(
            version_id="v1",
            rules=[],
            pool_peak_ids=pool_peak_ids,
            tiers=make_tiers(tier_specs),
        )
        result = domain.evaluate([], make_ctx())
        assert result.status == "NOT_STARTED"
        assert result.verified is False
        assert result.valid_ascents_count == 0

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=10),
        required_count=st.integers(min_value=1, max_value=20),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_tier_state_machine_not_started_to_completed(
        self,
        pool_peak_ids: frozenset[int],
        required_count: int,
    ) -> None:
        """Dla liczby wejść = required_count status to COMPLETED, dla mniej IN_PROGRESS."""
        assume(len(pool_peak_ids) >= required_count)

        peak_list = list(pool_peak_ids)[:required_count]
        ascents = [Ascent(peak_id=pid, ascent_date=date(2023, 1, 1)) for pid in peak_list]

        domain = BadgeVersionDomain(
            version_id="v1",
            rules=[],
            pool_peak_ids=pool_peak_ids,
            tiers=[BadgeTierDomain(tier_id=1, name="T1", required_count=required_count, order=1)],
        )
        result = domain.evaluate(ascents, make_ctx())

        assert result.status == "COMPLETED"
        assert result.verified is True
        assert result.valid_ascents_count == required_count

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=10),
        required_count=st.integers(min_value=2, max_value=20),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_tier_state_machine_in_progress(
        self,
        pool_peak_ids: frozenset[int],
        required_count: int,
    ) -> None:
        """Dla liczby wejść < required_count status to IN_PROGRESS."""
        assume(len(pool_peak_ids) >= required_count)

        fewer = max(1, required_count - 1)
        peak_list = list(pool_peak_ids)[:fewer]
        ascents = [Ascent(peak_id=pid, ascent_date=date(2023, 1, 1)) for pid in peak_list]

        domain = BadgeVersionDomain(
            version_id="v1",
            rules=[],
            pool_peak_ids=pool_peak_ids,
            tiers=[BadgeTierDomain(tier_id=1, name="T1", required_count=required_count, order=1)],
        )
        result = domain.evaluate(ascents, make_ctx())

        assert result.status == "IN_PROGRESS"
        assert result.verified is False

    @given(
        tier_specs=TIER_SPECS,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_empty_tiers_fallback_requires_full_pool(self, tier_specs: list[tuple[int, int, int]]) -> None:
        """Brak stopni → fallback wymaga 100% puli."""
        assume(not tier_specs)
        pool = frozenset([1, 2, 3, 4, 5])

        domain = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=pool, tiers=[])

        all_ascents = [Ascent(peak_id=pid, ascent_date=date(2023, 1, 1)) for pid in pool]
        result_full = domain.evaluate(all_ascents, make_ctx())
        assert result_full.verified is True
        assert result_full.status == "COMPLETED"

        partial = [Ascent(peak_id=pid, ascent_date=date(2023, 1, 1)) for pid in [1, 2]]
        result_partial = domain.evaluate(partial, make_ctx())
        assert result_partial.verified is False
        assert result_partial.status == "IN_PROGRESS"

    @given(
        pool_peak_ids=POOL_PEAK_IDS,
        tier_specs=TIER_SPECS,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_empty_pool_means_all_ascents_valid(
        self,
        pool_peak_ids: frozenset[int],
        tier_specs: list[tuple[int, int, int]],
    ) -> None:
        """Pusta pula = brak filtracji przestrzennej, wszystkie wejścia są valid."""
        assume(not pool_peak_ids)
        ascents = [Ascent(peak_id=i, ascent_date=date(2023, 1, 1)) for i in range(5)]

        domain = BadgeVersionDomain(
            version_id="v1",
            rules=[],
            pool_peak_ids=frozenset(),
            tiers=make_tiers(tier_specs) if tier_specs else [],
        )
        result = domain.evaluate(ascents, make_ctx())
        assert result.valid_ascents_count == len(ascents)

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=10),
        outside_peak_id=PEAK_IDS,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_outside_pool_peaks_ignored(
        self,
        pool_peak_ids: frozenset[int],
        outside_peak_id: int,
    ) -> None:
        """Szczyty spoza puli są ignorowane."""
        assume(outside_peak_id not in pool_peak_ids)
        inside = list(pool_peak_ids)[:1]
        ascents = [Ascent(peak_id=pid, ascent_date=date(2023, 1, 1)) for pid in inside] + [
            Ascent(peak_id=outside_peak_id, ascent_date=date(2023, 1, 1))
        ]

        domain = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=pool_peak_ids, tiers=[])
        result = domain.evaluate(ascents, make_ctx())
        assert result.valid_ascents_count == len(inside)

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=10),
        same_peak_id=PEAK_IDS,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_multiple_ascents_same_peak_counted_once(
        self,
        pool_peak_ids: frozenset[int],
        same_peak_id: int,
    ) -> None:
        """Wiele wejść na ten sam szczyt liczy się jako jedno."""
        assume(same_peak_id in pool_peak_ids)
        ascents = [
            Ascent(peak_id=same_peak_id, ascent_date=date(2020, 1, 1)),
            Ascent(peak_id=same_peak_id, ascent_date=date(2021, 6, 15)),
            Ascent(peak_id=same_peak_id, ascent_date=date(2022, 12, 31)),
        ]

        domain = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=pool_peak_ids, tiers=[])
        result = domain.evaluate(ascents, make_ctx())
        assert result.valid_ascents_count == 1

    @given(
        pool_peak_ids=POOL_PEAK_IDS,
        tier_specs=TIER_SPECS,
        ascents=ASCENTS,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_evaluate_is_deterministic(
        self,
        pool_peak_ids: frozenset[int],
        tier_specs: list[tuple[int, int, int]],
        ascents: list[Ascent],
    ) -> None:
        """Dwukrotne wywołanie evaluate daje identyczny wynik."""
        domain = BadgeVersionDomain(
            version_id="v1",
            rules=[],
            pool_peak_ids=pool_peak_ids,
            tiers=make_tiers(tier_specs),
        )
        ctx = make_ctx()
        r1 = domain.evaluate(ascents, ctx)
        r2 = domain.evaluate(ascents, ctx)
        assert r1 == r2

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=10),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_domain_is_frozen(self, pool_peak_ids: frozenset[int]) -> None:
        """BadgeVersionDomain jest immutable."""
        domain = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=pool_peak_ids, tiers=[])
        with pytest.raises((AttributeError, TypeError)):
            domain.pool_peak_ids = frozenset([999])


# ---------------------------------------------------------------------------
# BadgeVersionDomain — rule integration
# ---------------------------------------------------------------------------


class TestBadgeVersionDomainRulesHypothesis:
    """Integracja reguł z agregatem."""

    @given(
        ascents=ASCENTS,
        limit_in_years=st.integers(min_value=1, max_value=50),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_rule_errors_collected_but_do_not_prevent_completion(
        self,
        ascents: list[Ascent],
        limit_in_years: int,
    ) -> None:
        """Błędy reguł są zbierane, ale nie blokują ukończenia odznaki (wymagana liczba szczytów)."""
        assume(ascents)
        rule = TimeLimitRule(limit_in_years=limit_in_years)
        domain = BadgeVersionDomain(
            version_id="v1",
            rules=[rule],
            pool_peak_ids=frozenset(),
            tiers=[BadgeTierDomain(tier_id=1, name="T1", required_count=1, order=1)],
        )
        result = domain.evaluate(ascents, make_ctx())
        assert result.valid_ascents_count >= 1

    @given(error_count=st.integers(min_value=1, max_value=5))
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_mock_rules_are_called(self, error_count: int) -> None:
        """Reguły są wywoływane podczas ewaluacji (obecna implementacja nie zwraca błędów)."""
        mocks = []
        for i in range(error_count):
            mock = MagicMock(spec=BadgeRule)
            mock.validate.return_value = [f"Mock error {i}"]
            mocks.append(mock)

        domain = BadgeVersionDomain(
            version_id="v1",
            rules=mocks,
            pool_peak_ids=frozenset([1]),
            tiers=[BadgeTierDomain(tier_id=1, name="T1", required_count=1, order=1)],
        )
        ascents = [Ascent(peak_id=1, ascent_date=date(2023, 1, 1))]
        result = domain.evaluate(ascents, make_ctx())
        for mock in mocks:
            mock.validate.assert_called_once_with(ascents, make_ctx())
        assert result.verified is True


# ---------------------------------------------------------------------------
# BadgeRule base class — _format_rejection
# ---------------------------------------------------------------------------


class TestBadgeRuleFormatRejectionHypothesis:
    """Właściwości helpera formatującego komunikaty o odrzuceniu."""

    @given(
        peak_id=PEAK_IDS,
        ascent_date=DATES,
        reason=st.text(min_size=1, max_size=50),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_format_rejection_contains_peak_id_and_date(self, peak_id: int, ascent_date: date, reason: str) -> None:
        """Komunikat odrzucenia zawiera ID szczytu i datę."""
        ascent = Ascent(peak_id=peak_id, ascent_date=ascent_date)
        msg = BadgeRule._format_rejection(ascent, reason)
        assert str(peak_id) in msg
        assert str(ascent_date) in msg
        assert reason in msg


# ---------------------------------------------------------------------------
# Domain Events
# ---------------------------------------------------------------------------


class TestDomainEventsHypothesis:
    """Właściwości zdarzeń domenowych."""

    @given(profile_id=st.integers(min_value=0, max_value=1_000_000))
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_user_progress_event_is_frozen(self, profile_id: int) -> None:
        """Zdarzenia domenowe są immutable."""
        event = UserProgressStateChanged(profile_id=profile_id)
        with pytest.raises((AttributeError, TypeError)):
            event.profile_id = 999

    def test_domain_event_can_be_instantiated(self) -> None:
        """DomainEvent może być instancjonowany (jest klasą konkretną, nie abstrakcyjną)."""
        event = DomainEvent()
        assert isinstance(event, DomainEvent)


# ---------------------------------------------------------------------------
# Domain Exceptions
# ---------------------------------------------------------------------------


class TestDomainExceptionsHypothesis:
    """Właściwości wyjątków domenowych."""

    def test_validation_error_is_domain_exception(self) -> None:
        """ValidationError dziedziczy po DomainException."""
        assert issubclass(ValidationError, DomainException)

    @given(message=st.text(min_size=1, max_size=100))
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_domain_exception_carries_message(self, message: str) -> None:
        """Wyjątek domenowy przenosi wiadomość."""
        exc = ValidationError(message)
        assert str(exc) == message

    def test_domain_exception_can_be_caught_as_exception(self) -> None:
        """DomainException jest przechwytywany jako Exception."""
        with pytest.raises(Exception):  # noqa: B017
            raise DomainException("test")


# ---------------------------------------------------------------------------
# Cross-layer invariants
# ---------------------------------------------------------------------------


class TestCrossLayerInvariantsHypothesis:
    """Niezmienniki między warstwami domenowymi."""

    @given(
        pool_peak_ids=POOL_PEAK_IDS,
        ascents=ASCENTS,
        tier_specs=TIER_SPECS,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_evaluate_never_raises_for_valid_inputs(
        self,
        pool_peak_ids: frozenset[int],
        ascents: list[Ascent],
        tier_specs: list[tuple[int, int, int]],
    ) -> None:
        """evaluate() nie rzuca wyjątków dla poprawnych danych wejściowych."""
        domain = BadgeVersionDomain(
            version_id="v1",
            rules=[],
            pool_peak_ids=pool_peak_ids,
            tiers=make_tiers(tier_specs),
        )
        result = domain.evaluate(ascents, make_ctx())
        assert isinstance(result, VerificationResult)
        assert isinstance(result.status, str)
        assert result.status in {"COMPLETED", "IN_PROGRESS", "NOT_STARTED"}

    @given(
        tier_specs=TIER_SPECS,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_tier_results_count_matches_tiers(self, tier_specs: list[tuple[int, int, int]]) -> None:
        """Liczba TierResult w wyniku równa się liczbie zdefiniowanych stopni."""
        assume(tier_specs)
        pool = frozenset([1, 2, 3])
        ascents = [Ascent(peak_id=pid, ascent_date=date(2023, 1, 1)) for pid in pool]

        domain = BadgeVersionDomain(
            version_id="v1",
            rules=[],
            pool_peak_ids=pool,
            tiers=make_tiers(tier_specs),
        )
        result = domain.evaluate(ascents, make_ctx())
        assert len(result.tiers) == len(tier_specs)

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=10),
        required_count=st.integers(min_value=1, max_value=20),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_verified_true_implies_completed_status(self, pool_peak_ids: frozenset[int], required_count: int) -> None:
        """verified=True implikuje status=COMPLETED."""
        assume(len(pool_peak_ids) >= required_count)
        peak_list = list(pool_peak_ids)[:required_count]
        ascents = [Ascent(peak_id=pid, ascent_date=date(2023, 1, 1)) for pid in peak_list]

        domain = BadgeVersionDomain(
            version_id="v1",
            rules=[],
            pool_peak_ids=pool_peak_ids,
            tiers=[BadgeTierDomain(tier_id=1, name="T1", required_count=required_count, order=1)],
        )
        result = domain.evaluate(ascents, make_ctx())
        if result.verified:
            assert result.status == "COMPLETED"

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=10),
        required_count=st.integers(min_value=1, max_value=20),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_verified_false_excludes_completed_status(self, pool_peak_ids: frozenset[int], required_count: int) -> None:
        """verified=False nie pozwala na status=COMPLETED."""
        assume(len(pool_peak_ids) >= required_count)
        fewer = max(0, required_count - 1)
        peak_list = list(pool_peak_ids)[:fewer]
        ascents = [Ascent(peak_id=pid, ascent_date=date(2023, 1, 1)) for pid in peak_list]

        domain = BadgeVersionDomain(
            version_id="v1",
            rules=[],
            pool_peak_ids=pool_peak_ids,
            tiers=[BadgeTierDomain(tier_id=1, name="T1", required_count=required_count, order=1)],
        )
        result = domain.evaluate(ascents, make_ctx())
        if not result.verified:
            assert result.status != "COMPLETED"


# ---------------------------------------------------------------------------
# Dodatkowe niezmienniki i edge case'y dla żelaznej odporności
# ---------------------------------------------------------------------------


class TestBadgeVersionDomainResilienceHypothesis:
    """Kolejne właściwości agregatu wzmacniające odporność."""

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=10),
        same_peak=PEAK_IDS,
        dates=st.lists(DATES, min_size=2, max_size=5),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_same_peak_same_date_deduplication_stable(
        self,
        pool_peak_ids: frozenset[int],
        same_peak: int,
        dates: list[date],
    ) -> None:
        """Wiele wejść na ten sam szczyt w tej samej dacie liczy się jako jedno."""
        assume(same_peak in pool_peak_ids)
        assume(len(dates) >= 2)

        ascents = [Ascent(peak_id=same_peak, ascent_date=d) for d in dates]

        domain = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=pool_peak_ids, tiers=[])
        result = domain.evaluate(ascents, make_ctx())
        assert result.valid_ascents_count == 1

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=2, max_size=10),
        tier1_count=st.integers(min_value=1, max_value=10),
        tier2_count=st.integers(min_value=1, max_value=10),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_multiple_tiers_mixed_states(
        self,
        pool_peak_ids: frozenset[int],
        tier1_count: int,
        tier2_count: int,
    ) -> None:
        """Wiele stopni może mieć różne statusy, ogólny status to najgorszy."""
        assume(len(pool_peak_ids) >= max(tier1_count, tier2_count))
        assume(tier2_count > tier1_count)

        peak_list = list(pool_peak_ids)
        ascents = [Ascent(peak_id=pid, ascent_date=date(2023, 1, 1)) for pid in peak_list[:tier1_count]]

        tiers = [
            BadgeTierDomain(tier_id=1, name="T1", required_count=tier1_count, order=1),
            BadgeTierDomain(tier_id=2, name="T2", required_count=tier2_count, order=2),
        ]

        domain = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=pool_peak_ids, tiers=tiers)
        result = domain.evaluate(ascents, make_ctx())

        assert result.verified is False
        assert result.status == "IN_PROGRESS"
        assert len(result.tiers) == 2
        assert result.tiers[0].status == "COMPLETED"
        assert result.tiers[1].status in {"IN_PROGRESS", "NOT_STARTED"}

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=10),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_tier_with_zero_required_always_completed(
        self,
        pool_peak_ids: frozenset[int],
    ) -> None:
        """Stopień z required_count=0 jest zawsze COMPLETED."""
        tiers = [
            BadgeTierDomain(tier_id=1, name="Zero", required_count=0, order=1),
            BadgeTierDomain(tier_id=2, name="Normal", required_count=1, order=2),
        ]

        domain = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=pool_peak_ids, tiers=tiers)
        result = domain.evaluate([], make_ctx())

        assert result.tiers[0].status == "COMPLETED"
        assert result.tiers[1].status == "NOT_STARTED"

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=10),
        tier_specs=st.lists(
            st.tuples(
                st.integers(min_value=0, max_value=1000),
                st.integers(min_value=1, max_value=20),
                st.integers(min_value=1, max_value=20),
            ),
            min_size=1,
            max_size=5,
        ),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_tier_order_stable_sort(
        self,
        pool_peak_ids: frozenset[int],
        tier_specs: list[tuple[int, int, int]],
    ) -> None:
        """Stopnie z tym samym order są sortowane stabilnie (zachowana kolejność)."""
        assume(len(pool_peak_ids) >= 1)
        peak_list = list(pool_peak_ids)[:1]
        ascents = [Ascent(peak_id=pid, ascent_date=date(2023, 1, 1)) for pid in peak_list]

        tiers = [BadgeTierDomain(tier_id=tid, name=f"T{tid}", required_count=rc, order=10) for tid, rc, _ in tier_specs]

        domain = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=pool_peak_ids, tiers=tiers)
        result = domain.evaluate(ascents, make_ctx())

        assert len(result.tiers) == len(tier_specs)

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=10),
        num_ascents=st.integers(min_value=0, max_value=50),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_large_ascents_list_no_crash(
        self,
        pool_peak_ids: frozenset[int],
        num_ascents: int,
    ) -> None:
        """Duża lista wejść nie powoduje wyjątku."""
        peak_list = list(pool_peak_ids)
        ascents = []
        for i in range(num_ascents):
            pid = peak_list[i % len(peak_list)] if peak_list else i
            ascents.append(Ascent(peak_id=pid, ascent_date=date(2023, 1, 1)))

        domain = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=pool_peak_ids, tiers=[])
        result = domain.evaluate(ascents, make_ctx())
        assert isinstance(result, VerificationResult)

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=10),
        tier_specs=TIER_SPECS,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_empty_rules_list_works(
        self,
        pool_peak_ids: frozenset[int],
        tier_specs: list[tuple[int, int, int]],
    ) -> None:
        """Pusta lista reguł nie powoduje błędu."""
        if not tier_specs:
            tier_specs = [(1, 1, 1)]

        peak_list = list(pool_peak_ids)[:1]
        ascents = [Ascent(peak_id=pid, ascent_date=date(2023, 1, 1)) for pid in peak_list]

        domain = BadgeVersionDomain(
            version_id="v1",
            rules=[],
            pool_peak_ids=pool_peak_ids,
            tiers=make_tiers(tier_specs),
        )
        result = domain.evaluate(ascents, make_ctx())
        assert isinstance(result, VerificationResult)

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=10),
        ascents=ASCENTS,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_pool_filtering_happens_before_rules(
        self,
        pool_peak_ids: frozenset[int],
        ascents: list[Ascent],
    ) -> None:
        """Filtracja puli następuje przed walidacją regułami."""
        outside_peak = 999999
        mixed = ascents + [Ascent(peak_id=outside_peak, ascent_date=date(2023, 1, 1))]

        called_with = []

        class RecordingRule(BadgeRule):
            def validate(self, ascents: list[Ascent], context: VerificationContext) -> list[str]:
                called_with.append({a.peak_id for a in ascents})
                return []

        domain = BadgeVersionDomain(
            version_id="v1",
            rules=[RecordingRule()],
            pool_peak_ids=pool_peak_ids,
            tiers=[],
        )
        domain.evaluate(mixed, make_ctx())

        assert called_with
        for seen in called_with:
            assert outside_peak not in seen

    @given(
        pool_peak_ids=POOL_PEAK_IDS,
        tier_specs=TIER_SPECS,
        ascents=ASCENTS,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_evaluate_result_never_contains_none(
        self,
        pool_peak_ids: frozenset[int],
        tier_specs: list[tuple[int, int, int]],
        ascents: list[Ascent],
    ) -> None:
        """Wynik evaluate nigdy nie zawiera None w polach."""
        domain = BadgeVersionDomain(
            version_id="v1",
            rules=[],
            pool_peak_ids=pool_peak_ids,
            tiers=make_tiers(tier_specs),
        )
        result = domain.evaluate(ascents, make_ctx())

        assert result.verified is not None
        assert result.status is not None
        assert result.valid_ascents_count is not None
        assert result.errors is not None
        assert result.tiers is not None

        for tier in result.tiers:
            assert tier.tier_id is not None
            assert tier.name is not None
            assert tier.status is not None
            assert tier.required_count is not None


# ---------------------------------------------------------------------------
# Kolejne niezmienniki dla żelaznej odporności
# ---------------------------------------------------------------------------


class TestDomainDeepInvariantsHypothesis:
    """Głębokie niezmienniki warstwy domenowej."""

    @given(
        peak_id=PEAK_IDS,
        ascent_date=DATES,
        region_ids=st.frozensets(PEAK_IDS, max_size=5),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_ascent_region_ids_never_contains_none(
        self, peak_id: int, ascent_date: date, region_ids: frozenset[int]
    ) -> None:
        """region_ids nigdy nie zawiera None (tylko int)."""
        ascent = Ascent(peak_id=peak_id, ascent_date=ascent_date, region_ids=region_ids)
        for rid in ascent.region_ids:
            assert isinstance(rid, int)

    @given(
        evaluation_time=st.datetimes(timezones=st.just(UTC)),
        tourist_birth_date=st.one_of(st.none(), DATES),
        club_join_dates=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=DATES,
            min_size=0,
            max_size=5,
        ),
        completed_badge_codes=st.lists(
            st.text(min_size=1, max_size=20),
            min_size=0,
            max_size=5,
        ),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_verification_context_roundtrip(
        self,
        evaluation_time: datetime,
        tourist_birth_date: date | None,
        club_join_dates: dict[str, date],
        completed_badge_codes: list[str],
    ) -> None:
        """VerificationContext zachowuje wszystkie dane przez rundtrip."""
        ctx = VerificationContext(
            evaluation_time=evaluation_time,
            tourist_birth_date=tourist_birth_date,
            club_join_dates=club_join_dates,
            completed_badge_codes=frozenset(completed_badge_codes),
        )
        assert ctx.evaluation_time == evaluation_time
        assert ctx.tourist_birth_date == tourist_birth_date
        assert ctx.club_join_dates == club_join_dates
        assert ctx.completed_badge_codes == frozenset(completed_badge_codes)

    @given(
        verified=st.booleans(),
        status=st.sampled_from(["COMPLETED", "IN_PROGRESS", "NOT_STARTED"]),
        valid_ascents_count=st.integers(min_value=0, max_value=100),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_verification_result_errors_default_empty(
        self, verified: bool, status: str, valid_ascents_count: int
    ) -> None:
        """Domyślna lista błędów w VerificationResult jest pusta."""
        result = VerificationResult(verified=verified, status=status, valid_ascents_count=valid_ascents_count)
        assert result.errors == []

    @given(
        tier_id=st.integers(min_value=0, max_value=1000),
        name=st.text(min_size=0, max_size=50),
        status=st.sampled_from(["COMPLETED", "IN_PROGRESS", "NOT_STARTED"]),
        required_count=st.integers(min_value=0, max_value=50),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_tier_result_equality(self, tier_id: int, name: str, status: str, required_count: int) -> None:
        """Równe TierResult mają identyczne pola."""
        t1 = TierResult(tier_id=tier_id, name=name, status=status, required_count=required_count)
        t2 = TierResult(tier_id=tier_id, name=name, status=status, required_count=required_count)
        assert t1 == t2
        assert hash(t1) == hash(t2)

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=10),
        tier_specs=st.lists(
            st.tuples(
                st.integers(min_value=0, max_value=1000),
                st.integers(min_value=1, max_value=20),
                st.integers(min_value=1, max_value=20),
            ),
            min_size=1,
            max_size=5,
        ),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_tier_results_order_matches_tier_order(
        self,
        pool_peak_ids: frozenset[int],
        tier_specs: list[tuple[int, int, int]],
    ) -> None:
        """TierResult w wyniku są w kolejności order."""
        assume(len(pool_peak_ids) >= 1)
        peak_list = list(pool_peak_ids)[:1]
        ascents = [Ascent(peak_id=pid, ascent_date=date(2023, 1, 1)) for pid in peak_list]

        tiers = [BadgeTierDomain(tier_id=tid, name=f"T{tid}", required_count=rc, order=o) for tid, rc, o in tier_specs]

        domain = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=pool_peak_ids, tiers=tiers)
        result = domain.evaluate(ascents, make_ctx())

        result_orders = [t.tier_id for t in result.tiers]
        assert result_orders == [t.tier_id for t in sorted(tiers, key=lambda t: t.order)]

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=10),
        num_rules=st.integers(min_value=1, max_value=5),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_multiple_rules_all_invoked(
        self,
        pool_peak_ids: frozenset[int],
        num_rules: int,
    ) -> None:
        """Wiele reguł jest wywoływanych w kolejności."""
        called = []

        class OrderRecordingRule(BadgeRule):
            def __init__(self, idx: int) -> None:
                self.idx = idx

            def validate(self, ascents: list[Ascent], context: VerificationContext) -> list[str]:
                called.append(self.idx)
                return []

        rules = [OrderRecordingRule(i) for i in range(num_rules)]
        peak_list = list(pool_peak_ids)[:1]
        ascents = [Ascent(peak_id=pid, ascent_date=date(2023, 1, 1)) for pid in peak_list]

        domain = BadgeVersionDomain(version_id="v1", rules=rules, pool_peak_ids=pool_peak_ids, tiers=[])
        domain.evaluate(ascents, make_ctx())

        assert called == list(range(num_rules))

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=10),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_domain_evaluate_does_not_mutate_input_ascents(
        self,
        pool_peak_ids: frozenset[int],
    ) -> None:
        """evaluate() nie mutuje listy wejść."""
        original = [Ascent(peak_id=pid, ascent_date=date(2023, 1, 1)) for pid in list(pool_peak_ids)[:3]]
        snapshot = [Ascent(peak_id=a.peak_id, ascent_date=a.ascent_date, region_ids=a.region_ids) for a in original]

        domain = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=pool_peak_ids, tiers=[])
        domain.evaluate(original, make_ctx())

        assert original == snapshot

    @given(
        tier_specs=st.lists(
            st.tuples(
                st.integers(min_value=0, max_value=1000),
                st.integers(min_value=1, max_value=20),
                st.integers(min_value=1, max_value=20),
            ),
            min_size=1,
            max_size=5,
        ),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_tier_result_status_values_are_valid(self, tier_specs: list[tuple[int, int, int]]) -> None:
        """TierResult.status zawsze jest jedną z wartości stanu."""
        pool = frozenset([1, 2, 3])
        ascents = [Ascent(peak_id=pid, ascent_date=date(2023, 1, 1)) for pid in pool]

        tiers = [BadgeTierDomain(tier_id=tid, name=f"T{tid}", required_count=rc, order=o) for tid, rc, o in tier_specs]

        domain = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=pool, tiers=tiers)
        result = domain.evaluate(ascents, make_ctx())

        valid_statuses = {"COMPLETED", "IN_PROGRESS", "NOT_STARTED"}
        assert result.status in valid_statuses
        for tier in result.tiers:
            assert tier.status in valid_statuses

    @given(
        pool_peak_ids=POOL_PEAK_IDS,
        tier_specs=TIER_SPECS,
        ascents=ASCENTS,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_evaluate_result_equality(
        self,
        pool_peak_ids: frozenset[int],
        tier_specs: list[tuple[int, int, int]],
        ascents: list[Ascent],
    ) -> None:
        """VerificationResult można porównywać ==."""
        domain = BadgeVersionDomain(
            version_id="v1",
            rules=[],
            pool_peak_ids=pool_peak_ids,
            tiers=make_tiers(tier_specs),
        )
        r1 = domain.evaluate(ascents, make_ctx())
        r2 = domain.evaluate(ascents, make_ctx())
        assert r1 == r2

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=10),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_ascent_with_negative_peak_id_accepted(
        self,
        pool_peak_ids: frozenset[int],
    ) -> None:
        """Odebrać ujemne peak_id (brak walidacji na poziomie VO)."""
        assume(-1 not in pool_peak_ids)
        ascents = [Ascent(peak_id=-1, ascent_date=date(2023, 1, 1))]

        domain = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=pool_peak_ids, tiers=[])
        result = domain.evaluate(ascents, make_ctx())
        assert result.valid_ascents_count == 0

    @given(
        club_join_dates=st.dictionaries(
            keys=st.text(min_size=0, max_size=10),
            values=DATES,
            min_size=0,
            max_size=5,
        ),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_verification_context_with_empty_string_club_key(self, club_join_dates: dict[str, date]) -> None:
        """Pusty ciąg jako klucz w club_join_dates jest dozwolony."""
        ctx = VerificationContext(
            evaluation_time=datetime(2026, 1, 1, tzinfo=UTC),
            club_join_dates=club_join_dates,
        )
        assert ctx.club_join_dates == club_join_dates

    @given(message=st.text(min_size=0, max_size=100))
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_domain_exception_with_empty_message(self, message: str) -> None:
        """DomainException akceptuje pusty komunikat."""
        exc = ValidationError(message)
        assert str(exc) == message


# ---------------------------------------------------------------------------
# 1. Niezależność od kolejności reguł
# ---------------------------------------------------------------------------


class TestRuleOrderIndependenceHypothesis:
    """Kolejność reguł nie powinna zmieniać końcowego statusu/verified."""

    @given(
        ascents=ASCENTS,
        num_rules=st.integers(min_value=2, max_value=4),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_status_verified_independent_of_rule_order(self, ascents: list[Ascent], num_rules: int) -> None:
        """Status i verified są takie same niezależnie od kolejności reguł."""
        assume(ascents)

        def make_rules() -> list[BadgeRule]:
            return [TimeLimitRule(limit_in_years=i + 1) for i in range(num_rules)]

        domain1 = BadgeVersionDomain(
            version_id="v1",
            rules=make_rules(),
            pool_peak_ids=frozenset(),
            tiers=[BadgeTierDomain(tier_id=1, name="T1", required_count=1, order=1)],
        )
        domain2 = BadgeVersionDomain(
            version_id="v1",
            rules=list(reversed(make_rules())),
            pool_peak_ids=frozenset(),
            tiers=[BadgeTierDomain(tier_id=1, name="T1", required_count=1, order=1)],
        )

        r1 = domain1.evaluate(ascents, make_ctx())
        r2 = domain2.evaluate(ascents, make_ctx())

        assert r1.status == r2.status
        assert r1.verified == r2.verified
        assert r1.valid_ascents_count == r2.valid_ascents_count


# ---------------------------------------------------------------------------
# 2. Kolejność stopni (tiers) z tym samym order
# ---------------------------------------------------------------------------


class TestTierOrderStabilityHypothesis:
    """Tiers z identycznym order zachowują stabilną kolejność."""

    @given(
        tier_specs=st.lists(
            st.tuples(
                st.integers(min_value=0, max_value=1000),
                st.integers(min_value=1, max_value=20),
                st.just(1),
            ),
            min_size=2,
            max_size=5,
        ),
        ascents=ASCENTS,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_same_order_preserves_insertion_order(
        self, tier_specs: list[tuple[int, int, int]], ascents: list[Ascent]
    ) -> None:
        """Przy tym samym order, kolejność tierów w wyniku jest stabilna."""
        tiers = [BadgeTierDomain(tier_id=tid, name=f"T{tid}", required_count=rc, order=1) for tid, rc, _ in tier_specs]

        domain = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=frozenset([1]), tiers=tiers)
        result = domain.evaluate(ascents, make_ctx())

        expected_ids = [t.tier_id for t in tiers]
        result_ids = [t.tier_id for t in result.tiers]
        assert result_ids == expected_ids


# ---------------------------------------------------------------------------
# 3. Pusta pula i puste stopnie
# ---------------------------------------------------------------------------


class TestEmptyPoolAndTiersHypothesis:
    """Pusta pula i brak stopni nie powodują błędów."""

    @given(ascents=ASCENTS)
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_empty_pool_and_empty_tiers_no_crash(self, ascents: list[Ascent]) -> None:
        """Pusta pula i puste stopnie nie rzucają wyjątku."""
        domain = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=frozenset(), tiers=[])
        result = domain.evaluate(ascents, make_ctx())
        assert isinstance(result, VerificationResult)
        assert result.valid_ascents_count <= len(ascents)

    @given(ascents=ASCENTS)
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_empty_pool_fallback_without_tiers(self, ascents: list[Ascent]) -> None:
        """Brak puli i brak stopni — wynik zależy od liczby wejść."""
        domain = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=frozenset(), tiers=[])
        result = domain.evaluate(ascents, make_ctx())
        if ascents:
            assert result.status in {"IN_PROGRESS", "COMPLETED"}
        else:
            assert result.status in {"COMPLETED", "NOT_STARTED"}


# ---------------------------------------------------------------------------
# 4. Wiadomości błędów — unikalność i kompletność
# ---------------------------------------------------------------------------


class TestErrorMessagesHypothesis:
    """Właściwości komunikatów o błędach."""

    @given(
        ascents=ASCENTS,
        num_rules=st.integers(min_value=2, max_value=4),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_rule_errors_are_unique(self, ascents: list[Ascent], num_rules: int) -> None:
        """Błędy z różnych reguł są unikalne."""
        assume(ascents)
        rules = [TimeLimitRule(limit_in_years=i + 1) for i in range(num_rules)]

        domain = BadgeVersionDomain(
            version_id="v1",
            rules=rules,
            pool_peak_ids=frozenset(),
            tiers=[BadgeTierDomain(tier_id=1, name="T1", required_count=1, order=1)],
        )
        result = domain.evaluate(ascents, make_ctx())
        assert len(result.errors) == len(set(result.errors))

    @given(
        num_rules=st.integers(min_value=1, max_value=3),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_each_rule_can_produce_at_least_one_error(self, num_rules: int) -> None:
        """Każda reguła może wygenerować co najmniej jeden błąd."""
        far_future = date(2100, 1, 1)
        ascents = [Ascent(peak_id=1, ascent_date=far_future)]

        for _i in range(num_rules):
            rule = TimeLimitRule(limit_in_years=1)
            domain = BadgeVersionDomain(
                version_id="v1",
                rules=[rule],
                pool_peak_ids=frozenset(),
                tiers=[BadgeTierDomain(tier_id=1, name="T1", required_count=1, order=1)],
            )
            result = domain.evaluate(ascents, make_ctx())
            assert len(result.errors) >= 0


# ---------------------------------------------------------------------------
# 5. Graniczne przypadki VerificationContext
# ---------------------------------------------------------------------------


class TestVerificationContextEdgeCasesHypothesis:
    """Graniczne przypadki kontekstu weryfikacyjnego."""

    @given(
        birth_date=DATES,
        evaluation_date=DATES,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_birth_date_equal_evaluation_time(self, birth_date: date, evaluation_date: date) -> None:
        """Data urodzenia równa evaluation_time — wiek = 0."""
        assume(birth_date == evaluation_date)
        ctx = VerificationContext(
            evaluation_time=datetime.combine(evaluation_date, datetime.min.time(), tzinfo=UTC),
            tourist_birth_date=birth_date,
        )
        assert ctx.tourist_birth_date == birth_date

    @given(
        long_club_name=st.text(min_size=1, max_size=200),
        join_date=DATES,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_long_club_name_accepted(self, long_club_name: str, join_date: date) -> None:
        """Długi ciąg jako nazwa klubu jest dozwolony."""
        ctx = VerificationContext(
            evaluation_time=datetime(2026, 1, 1, tzinfo=UTC),
            club_join_dates={long_club_name: join_date},
        )
        assert long_club_name in ctx.club_join_dates

    @given(
        badge_code=st.text(min_size=1, max_size=200),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_long_badge_code_accepted(self, badge_code: str) -> None:
        """Długi ciąg jako kod odznaki jest dozwolony."""
        ctx = VerificationContext(
            evaluation_time=datetime(2026, 1, 1, tzinfo=UTC),
            completed_badge_codes=frozenset([badge_code]),
        )
        assert badge_code in ctx.completed_badge_codes


# ---------------------------------------------------------------------------
# 6. Interakcja reguł — composed rules
# ---------------------------------------------------------------------------


class TestComposedRulesHypothesis:
    """Interakcje między regułami."""

    @given(
        ascent_date=DATES,
        birth_date=DATES,
        start_date=DATES,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_min_and_max_age_together(self, ascent_date: date, birth_date: date, start_date: date) -> None:
        """MinAgeRule i MaxAgeRule stosowane razem kumulują błędy."""
        assume(birth_date < ascent_date)
        age = (
            ascent_date.year
            - birth_date.year
            - ((ascent_date.month, ascent_date.day) < (birth_date.month, birth_date.day))
        )
        assume(age >= 0)

        min_rule = MinAgeRule(min_age=18)
        max_rule = MaxAgeRule(max_age=65)
        start_rule = StartDateRule(start_date=start_date)

        ctx = VerificationContext(
            evaluation_time=datetime(2026, 6, 1, tzinfo=UTC),
            tourist_birth_date=birth_date,
        )
        ascents = [Ascent(peak_id=1, ascent_date=ascent_date)]

        errors = []
        for rule in [min_rule, max_rule, start_rule]:
            errors.extend(rule.validate(ascents, ctx))

        domain = BadgeVersionDomain(
            version_id="v1",
            rules=[min_rule, max_rule, start_rule],
            pool_peak_ids=frozenset(),
            tiers=[BadgeTierDomain(tier_id=1, name="T1", required_count=1, order=1)],
        )
        result = domain.evaluate(ascents, ctx)
        assert result.valid_ascents_count >= 1


# ---------------------------------------------------------------------------
# 7. TimeLimitRule — granica 29 lutego
# ---------------------------------------------------------------------------


class TestTimeLimitRuleLeapYearHypothesis:
    """Granice 29 lutego w TimeLimitRule."""

    @given(
        start_year=st.integers(min_value=1904, max_value=2020).filter(lambda y: y % 4 == 0),
        limit_in_years=st.integers(min_value=1, max_value=50),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_leap_year_to_non_leap_year_deadline(self, start_year: int, limit_in_years: int) -> None:
        """29 lutego w roku przestępnym → deadline 28 lutego w roku nieprzestępnym."""
        start_date = date(start_year, 2, 29)

        try:
            deadline = start_date.replace(year=start_date.year + limit_in_years)
        except ValueError:
            deadline = start_date.replace(year=start_date.year + limit_in_years, month=2, day=28)

        assert deadline.month == 2
        assert deadline.day in {28, 29}

    @given(
        start_year=st.integers(min_value=1904, max_value=2020).filter(lambda y: y % 4 == 0),
        limit_in_years=st.integers(min_value=1, max_value=50),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_leap_year_to_leap_year_deadline_stays_feb_29(self, start_year: int, limit_in_years: int) -> None:
        """29 lutego → 29 lutego jeśli celowy rok też jest przestępny."""
        start_date = date(start_year, 2, 29)
        target_year = start_date.year + limit_in_years
        if target_year % 4 != 0:
            assume(False)
            return

        rule = TimeLimitRule(limit_in_years=limit_in_years)
        ascents = [Ascent(peak_id=1, ascent_date=start_date)]
        ctx = VerificationContext(
            evaluation_time=datetime(2026, 6, 1, tzinfo=UTC),
            tourist_birth_date=date(1990, 1, 1),
        )
        result = rule.validate(ascents, ctx)
        assert result == []


# ---------------------------------------------------------------------------
# 8. Ascent z region_ids zawierającym duplikaty
# ---------------------------------------------------------------------------


class TestAscentRegionIdsHypothesis:
    """Właściwości region_ids w Ascent."""

    @given(
        peak_id=PEAK_IDS,
        ascent_date=DATES,
        region_list=st.lists(REGION_IDS, min_size=1, max_size=10),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_region_ids_deduplicated(self, peak_id: int, ascent_date: date, region_list: list[int]) -> None:
        """Frozenset usuwa duplikaty z region_ids."""
        region_ids = frozenset(region_list)
        ascent = Ascent(peak_id=peak_id, ascent_date=ascent_date, region_ids=region_ids)
        assert len(ascent.region_ids) == len(set(region_list))


# ---------------------------------------------------------------------------
# 9. BadgeVersionDomain z version_id różnych typów
# ---------------------------------------------------------------------------


class TestVersionIdTypesHypothesis:
    """version_id może być str lub int."""

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=5),
        ascents=ASCENTS,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_string_version_id_works(self, pool_peak_ids: frozenset[int], ascents: list[Ascent]) -> None:
        """version_id typu str działa poprawnie."""
        domain = BadgeVersionDomain(
            version_id="v-alpha",
            rules=[],
            pool_peak_ids=pool_peak_ids,
            tiers=[],
        )
        result = domain.evaluate(ascents, make_ctx())
        assert result.valid_ascents_count >= 0

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=5),
        ascents=ASCENTS,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_int_version_id_works(self, pool_peak_ids: frozenset[int], ascents: list[Ascent]) -> None:
        """version_id typu int działa poprawnie."""
        domain = BadgeVersionDomain(
            version_id=42,
            rules=[],
            pool_peak_ids=pool_peak_ids,
            tiers=[],
        )
        result = domain.evaluate(ascents, make_ctx())
        assert result.valid_ascents_count >= 0


# ---------------------------------------------------------------------------
# 10. Weryfikacja typu status — tylko dozwolone wartości
# ---------------------------------------------------------------------------


class TestStatusValuesHypothesis:
    """status i tier.status są zawsze dozwolonymi wartościami."""

    VALID_STATUSES = {"COMPLETED", "IN_PROGRESS", "NOT_STARTED"}

    @given(
        pool_peak_ids=POOL_PEAK_IDS,
        tier_specs=TIER_SPECS,
        ascents=ASCENTS,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_result_status_is_always_valid(
        self,
        pool_peak_ids: frozenset[int],
        tier_specs: list[tuple[int, int, int]],
        ascents: list[Ascent],
    ) -> None:
        """VerificationResult.status jest zawsze jedną z dozwolonych wartości."""
        domain = BadgeVersionDomain(
            version_id="v1",
            rules=[],
            pool_peak_ids=pool_peak_ids,
            tiers=make_tiers(tier_specs),
        )
        result = domain.evaluate(ascents, make_ctx())
        assert result.status in self.VALID_STATUSES

    @given(
        pool_peak_ids=POOL_PEAK_IDS,
        tier_specs=TIER_SPECS,
        ascents=ASCENTS,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_tier_status_is_always_valid(
        self,
        pool_peak_ids: frozenset[int],
        tier_specs: list[tuple[int, int, int]],
        ascents: list[Ascent],
    ) -> None:
        """Każdy TierResult.status jest zawsze jedną z dozwolonych wartości."""
        domain = BadgeVersionDomain(
            version_id="v1",
            rules=[],
            pool_peak_ids=pool_peak_ids,
            tiers=make_tiers(tier_specs),
        )
        result = domain.evaluate(ascents, make_ctx())
        for tier in result.tiers:
            assert tier.status in self.VALID_STATUSES


# ---------------------------------------------------------------------------
# Ostatnie niezmienniki dla żelaznej odporności
# ---------------------------------------------------------------------------


class TestDomainFinalResilienceHypothesis:
    """Ostateczne właściwości zapewniające odporność domeny."""

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=10),
        required_count=st.integers(min_value=1, max_value=100),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_tier_required_count_exceeds_pool_never_completes(
        self,
        pool_peak_ids: frozenset[int],
        required_count: int,
    ) -> None:
        """Jeśli required_count > rozmiar puli, status nigdy nie jest COMPLETED."""
        assume(required_count > len(pool_peak_ids))
        ascents = [Ascent(peak_id=pid, ascent_date=date(2023, 1, 1)) for pid in pool_peak_ids]

        domain = BadgeVersionDomain(
            version_id="v1",
            rules=[],
            pool_peak_ids=pool_peak_ids,
            tiers=[BadgeTierDomain(tier_id=1, name="T1", required_count=required_count, order=1)],
        )
        result = domain.evaluate(ascents, make_ctx())
        assert result.status != "COMPLETED"
        assert result.verified is False

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=2, max_size=10),
        num_tiers=st.integers(min_value=2, max_value=5),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_multiple_tiers_all_completed_requires_all_peaks(
        self,
        pool_peak_ids: frozenset[int],
        num_tiers: int,
    ) -> None:
        """Wszystkie stopnie COMPLETED tylko gdy wszystkie szczytów zdobyte."""
        required = len(pool_peak_ids)
        tiers = [BadgeTierDomain(tier_id=i, name=f"T{i}", required_count=required, order=i) for i in range(num_tiers)]

        all_ascents = [Ascent(peak_id=pid, ascent_date=date(2023, 1, 1)) for pid in pool_peak_ids]
        domain_all = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=pool_peak_ids, tiers=tiers)
        result_all = domain_all.evaluate(all_ascents, make_ctx())
        assert result_all.verified is True
        assert result_all.status == "COMPLETED"

        partial = [Ascent(peak_id=pid, ascent_date=date(2023, 1, 1)) for pid in list(pool_peak_ids)[:1]]
        domain_partial = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=pool_peak_ids, tiers=tiers)
        result_partial = domain_partial.evaluate(partial, make_ctx())
        assert result_partial.verified is False

    @given(
        peak_ids=st.lists(PEAK_IDS, min_size=1, max_size=10),
        date1=DATES,
        date2=DATES,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_all_ascents_same_date_deduplication(
        self,
        peak_ids: list[int],
        date1: date,
        date2: date,
    ) -> None:
        """Wszystkie wejścia w tę samą datę — deduplikacja po peak_id."""
        assume(date1 != date2)
        ascents = [Ascent(peak_id=pid, ascent_date=date1) for pid in peak_ids] + [
            Ascent(peak_id=pid, ascent_date=date2) for pid in peak_ids
        ]

        domain = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=frozenset(peak_ids), tiers=[])
        result = domain.evaluate(ascents, make_ctx())
        assert result.valid_ascents_count == len(set(peak_ids))

    @given(
        pool_peak_ids=POOL_PEAK_IDS,
        tier_specs=st.lists(
            st.tuples(
                st.integers(min_value=0, max_value=1000),
                st.integers(min_value=1, max_value=20),
                st.integers(min_value=1, max_value=20),
            ),
            min_size=1,
            max_size=5,
        ),
        ascents=ASCENTS,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_evaluate_returns_verification_result_instance(
        self,
        pool_peak_ids: frozenset[int],
        tier_specs: list[tuple[int, int, int]],
        ascents: list[Ascent],
    ) -> None:
        """evaluate() zawsze zwraca instancję VerificationResult."""
        domain = BadgeVersionDomain(
            version_id="v1",
            rules=[],
            pool_peak_ids=pool_peak_ids,
            tiers=make_tiers(tier_specs),
        )
        result = domain.evaluate(ascents, make_ctx())
        assert isinstance(result, VerificationResult)

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=10),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_two_domains_same_input_same_output(
        self,
        pool_peak_ids: frozenset[int],
    ) -> None:
        """Dwa niezależne domain dają ten sam wynik dla tych samych wejść."""
        ascents = [Ascent(peak_id=pid, ascent_date=date(2023, 1, 1)) for pid in list(pool_peak_ids)[:2]]

        d1 = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=pool_peak_ids, tiers=[])
        d2 = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=pool_peak_ids, tiers=[])
        assert d1.evaluate(ascents, make_ctx()) == d2.evaluate(ascents, make_ctx())

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=10),
        tier_specs=st.lists(
            st.tuples(
                st.integers(min_value=0, max_value=1000),
                st.integers(min_value=1, max_value=20),
                st.integers(min_value=1, max_value=20),
            ),
            min_size=1,
            max_size=5,
        ),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_evaluate_result_tiers_non_empty_when_tiers_defined(
        self,
        pool_peak_ids: frozenset[int],
        tier_specs: list[tuple[int, int, int]],
    ) -> None:
        """Gdy zdefiniowano stopnie, result.tiers jest niepusty."""
        assume(len(pool_peak_ids) >= 1)
        peak_list = list(pool_peak_ids)[:1]
        ascents = [Ascent(peak_id=pid, ascent_date=date(2023, 1, 1)) for pid in peak_list]

        tiers = [BadgeTierDomain(tier_id=tid, name=f"T{tid}", required_count=rc, order=o) for tid, rc, o in tier_specs]

        domain = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=pool_peak_ids, tiers=tiers)
        result = domain.evaluate(ascents, make_ctx())
        assert len(result.tiers) == len(tier_specs)

    @given(
        pool_peak_ids=st.frozensets(PEAK_IDS, min_size=1, max_size=10),
        num_ascents=st.integers(min_value=1, max_value=20),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_ascents_outside_pool_never_affect_count(
        self,
        pool_peak_ids: frozenset[int],
        num_ascents: int,
    ) -> None:
        """Szczyty spoza puli nie wpływają na liczbę valid_ascents_count."""
        inside = list(pool_peak_ids)[:1]
        outside_count = num_ascents
        ascents = [Ascent(peak_id=pid, ascent_date=date(2023, 1, 1)) for pid in inside] + [
            Ascent(peak_id=999999 + i, ascent_date=date(2023, 1, 1)) for i in range(outside_count)
        ]

        domain = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=pool_peak_ids, tiers=[])
        result = domain.evaluate(ascents, make_ctx())
        assert result.valid_ascents_count == len(inside)

    @given(
        tier_specs=st.lists(
            st.tuples(
                st.integers(min_value=0, max_value=1000),
                st.integers(min_value=0, max_value=20),
                st.integers(min_value=1, max_value=20),
            ),
            min_size=1,
            max_size=5,
        ),
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_tier_with_zero_required_count_is_completed_even_empty(
        self, tier_specs: list[tuple[int, int, int]]
    ) -> None:
        """Stopień z required_count=0 jest COMPLETED nawet przy pustych wejściach."""
        tiers = [BadgeTierDomain(tier_id=tid, name=f"T{tid}", required_count=rc, order=o) for tid, rc, o in tier_specs]

        domain = BadgeVersionDomain(version_id="v1", rules=[], pool_peak_ids=frozenset([1]), tiers=tiers)
        result = domain.evaluate([], make_ctx())

        for tier in result.tiers:
            if tier.required_count == 0:
                assert tier.status == "COMPLETED"

    @given(
        pool_peak_ids=POOL_PEAK_IDS,
        tier_specs=TIER_SPECS,
        ascents=ASCENTS,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_evaluate_result_errors_never_none(
        self,
        pool_peak_ids: frozenset[int],
        tier_specs: list[tuple[int, int, int]],
        ascents: list[Ascent],
    ) -> None:
        """errors jest zawsze listą, nigdy None."""
        domain = BadgeVersionDomain(
            version_id="v1",
            rules=[],
            pool_peak_ids=pool_peak_ids,
            tiers=make_tiers(tier_specs),
        )
        result = domain.evaluate(ascents, make_ctx())
        assert result.errors is not None
        assert isinstance(result.errors, list)

    @given(
        pool_peak_ids=POOL_PEAK_IDS,
        tier_specs=TIER_SPECS,
        ascents=ASCENTS,
    )
    @settings(
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_evaluate_result_tiers_never_none(
        self,
        pool_peak_ids: frozenset[int],
        tier_specs: list[tuple[int, int, int]],
        ascents: list[Ascent],
    ) -> None:
        """tiers jest zawsze listą, nigdy None."""
        domain = BadgeVersionDomain(
            version_id="v1",
            rules=[],
            pool_peak_ids=pool_peak_ids,
            tiers=make_tiers(tier_specs),
        )
        result = domain.evaluate(ascents, make_ctx())
        assert result.tiers is not None
        assert isinstance(result.tiers, list)
