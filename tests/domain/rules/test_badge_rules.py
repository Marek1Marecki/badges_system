"""Testy dla reguł biznesowych zdobywania odznak."""

from datetime import date

import pytest

from domain.rules.badge_rules import (
    BadgeRule,
    GroupedAlternativesRule,
    MandatoryObjectsRule,
    MinAgeRule,
    RequiresClubJoinDateRule,
    StartDateRule,
    TimeLimitRule,
)
from domain.value_objects.ascent import Ascent


class TestTimeLimitRule:
    """Testy klasy TimeLimitRule."""

    def test_validate_within_time_limit(self):
        """Test walidacji w ramach limitu czasowego."""
        rule = TimeLimitRule(limit_in_years=2)

        ascents = [
            Ascent(peak_id=1, ascent_date=date(2023, 1, 1)),
            Ascent(peak_id=2, ascent_date=date(2024, 6, 1)),
        ]

        errors = rule.validate(ascents)
        assert errors == []

    def test_validate_exactly_at_limit(self):
        """Test walidacji dokładnie na granicy limitu."""
        rule = TimeLimitRule(limit_in_years=1)

        ascents = [
            Ascent(peak_id=1, ascent_date=date(2023, 1, 1)),
            Ascent(peak_id=2, ascent_date=date(2024, 1, 1)),
        ]

        errors = rule.validate(ascents)
        assert errors == []

    def test_validate_exceeds_time_limit(self):
        """Test walidacji z przekroczeniem limitu czasowego."""
        rule = TimeLimitRule(limit_in_years=1)

        ascents = [
            Ascent(peak_id=1, ascent_date=date(2022, 1, 1)),
            Ascent(peak_id=2, ascent_date=date(2023, 6, 1)),
        ]

        errors = rule.validate(ascents)
        assert len(errors) == 1
        assert "Przekroczono limit czasu" in errors[0]
        assert "wymagała ukończenia do" in errors[0]

    def test_validate_empty_ascents_list(self):
        """Test walidacji z pustą listą wejść."""
        rule = TimeLimitRule(limit_in_years=1)

        errors = rule.validate([])
        assert errors == []

    def test_validate_single_ascent(self):
        """Test walidacji z pojedynczym wejściem."""
        rule = TimeLimitRule(limit_in_years=1)

        ascents = [Ascent(peak_id=1, ascent_date=date(2023, 1, 1))]

        errors = rule.validate(ascents)
        assert errors == []

    def test_validate_different_order(self):
        """Test walidacji z wejściami w innej kolejności."""
        rule = TimeLimitRule(limit_in_years=1)

        ascents = [
            Ascent(peak_id=2, ascent_date=date(2023, 6, 1)),
            Ascent(peak_id=1, ascent_date=date(2023, 1, 1)),
        ]

        errors = rule.validate(ascents)
        assert errors == []

    def test_validate_zero_year_limit(self):
        """Test walidacji z zerowym limitem lat."""
        rule = TimeLimitRule(limit_in_years=0)

        ascents = [
            Ascent(peak_id=1, ascent_date=date(2023, 1, 1)),
            Ascent(peak_id=2, ascent_date=date(2023, 1, 1)),
        ]

        errors = rule.validate(ascents)
        assert errors == []

    def test_validate_large_time_span(self):
        """Test walidacji z dużym zakresem czasowym."""
        rule = TimeLimitRule(limit_in_years=10)

        ascents = [
            Ascent(peak_id=1, ascent_date=date(2010, 1, 1)),
            Ascent(peak_id=2, ascent_date=date(2019, 12, 30)),
        ]

        errors = rule.validate(ascents)
        assert errors == []


