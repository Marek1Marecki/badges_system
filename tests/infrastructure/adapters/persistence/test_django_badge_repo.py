"""Testy dla DjangoBadgeRepo - budowniczych reguł."""

from datetime import date

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
    TimeLimitRule,
)
from infrastructure.adapters.persistence.django_badge_repo import (
    _build_club_join_rule,
    _build_date_window_rule,
    _build_grouped_alternatives_rule,
    _build_mandatory_objects_rule,
    _build_max_age_rule,
    _build_min_age_rule,
    _build_multi_pool_rule,
    _build_prerequisite_badge_rule,
    _build_region_count_rule,
    _build_start_date_rule,
    _build_time_limit_rule,
)


class TestTimeLimitRuleBuilder:
    def test_builds_time_limit_rule(self):
        """Buduje regułę limitu czasu."""
        data = {"limit_in_years": 5}
        rule = _build_time_limit_rule(data)

        assert isinstance(rule, TimeLimitRule)
        assert rule.limit_in_years == 5

    def test_raises_error_when_limit_missing(self):
        """Rzuca błąd gdy brakuje parametru limit_in_years."""
        data = {}
        with pytest.raises(ValueError, match="limit_in_years"):
            _build_time_limit_rule(data)


class TestClubJoinRuleBuilder:
    def test_builds_club_join_rule(self):
        """Buduje regułę wymogu dołączenia do klubu."""
        rule = _build_club_join_rule({})

        assert isinstance(rule, RequiresClubJoinDateRule)


class TestMinAgeRuleBuilder:
    def test_builds_min_age_rule(self):
        """Buduje regułę minimalnego wieku."""
        data = {"min_age": 18}
        rule = _build_min_age_rule(data)

        assert isinstance(rule, MinAgeRule)
        assert rule.min_age == 18

    def test_raises_error_when_age_missing(self):
        """Rzuca błąd gdy brakuje parametru min_age."""
        data = {}
        with pytest.raises(ValueError, match="min_age"):
            _build_min_age_rule(data)


class TestMaxAgeRuleBuilder:
    def test_builds_max_age_rule(self):
        """Buduje regułę maksymalnego wieku."""
        data = {"max_age": 65}
        rule = _build_max_age_rule(data)

        assert isinstance(rule, MaxAgeRule)
        assert rule.max_age == 65

    def test_raises_error_when_age_missing(self):
        """Rzuca błąd gdy brakuje parametru max_age."""
        data = {}
        with pytest.raises(ValueError, match="max_age"):
            _build_max_age_rule(data)


class TestStartDateRuleBuilder:
    def test_builds_start_date_rule(self):
        """Buduje regułę daty rozpoczęcia."""
        data = {"start_date": "2023-01-01"}
        rule = _build_start_date_rule(data)

        assert isinstance(rule, StartDateRule)
        assert rule.start_date == date(2023, 1, 1)

    def test_raises_error_when_date_missing(self):
        """Rzuca błąd gdy brakuje parametru start_date."""
        data = {}
        with pytest.raises(ValueError, match="start_date"):
            _build_start_date_rule(data)

    def test_raises_error_when_date_invalid(self):
        """Rzuca błąd gdy format daty jest nieprawidłowy."""
        data = {"start_date": "invalid-date"}
        with pytest.raises(ValueError, match="format daty"):
            _build_start_date_rule(data)


class TestDateWindowRuleBuilder:
    def test_builds_date_window_rule(self):
        """Buduje regułę okna czasowego."""
        data = {"start_date": "2023-01-01", "end_date": "2023-12-31"}
        rule = _build_date_window_rule(data)

        assert isinstance(rule, DateWindowRule)
        assert rule.start_date == date(2023, 1, 1)
        assert rule.end_date == date(2023, 12, 31)

    def test_raises_error_when_dates_missing(self):
        """Rzuca błąd gdy brakuje parametrów dat."""
        data = {}
        with pytest.raises(ValueError, match="start_date.*end_date"):
            _build_date_window_rule(data)


