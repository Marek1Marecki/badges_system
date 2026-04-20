"""Testy dla reguł biznesowych zdobywania odznak."""

from datetime import date

import pytest

from domain.rules.badge_rules import (
    ActivityRule,
    BadgeRule,
    MandatoryObjectsRule,
    MinAgeRule,
    RequiresClubJoinDateRule,
    StartDateRule,
    TimeLimitRule,
)
from domain.value_objects.ascent import ActivityType, Ascent


class TestActivityRule:
    """Testy klasy ActivityRule."""

    def test_validate_all_valid_activities(self):
        """Test walidacji z wszystkimi dozwolonymi aktywnościami."""
        rule = ActivityRule(allowed_activities={ActivityType.HIKING, ActivityType.CYCLING})
        
        ascents = [
            Ascent(peak_id=1, ascent_date=date(2023, 1, 1), activity=ActivityType.HIKING),
            Ascent(peak_id=2, ascent_date=date(2023, 6, 1), activity=ActivityType.CYCLING),
        ]
        
        errors = rule.validate(ascents)
        assert errors == []

    def test_validate_with_invalid_activity(self):
        """Test walidacji z niedozwoloną aktywnością."""
        rule = ActivityRule(allowed_activities={ActivityType.HIKING})
        
        ascents = [
            Ascent(peak_id=1, ascent_date=date(2023, 1, 1), activity=ActivityType.HIKING),
            Ascent(peak_id=2, ascent_date=date(2023, 6, 1), activity=ActivityType.CYCLING),
        ]
        
        errors = rule.validate(ascents)
        assert len(errors) == 1
        assert "Aktywność CYCLING jest niedozwolona" in errors[0]

    def test_validate_multiple_invalid_activities(self):
        """Test walidacji z wieloma niedozwolonymi aktywnościami."""
        rule = ActivityRule(allowed_activities={ActivityType.HIKING})
        
        ascents = [
            Ascent(peak_id=1, ascent_date=date(2023, 1, 1), activity=ActivityType.CYCLING),
            Ascent(peak_id=2, ascent_date=date(2023, 6, 1), activity=ActivityType.SKIING),
        ]
        
        errors = rule.validate(ascents)
        assert len(errors) == 2
        assert "Aktywność CYCLING jest niedozwolona" in errors[0]
        assert "Aktywność SKIING jest niedozwolona" in errors[1]

    def test_validate_empty_ascents_list(self):
        """Test walidacji z pustą listą wejść."""
        rule = ActivityRule(allowed_activities={ActivityType.HIKING})
        
        errors = rule.validate([])
        assert errors == []

    def test_validate_single_allowed_activity(self):
        """Test walidacji z pojedynczą dozwoloną aktywnością."""
        rule = ActivityRule(allowed_activities={ActivityType.SKIING})
        
        ascents = [Ascent(peak_id=1, ascent_date=date(2023, 1, 1), activity=ActivityType.SKIING)]
        
        errors = rule.validate(ascents)
        assert errors == []