class TestRequiresClubJoinDateRule:
    """Testy klasy RequiresClubJoinDateRule."""

    def test_validate_all_ascents_after_join_date(self):
        """Test walidacji z wszystkimi wejściami po dacie dołączenia do klubu."""
        rule = RequiresClubJoinDateRule()

        ascents = [
            Ascent(peak_id=1, ascent_date=date(2020, 6, 1)),
            Ascent(peak_id=2, ascent_date=date(2021, 1, 15)),
        ]

        errors = rule.validate(ascents)
        assert errors == []

    def test_validate_ascents_before_join_date(self):
        """Test walidacji z wejściami przed datą dołączenia do klubu."""
        rule = RequiresClubJoinDateRule()

        ascents = [
            Ascent(peak_id=1, ascent_date=date(2019, 6, 1)),
            Ascent(peak_id=2, ascent_date=date(2020, 6, 1)),
        ]

        errors = rule.validate(ascents)
        assert len(errors) == 1
        assert (
            "Wejście na obiekt (ID: 1, Data: 2019-06-01) odrzucone: wejście odbyło się przed dołączeniem do klubu (2020-01-01)."
            in errors[0]
        )

    def test_validate_multiple_ascents_before_join_date(self):
        """Test walidacji z wieloma wejściami przed datą dołączenia."""
        rule = RequiresClubJoinDateRule()

        ascents = [
            Ascent(peak_id=1, ascent_date=date(2018, 5, 1)),
            Ascent(peak_id=2, ascent_date=date(2019, 3, 15)),
            Ascent(peak_id=3, ascent_date=date(2020, 2, 1)),
        ]

        errors = rule.validate(ascents)
        assert len(errors) == 2
        assert (
            "Wejście na obiekt (ID: 1, Data: 2018-05-01) odrzucone: wejście odbyło się przed dołączeniem do klubu (2020-01-01)."
            in errors[0]
        )
        assert (
            "Wejście na obiekt (ID: 2, Data: 2019-03-15) odrzucone: wejście odbyło się przed dołączeniem do klubu (2020-01-01)."
            in errors[1]
        )

    def test_validate_empty_ascents_list(self):
        """Test walidacji z pustą listą wejść."""
        rule = RequiresClubJoinDateRule()

        errors = rule.validate([])
        assert errors == []

    def test_validate_exactly_on_join_date(self):
        """Test walidacji z wejściem dokładnie w dacie dołączenia."""
        rule = RequiresClubJoinDateRule()

        ascents = [Ascent(peak_id=1, ascent_date=date(2020, 1, 1))]

        errors = rule.validate(ascents)
        assert errors == []


class TestMinAgeRule:
    """Testy klasy MinAgeRule."""

    def test_validate_all_ascents_meet_min_age(self):
        """Test walidacji z wszystkimi wejściami spełniającymi minimalny wiek."""
        rule = MinAgeRule(min_age=8)

        ascents = [
            Ascent(peak_id=1, ascent_date=date(2023, 6, 1)),  # 8 lat
            Ascent(peak_id=2, ascent_date=date(2024, 1, 15)),  # 9 lat
        ]

        errors = rule.validate(ascents)
        assert errors == []

    def test_validate_ascents_below_min_age(self):
        """Test walidacji z wejściami poniżej minimalnego wieku."""
        rule = MinAgeRule(min_age=10)

        ascents = [
            Ascent(peak_id=1, ascent_date=date(2022, 6, 1)),  # 7 lat
            Ascent(peak_id=2, ascent_date=date(2024, 6, 1)),  # 9 lat
        ]

        errors = rule.validate(ascents)
        assert len(errors) == 2
        assert (
            "Wejście na obiekt (ID: 1, Data: 2022-06-01) odrzucone: wiek (7 lat) był mniejszy niż wymagane 10 lat."
            in errors[0]
        )
        assert (
            "Wejście na obiekt (ID: 2, Data: 2024-06-01) odrzucone: wiek (9 lat) był mniejszy niż wymagane 10 lat."
            in errors[1]
        )

    def test_validate_birthday_edge_case(self):
        """Test walidacji przypadków granicznych związanych z urodzinami."""
        rule = MinAgeRule(min_age=8)

        # Dzień przed 8. urodzinami
        ascents_before = [Ascent(peak_id=1, ascent_date=date(2022, 12, 31))]
        errors = rule.validate(ascents_before)
        assert len(errors) == 1
        assert (
            "Wejście na obiekt (ID: 1, Data: 2022-12-31) odrzucone: wiek (7 lat) był mniejszy niż wymagane 8 lat."
            in errors[0]
        )

        # W dniu 8. urodzin
        ascents_on = [Ascent(peak_id=2, ascent_date=date(2023, 1, 1))]
        errors = rule.validate(ascents_on)
        assert errors == []

    def test_validate_empty_ascents_list(self):
        """Test walidacji z pustą listą wejść."""
        rule = MinAgeRule(min_age=10)

        errors = rule.validate([])
        assert errors == []

    def test_validate_zero_min_age(self):
        """Test walidacji z zerowym minimalnym wiekiem."""
        rule = MinAgeRule(min_age=0)

        ascents = [Ascent(peak_id=1, ascent_date=date(2018, 6, 1))]  # 3 lat

        errors = rule.validate(ascents)
        assert errors == []