class TestMandatoryObjectsRuleBuilder:
    def test_builds_mandatory_objects_rule(self):
        """Buduje regułę obowiązkowych obiektów."""
        data = {"mandatory_peak_ids": [1, 2, 3]}
        rule = _build_mandatory_objects_rule(data)

        assert isinstance(rule, MandatoryObjectsRule)
        assert rule.mandatory_peak_ids == frozenset([1, 2, 3])

    def test_raises_error_when_ids_missing(self):
        """Rzuca błąd gdy brakuje listy mandatory_peak_ids."""
        data = {}
        with pytest.raises(ValueError, match="mandatory_peak_ids"):
            _build_mandatory_objects_rule(data)


class TestGroupedAlternativesRuleBuilder:
    def test_builds_grouped_alternatives_rule(self):
        """Buduje regułę pogrupowanych alternatyw."""
        data = {
            "min_groups_required": 2,
            "groups": [
                {"peak_ids": [1, 2]},
                {"peak_ids": [3, 4]},
                {"peak_ids": [5, 6]},
            ],
        }
        rule = _build_grouped_alternatives_rule(data)

        assert isinstance(rule, GroupedAlternativesRule)
        assert rule.min_groups_required == 2
        assert len(rule.groups) == 3

    def test_raises_error_when_params_missing(self):
        """Rzuca błąd gdy brakuje wymaganych parametrów."""
        data = {}
        with pytest.raises(ValueError, match="min_groups_required.*groups"):
            _build_grouped_alternatives_rule(data)


class TestMultiPoolRuleBuilder:
    def test_builds_multi_pool_rule(self):
        """Buduje regułę wielokrotnych pul."""
        data = {
            "pools": [
                {"required_count": 2, "peak_ids": "1,2,3"},
                {"required_count": 1, "peak_ids": "4,5"},
            ]
        }
        rule = _build_multi_pool_rule(data)

        assert isinstance(rule, MultiPoolRequirementRule)
        assert len(rule.pools) == 2
        assert rule.pools[0].required_count == 2
        assert rule.pools[0].peak_ids == frozenset([1, 2, 3])

    def test_raises_error_when_pools_missing(self):
        """Rzuca błąd gdy brakuje listy pools."""
        data = {}
        with pytest.raises(ValueError, match="pools"):
            _build_multi_pool_rule(data)

    def test_handles_whitespace_in_peak_ids(self):
        """Obsługuje białe znaki w liście ID."""
        data = {"pools": [{"required_count": 1, "peak_ids": " 1 , 2 , 3 "}]}
        rule = _build_multi_pool_rule(data)

        assert rule.pools[0].peak_ids == frozenset([1, 2, 3])


class TestPrerequisiteBadgeRuleBuilder:
    def test_builds_prerequisite_badge_rule(self):
        """Buduje regułę wymogu wstępnego odznaki."""
        data = {"required_badge_code": "KGP"}
        rule = _build_prerequisite_badge_rule(data)

        assert isinstance(rule, PrerequisiteBadgeRule)
        assert rule.required_badge_code == "KGP"

    def test_strips_whitespace_from_code(self):
        """Usuwa białe znaki z kodu odznaki."""
        data = {"required_badge_code": "  KGP  "}
        rule = _build_prerequisite_badge_rule(data)

        assert rule.required_badge_code == "KGP"

    def test_raises_error_when_code_missing(self):
        """Rzuca błąd gdy brakuje parametru required_badge_code."""
        data = {}
        with pytest.raises(ValueError, match="required_badge_code"):
            _build_prerequisite_badge_rule(data)


class TestRegionCountRuleBuilder:
    def test_builds_region_count_rule(self):
        """Buduje regułę liczby obiektów w regionie."""
        data = {"region_id": 5, "required_count": 10}
        rule = _build_region_count_rule(data)

        assert isinstance(rule, RegionCountRule)
        assert rule.region_id == 5
        assert rule.required_count == 10

    def test_raises_error_when_params_missing(self):
        """Rzuca błąd gdy brakuje wymaganych parametrów."""
        data = {}
        with pytest.raises(ValueError, match="region_id.*required_count"):
            _build_region_count_rule(data)