class TestTimeLimitRule:
    """Testy klasy TimeLimitRule."""

    def test_validate_within_time_limit(self):
        """Test walidacji w ramach limitu czasowego."""
        rule = TimeLimitRule(limit_in_years=2)
        
        ascents = [
            Ascent(peak_id=1, ascent_date=date(2023, 1, 1), activity=ActivityType.HIKING),
            Ascent(peak_id=2, ascent_date=date(2024, 6, 1), activity=ActivityType.HIKING),
        ]
        
        errors = rule.validate(ascents)
        assert errors == []

    def test_validate_exactly_at_limit(self):
        """Test walidacji dokładnie na granicy limitu."""
        rule = TimeLimitRule(limit_in_years=1)
        
        ascents = [
            Ascent(peak_id=1, ascent_date=date(2023, 1, 1), activity=ActivityType.HIKING),
            Ascent(peak_id=2, ascent_date=date(2024, 1, 1), activity=ActivityType.HIKING),
        ]
        
        errors = rule.validate(ascents)
        assert errors == []

    def test_validate_exceeds_time_limit(self):
        """Test walidacji z przekroczeniem limitu czasowego."""
        rule = TimeLimitRule(limit_in_years=1)
        
        ascents = [
            Ascent(peak_id=1, ascent_date=date(2022, 1, 1), activity=ActivityType.HIKING),
            Ascent(peak_id=2, ascent_date=date(2023, 6, 1), activity=ActivityType.HIKING),
        ]
        
        errors = rule.validate(ascents)
        assert len(errors) == 1
        assert "Przekroczono limit 1 lat" in errors[0]
        assert "trwało 516 dni" in errors[0]

    def test_validate_empty_ascents_list(self):
        """Test walidacji z pustą listą wejść."""
        rule = TimeLimitRule(limit_in_years=1)
        
        errors = rule.validate([])
        assert errors == []

    def test_validate_single_ascent(self):
        """Test walidacji z pojedynczym wejściem."""
        rule = TimeLimitRule(limit_in_years=1)
        
        ascents = [Ascent(peak_id=1, ascent_date=date(2023, 1, 1), activity=ActivityType.HIKING)]
        
        errors = rule.validate(ascents)
        assert errors == []

    def test_validate_different_order(self):
        """Test walidacji z wejściami w innej kolejności."""
        rule = TimeLimitRule(limit_in_years=1)
        
        ascents = [
            Ascent(peak_id=2, ascent_date=date(2023, 6, 1), activity=ActivityType.HIKING),
            Ascent(peak_id=1, ascent_date=date(2023, 1, 1), activity=ActivityType.HIKING),
        ]
        
        errors = rule.validate(ascents)
        assert errors == []

    def test_validate_zero_year_limit(self):
        """Test walidacji z zerowym limitem lat."""
        rule = TimeLimitRule(limit_in_years=0)
        
        ascents = [
            Ascent(peak_id=1, ascent_date=date(2023, 1, 1), activity=ActivityType.HIKING),
            Ascent(peak_id=2, ascent_date=date(2023, 1, 1), activity=ActivityType.HIKING),
        ]
        
        errors = rule.validate(ascents)
        assert errors == []

    def test_validate_large_time_span(self):
        """Test walidacji z dużym zakresem czasowym."""
        rule = TimeLimitRule(limit_in_years=10)
        
        ascents = [
            Ascent(peak_id=1, ascent_date=date(2010, 1, 1), activity=ActivityType.HIKING),
            Ascent(peak_id=2, ascent_date=date(2019, 12, 30), activity=ActivityType.HIKING),
        ]
        
        errors = rule.validate(ascents)
        assert errors == []


class TestRequiresClubJoinDateRule:
    """Testy klasy RequiresClubJoinDateRule."""

    def test_validate_all_ascents_after_join_date(self):
        """Test walidacji z wszystkimi wejściami po dacie dołączenia do klubu."""
        rule = RequiresClubJoinDateRule()
        
        ascents = [
            Ascent(peak_id=1, ascent_date=date(2020, 6, 1), activity=ActivityType.HIKING),
            Ascent(peak_id=2, ascent_date=date(2021, 1, 15), activity=ActivityType.CYCLING),
        ]
        
        errors = rule.validate(ascents)
        assert errors == []

    def test_validate_ascents_before_join_date(self):
        """Test walidacji z wejściami przed datą dołączenia do klubu."""
        rule = RequiresClubJoinDateRule()
        
        ascents = [
            Ascent(peak_id=1, ascent_date=date(2019, 6, 1), activity=ActivityType.HIKING),
            Ascent(peak_id=2, ascent_date=date(2020, 6, 1), activity=ActivityType.CYCLING),
        ]
        
        errors = rule.validate(ascents)
        assert len(errors) == 1
        assert "Wejście na szczyt (ID: 1) odrzucone" in errors[0]
        assert "Data wejścia (2019-06-01) jest przed datą dołączenia do klubu (2020-01-01)" in errors[0]

    def test_validate_multiple_ascents_before_join_date(self):
        """Test walidacji z wieloma wejściami przed datą dołączenia."""
        rule = RequiresClubJoinDateRule()
        
        ascents = [
            Ascent(peak_id=1, ascent_date=date(2018, 5, 1), activity=ActivityType.HIKING),
            Ascent(peak_id=2, ascent_date=date(2019, 3, 15), activity=ActivityType.CYCLING),
            Ascent(peak_id=3, ascent_date=date(2020, 2, 1), activity=ActivityType.SKIING),
        ]
        
        errors = rule.validate(ascents)
        assert len(errors) == 2
        assert "Wejście na szczyt (ID: 1) odrzucone" in errors[0]
        assert "Wejście na szczyt (ID: 2) odrzucone" in errors[1]

    def test_validate_empty_ascents_list(self):
        """Test walidacji z pustą listą wejść."""
        rule = RequiresClubJoinDateRule()
        
        errors = rule.validate([])
        assert errors == []

    def test_validate_exactly_on_join_date(self):
        """Test walidacji z wejściem dokładnie w dacie dołączenia."""
        rule = RequiresClubJoinDateRule()
        
        ascents = [Ascent(peak_id=1, ascent_date=date(2020, 1, 1), activity=ActivityType.HIKING)]
        
        errors = rule.validate(ascents)
        assert errors == []