class TestStartDateRule:
    """Testy klasy StartDateRule."""

    def test_validate_all_ascents_after_start_date(self):
        """Test walidacji z wszystkimi wejściami po dacie startowej."""
        rule = StartDateRule(start_date=date(2020, 6, 1))

        ascents = [
            Ascent(peak_id=1, ascent_date=date(2020, 6, 1)),
            Ascent(peak_id=2, ascent_date=date(2021, 1, 15)),
        ]

        errors = rule.validate(ascents)
        assert errors == []

    def test_validate_ascents_before_start_date(self):
        """Test walidacji z wejściami przed datą startową."""
        rule = StartDateRule(start_date=date(2020, 6, 1))

        ascents = [
            Ascent(peak_id=1, ascent_date=date(2019, 6, 1)),
            Ascent(peak_id=2, ascent_date=date(2020, 6, 1)),
        ]

        errors = rule.validate(ascents)
        assert len(errors) == 1
        assert (
            "Wejście na obiekt (ID: 1, Data: 2019-06-01) odrzucone: wejście było przed wejściem regulaminu w życie (2020-06-01)."
            in errors[0]
        )

    def test_validate_multiple_ascents_before_start_date(self):
        """Test walidacji z wieloma wejściami przed datą startową."""
        rule = StartDateRule(start_date=date(2020, 6, 1))

        ascents = [
            Ascent(peak_id=1, ascent_date=date(2018, 5, 1)),
            Ascent(peak_id=2, ascent_date=date(2019, 3, 15)),
            Ascent(peak_id=3, ascent_date=date(2020, 6, 1)),
        ]

        errors = rule.validate(ascents)
        assert len(errors) == 2
        assert (
            "Wejście na obiekt (ID: 1, Data: 2018-05-01) odrzucone: wejście było przed wejściem regulaminu w życie (2020-06-01)."
            in errors[0]
        )
        assert (
            "Wejście na obiekt (ID: 2, Data: 2019-03-15) odrzucone: wejście było przed wejściem regulaminu w życie (2020-06-01)."
            in errors[1]
        )

    def test_validate_empty_ascents_list(self):
        """Test walidacji z pustą listą wejść."""
        rule = StartDateRule(start_date=date(2020, 6, 1))

        errors = rule.validate([])
        assert errors == []

    def test_validate_exactly_on_start_date(self):
        """Test walidacji z wejściem dokładnie w dacie startowej."""
        rule = StartDateRule(start_date=date(2020, 6, 1))

        ascents = [Ascent(peak_id=1, ascent_date=date(2020, 6, 1))]

        errors = rule.validate(ascents)
        assert errors == []


class TestMandatoryObjectsRule:
    """Testy klasy MandatoryObjectsRule."""

    def test_validate_all_mandatory_peaks_climbed(self):
        """Test walidacji gdy wszystkie obowiązkowe szczyty zostały zdobyte."""
        rule = MandatoryObjectsRule(mandatory_peak_ids={1, 2, 3})

        ascents = [
            Ascent(peak_id=1, ascent_date=date(2023, 1, 1)),
            Ascent(peak_id=2, ascent_date=date(2023, 2, 1)),
            Ascent(peak_id=3, ascent_date=date(2023, 3, 1)),
            Ascent(peak_id=4, ascent_date=date(2023, 4, 1)),  # dodatkowy
        ]

        errors = rule.validate(ascents)
        assert errors == []

    def test_validate_missing_mandatory_peaks(self):
        """Test walidacji gdy brakuje obowiązkowych szczytów."""
        rule = MandatoryObjectsRule(mandatory_peak_ids={1, 2, 3, 4})

        ascents = [
            Ascent(peak_id=1, ascent_date=date(2023, 1, 1)),
            Ascent(peak_id=3, ascent_date=date(2023, 3, 1)),
        ]

        errors = rule.validate(ascents)
        assert len(errors) == 1
        assert "Brakuje obowiązkowych obiektów o ID: [2, 4]" in errors[0]

    def test_validate_no_mandatory_peaks_climbed(self):
        """Test walidacji gdy żaden obowiązkowy szczyt nie został zdobyty."""
        rule = MandatoryObjectsRule(mandatory_peak_ids={1, 2, 3})

        ascents = [
            Ascent(peak_id=4, ascent_date=date(2023, 1, 1)),
            Ascent(peak_id=5, ascent_date=date(2023, 2, 1)),
        ]

        errors = rule.validate(ascents)
        assert len(errors) == 1
        assert "Brakuje obowiązkowych obiektów o ID: [1, 2, 3]" in errors[0]

    def test_validate_empty_ascents_list(self):
        """Test walidacji z pustą listą wejść."""
        rule = MandatoryObjectsRule(mandatory_peak_ids={1, 2, 3})

        errors = rule.validate([])
        assert len(errors) == 1
        assert "Brakuje obowiązkowych obiektów o ID: [1, 2, 3]" in errors[0]

    def test_validate_empty_mandatory_peaks(self):
        """Test walidacji gdy nie ma obowiązkowych szczytów."""
        rule = MandatoryObjectsRule(mandatory_peak_ids=set())

        ascents = [
            Ascent(peak_id=1, ascent_date=date(2023, 1, 1)),
            Ascent(peak_id=2, ascent_date=date(2023, 2, 1)),
        ]

        errors = rule.validate(ascents)
        assert errors == []

    def test_validate_duplicate_ascents(self):
        """Test walidacji z duplikatami wejść na ten sam szczyt."""
        rule = MandatoryObjectsRule(mandatory_peak_ids={1, 2})

        ascents = [
            Ascent(peak_id=1, ascent_date=date(2023, 1, 1)),
            Ascent(peak_id=1, ascent_date=date(2023, 2, 1)),  # duplikat
            Ascent(peak_id=2, ascent_date=date(2023, 3, 1)),
        ]

        errors = rule.validate(ascents)
        assert errors == []


