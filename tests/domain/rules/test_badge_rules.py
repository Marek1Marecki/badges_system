"""Testy dla reguł biznesowych zdobywania odznak."""

from datetime import date

import pytest

from domain.rules.badge_rules import ActivityRule, BadgeRule, TimeLimitRule
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


class TestBadgeRule:
    """Testy klasy bazowej BadgeRule."""

    def test_badge_rule_is_abstract(self):
        """Test że BadgeRule jest klasą abstrakcyjną."""
        with pytest.raises(TypeError):
            BadgeRule()