class TestMinAgeRule:
    """Testy klasy MinAgeRule."""

    def test_validate_all_ascents_meet_min_age(self):
        """Test walidacji z wszystkimi wejściami spełniającymi minimalny wiek."""
        rule = MinAgeRule(min_age=8)
        
        ascents = [
            Ascent(peak_id=1, ascent_date=date(2023, 6, 1), activity=ActivityType.HIKING),  # 8 lat
            Ascent(peak_id=2, ascent_date=date(2024, 1, 15), activity=ActivityType.CYCLING),  # 9 lat
        ]
        
        errors = rule.validate(ascents)
        assert errors == []

    def test_validate_ascents_below_min_age(self):
        """Test walidacji z wejściami poniżej minimalnego wieku."""
        rule = MinAgeRule(min_age=10)
        
        ascents = [
            Ascent(peak_id=1, ascent_date=date(2022, 6, 1), activity=ActivityType.HIKING),  # 7 lat
            Ascent(peak_id=2, ascent_date=date(2024, 6, 1), activity=ActivityType.CYCLING),  # 9 lat
        ]
        
        errors = rule.validate(ascents)
        assert len(errors) == 2
        assert "Wejście na szczyt (ID: 1) odrzucone" in errors[0]
        assert "Wiek w dniu wejścia (7 lat) był mniejszy niż wymagane 10 lat" in errors[0]
        assert "Wejście na szczyt (ID: 2) odrzucone" in errors[1]
        assert "Wiek w dniu wejścia (9 lat) był mniejszy niż wymagane 10 lat" in errors[1]

    def test_validate_birthday_edge_case(self):
        """Test walidacji przypadków granicznych związanych z urodzinami."""
        rule = MinAgeRule(min_age=8)
        
        # Dzień przed 8. urodzinami
        ascents_before = [Ascent(peak_id=1, ascent_date=date(2022, 12, 31), activity=ActivityType.HIKING)]
        errors = rule.validate(ascents_before)
        assert len(errors) == 1
        assert "Wiek w dniu wejścia (7 lat) był mniejszy niż wymagane 8 lat" in errors[0]
        
        # W dniu 8. urodzin
        ascents_on = [Ascent(peak_id=2, ascent_date=date(2023, 1, 1), activity=ActivityType.HIKING)]
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
        
        ascents = [Ascent(peak_id=1, ascent_date=date(2018, 6, 1), activity=ActivityType.HIKING)]  # 3 lat
        
        errors = rule.validate(ascents)
        assert errors == []


class TestStartDateRule:
    """Testy klasy StartDateRule."""

    def test_validate_all_ascents_after_start_date(self):
        """Test walidacji z wszystkimi wejściami po dacie startowej."""
        rule = StartDateRule(start_date=date(2020, 6, 1))
        
        ascents = [
            Ascent(peak_id=1, ascent_date=date(2020, 6, 1), activity=ActivityType.HIKING),
            Ascent(peak_id=2, ascent_date=date(2021, 1, 15), activity=ActivityType.CYCLING),
        ]
        
        errors = rule.validate(ascents)
        assert errors == []

    def test_validate_ascents_before_start_date(self):
        """Test walidacji z wejściami przed datą startową."""
        rule = StartDateRule(start_date=date(2020, 6, 1))
        
        ascents = [
            Ascent(peak_id=1, ascent_date=date(2019, 6, 1), activity=ActivityType.HIKING),
            Ascent(peak_id=2, ascent_date=date(2020, 6, 1), activity=ActivityType.CYCLING),
        ]
        
        errors = rule.validate(ascents)
        assert len(errors) == 1
        assert "Wejście na szczyt (ID: 1) odrzucone" in errors[0]
        assert "Data wejścia (2019-06-01) jest przed datą wejścia w życie regulaminu odznaki (2020-06-01)" in errors[0]

    def test_validate_multiple_ascents_before_start_date(self):
        """Test walidacji z wieloma wejściami przed datą startową."""
        rule = StartDateRule(start_date=date(2020, 6, 1))
        
        ascents = [
            Ascent(peak_id=1, ascent_date=date(2018, 5, 1), activity=ActivityType.HIKING),
            Ascent(peak_id=2, ascent_date=date(2019, 3, 15), activity=ActivityType.CYCLING),
            Ascent(peak_id=3, ascent_date=date(2020, 6, 1), activity=ActivityType.SKIING),
        ]
        
        errors = rule.validate(ascents)
        assert len(errors) == 2
        assert "Wejście na szczyt (ID: 1) odrzucone" in errors[0]
        assert "Wejście na szczyt (ID: 2) odrzucone" in errors[1]

    def test_validate_empty_ascents_list(self):
        """Test walidacji z pustą listą wejść."""
        rule = StartDateRule(start_date=date(2020, 6, 1))
        
        errors = rule.validate([])
        assert errors == []

    def test_validate_exactly_on_start_date(self):
        """Test walidacji z wejściem dokładnie w dacie startowej."""
        rule = StartDateRule(start_date=date(2020, 6, 1))
        
        ascents = [Ascent(peak_id=1, ascent_date=date(2020, 6, 1), activity=ActivityType.HIKING)]
        
        errors = rule.validate(ascents)
        assert errors == []