class TestBadgeRule:
    """Testy klasy bazowej BadgeRule."""

    def test_badge_rule_is_abstract(self):
        """Test że BadgeRule jest klasą abstrakcyjną."""
        with pytest.raises(TypeError):
            BadgeRule()


def test_requires_club_join_date_rule() -> None:
    rule = RequiresClubJoinDateRule(club_join_date=date(2020, 1, 1))
    valid_ascent = Ascent(peak_id=1, ascent_date=date(2020, 1, 2))
    invalid_ascent = Ascent(peak_id=1, ascent_date=date(2019, 12, 31))

    assert not rule.validate([valid_ascent])
    assert len(rule.validate([invalid_ascent])) == 1


def test_min_age_rule() -> None:
    rule = MinAgeRule(min_age=10, birth_date=date(2010, 1, 1))
    valid_ascent = Ascent(peak_id=1, ascent_date=date(2021, 1, 1))  # 11 lat
    invalid_ascent = Ascent(peak_id=1, ascent_date=date(2019, 1, 1))  # 9 lat

    assert not rule.validate([valid_ascent])
    assert len(rule.validate([invalid_ascent])) == 1


def test_start_date_rule() -> None:
    rule = StartDateRule(start_date=date(2000, 1, 1))
    valid_ascent = Ascent(peak_id=1, ascent_date=date(2001, 1, 1))
    invalid_ascent = Ascent(peak_id=1, ascent_date=date(1999, 1, 1))

    assert not rule.validate([valid_ascent])
    assert len(rule.validate([invalid_ascent])) == 1


def test_mandatory_objects_rule() -> None:
    rule = MandatoryObjectsRule(mandatory_peak_ids=frozenset([1, 2]))
    valid_ascents = [
        Ascent(peak_id=1, ascent_date=date.today()),
        Ascent(peak_id=2, ascent_date=date.today()),
        Ascent(peak_id=3, ascent_date=date.today()),
    ]
    invalid_ascents = [
        Ascent(peak_id=1, ascent_date=date.today()),
        Ascent(peak_id=3, ascent_date=date.today()),
    ]

    assert not rule.validate(valid_ascents)
    assert len(rule.validate(invalid_ascents)) == 1


def test_grouped_alternatives_rule() -> None:
    rule = GroupedAlternativesRule(groups=(frozenset([1, 2]), frozenset([3, 4])), min_groups_required=2)
    valid_ascents = [Ascent(peak_id=1, ascent_date=date.today()), Ascent(peak_id=3, ascent_date=date.today())]
    invalid_ascents = [
        Ascent(peak_id=1, ascent_date=date.today()),
        Ascent(peak_id=2, ascent_date=date.today()),
    ]  # Oba wejścia z tej samej grupy!

    assert not rule.validate(valid_ascents)
    assert len(rule.validate(invalid_ascents)) == 1