class TestMandatoryObjectsRule:
    """Testy klasy MandatoryObjectsRule."""

    def test_validate_all_mandatory_peaks_climbed(self):
        """Test walidacji gdy wszystkie obowiązkowe szczyty zostały zdobyte."""
        rule = MandatoryObjectsRule(mandatory_peak_ids={1, 2, 3})
        
        ascents = [
            Ascent(peak_id=1, ascent_date=date(2023, 1, 1), activity=ActivityType.HIKING),
            Ascent(peak_id=2, ascent_date=date(2023, 2, 1), activity=ActivityType.HIKING),
            Ascent(peak_id=3, ascent_date=date(2023, 3, 1), activity=ActivityType.HIKING),
            Ascent(peak_id=4, ascent_date=date(2023, 4, 1), activity=ActivityType.HIKING),  # dodatkowy
        ]
        
        errors = rule.validate(ascents)
        assert errors == []

    def test_validate_missing_mandatory_peaks(self):
        """Test walidacji gdy brakuje obowiązkowych szczytów."""
        rule = MandatoryObjectsRule(mandatory_peak_ids={1, 2, 3, 4})
        
        ascents = [
            Ascent(peak_id=1, ascent_date=date(2023, 1, 1), activity=ActivityType.HIKING),
            Ascent(peak_id=3, ascent_date=date(2023, 3, 1), activity=ActivityType.HIKING),
        ]
        
        errors = rule.validate(ascents)
        assert len(errors) == 1
        assert "Brakuje obowiązkowych obiektów. Musisz zdobyć obiekty o ID: [2, 4]" in errors[0]

    def test_validate_no_mandatory_peaks_climbed(self):
        """Test walidacji gdy żaden obowiązkowy szczyt nie został zdobyty."""
        rule = MandatoryObjectsRule(mandatory_peak_ids={1, 2, 3})
        
        ascents = [
            Ascent(peak_id=4, ascent_date=date(2023, 1, 1), activity=ActivityType.HIKING),
            Ascent(peak_id=5, ascent_date=date(2023, 2, 1), activity=ActivityType.HIKING),
        ]
        
        errors = rule.validate(ascents)
        assert len(errors) == 1
        assert "Brakuje obowiązkowych obiektów. Musisz zdobyć obiekty o ID: [1, 2, 3]" in errors[0]

    def test_validate_empty_ascents_list(self):
        """Test walidacji z pustą listą wejść."""
        rule = MandatoryObjectsRule(mandatory_peak_ids={1, 2, 3})
        
        errors = rule.validate([])
        assert len(errors) == 1
        assert "Brakuje obowiązkowych obiektów. Musisz zdobyć obiekty o ID: [1, 2, 3]" in errors[0]

    def test_validate_empty_mandatory_peaks(self):
        """Test walidacji gdy nie ma obowiązkowych szczytów."""
        rule = MandatoryObjectsRule(mandatory_peak_ids=set())
        
        ascents = [
            Ascent(peak_id=1, ascent_date=date(2023, 1, 1), activity=ActivityType.HIKING),
            Ascent(peak_id=2, ascent_date=date(2023, 2, 1), activity=ActivityType.HIKING),
        ]
        
        errors = rule.validate(ascents)
        assert errors == []

    def test_validate_duplicate_ascents(self):
        """Test walidacji z duplikatami wejść na ten sam szczyt."""
        rule = MandatoryObjectsRule(mandatory_peak_ids={1, 2})
        
        ascents = [
            Ascent(peak_id=1, ascent_date=date(2023, 1, 1), activity=ActivityType.HIKING),
            Ascent(peak_id=1, ascent_date=date(2023, 2, 1), activity=ActivityType.HIKING),  # duplikat
            Ascent(peak_id=2, ascent_date=date(2023, 3, 1), activity=ActivityType.HIKING),
        ]
        
        errors = rule.validate(ascents)
        assert errors == []


class TestBadgeRule:
    """Testy klasy bazowej BadgeRule."""

    def test_badge_rule_is_abstract(self):
        """Test że BadgeRule jest klasą abstrakcyjną."""
        with pytest.raises(TypeError):
            BadgeRule()
