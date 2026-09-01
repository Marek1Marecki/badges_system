"""Testy czystej fabryki reguł (AUDYT-036).

Testy nie wymagają Django ORM ani bazy danych — testują wyłącznie logikę
parsowania JSON/JSONB → obiektów domenowych w `infrastructure/factories/`.
"""

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
from infrastructure.factories.badge_rule_factory import build_rule_from_dict


class TestBuildRuleFromDict:
    """Testy dyspatche'owania `build_rule_from_dict` na bazie `RULE_BUILDERS`."""

    def test_dispatches_to_correct_builder(self):
        rule = build_rule_from_dict({"type": "TimeLimitRule", "limit_in_years": 5})

        assert isinstance(rule, TimeLimitRule)
        assert rule.limit_in_years == 5


class TestTimeLimitRuleBuilder:
    """Testy budowniczego TimeLimitRule."""

    def test_builds_time_limit_rule(self):
        """Buduje regułę limitu czasu."""
        rule = build_rule_from_dict({"type": "TimeLimitRule", "limit_in_years": 5})

        assert isinstance(rule, TimeLimitRule)
        assert rule.limit_in_years == 5

    def test_raises_error_when_limit_missing(self):
        """Rzuca błąd gdy brakuje parametru limit_in_years."""
        with pytest.raises(ValueError, match="limit_in_years"):
            build_rule_from_dict({"type": "TimeLimitRule"})


class TestClubJoinRuleBuilder:
    """Testy budowniczego RequiresClubJoinDateRule."""

    def test_builds_club_join_rule(self):
        """Buduje regułę wymogu dołączenia do klubu."""
        rule = build_rule_from_dict({"type": "RequiresClubJoinDateRule"})

        assert isinstance(rule, RequiresClubJoinDateRule)


class TestMinAgeRuleBuilder:
    """Testy budowniczego MinAgeRule."""

    def test_builds_min_age_rule(self):
        """Buduje regułę minimalnego wieku."""
        rule = build_rule_from_dict({"type": "MinAgeRule", "min_age": 18})

        assert isinstance(rule, MinAgeRule)
        assert rule.min_age == 18

    def test_raises_error_when_age_missing(self):
        """Rzuca błąd gdy brakuje parametru min_age."""
        with pytest.raises(ValueError, match="min_age"):
            build_rule_from_dict({"type": "MinAgeRule"})


class TestMaxAgeRuleBuilder:
    """Testy budowniczego MaxAgeRule."""

    def test_builds_max_age_rule(self):
        """Buduje regułę maksymalnego wieku."""
        rule = build_rule_from_dict({"type": "MaxAgeRule", "max_age": 65})

        assert isinstance(rule, MaxAgeRule)
        assert rule.max_age == 65

    def test_raises_error_when_age_missing(self):
        """Rzuca błąd gdy brakuje parametru max_age."""
        with pytest.raises(ValueError, match="max_age"):
            build_rule_from_dict({"type": "MaxAgeRule"})


class TestStartDateRuleBuilder:
    """Testy budowniczego StartDateRule."""

    def test_builds_start_date_rule(self):
        """Buduje regułę daty rozpoczęcia."""
        rule = build_rule_from_dict({"type": "StartDateRule", "start_date": "2023-01-01"})

        assert isinstance(rule, StartDateRule)
        assert rule.start_date == date(2023, 1, 1)

    def test_raises_error_when_date_missing(self):
        """Rzuca błąd gdy brakuje parametru start_date."""
        with pytest.raises(ValueError, match="start_date"):
            build_rule_from_dict({"type": "StartDateRule"})

    def test_raises_error_when_date_invalid(self):
        """Rzuca błąd gdy format daty jest nieprawidłowy."""
        with pytest.raises(ValueError, match="format daty"):
            build_rule_from_dict({"type": "StartDateRule", "start_date": "invalid-date"})


class TestDateWindowRuleBuilder:
    """Testy budowniczego DateWindowRule."""

    def test_builds_date_window_rule(self):
        """Buduje regułę okna czasowego."""
        rule = build_rule_from_dict({"type": "DateWindowRule", "start_date": "2023-01-01", "end_date": "2023-12-31"})

        assert isinstance(rule, DateWindowRule)
        assert rule.start_date == date(2023, 1, 1)
        assert rule.end_date == date(2023, 12, 31)

    def test_raises_error_when_dates_missing(self):
        """Rzuca błąd gdy brakuje parametrów dat."""
        with pytest.raises(ValueError, match="start_date.*end_date"):
            build_rule_from_dict({"type": "DateWindowRule"})


class TestMandatoryObjectsRuleBuilder:
    """Testy budowniczego MandatoryObjectsRule."""

    def test_builds_mandatory_objects_rule(self):
        """Buduje regułę obowiązkowych obiektów."""
        rule = build_rule_from_dict({"type": "MandatoryObjectsRule", "mandatory_peak_ids": [1, 2, 3]})

        assert isinstance(rule, MandatoryObjectsRule)
        assert rule.mandatory_peak_ids == frozenset([1, 2, 3])

    def test_raises_error_when_ids_missing(self):
        """Rzuca błąd gdy brakuje listy mandatory_peak_ids."""
        with pytest.raises(ValueError, match="mandatory_peak_ids"):
            build_rule_from_dict({"type": "MandatoryObjectsRule"})


class TestGroupedAlternativesRuleBuilder:
    """Testy budowniczego GroupedAlternativesRule."""

    def test_builds_grouped_alternatives_rule(self):
        """Buduje regułę pogrupowanych alternatyw."""
        rule = build_rule_from_dict(
            {
                "type": "GroupedAlternativesRule",
                "min_groups_required": 2,
                "groups": [
                    {"peak_ids": [1, 2]},
                    {"peak_ids": [3, 4]},
                    {"peak_ids": [5, 6]},
                ],
            }
        )

        assert isinstance(rule, GroupedAlternativesRule)
        assert rule.min_groups_required == 2
        assert len(rule.groups) == 3

    def test_raises_error_when_params_missing(self):
        """Rzuca błąd gdy brakuje wymaganych parametrów."""
        with pytest.raises(ValueError, match="min_groups_required.*groups"):
            build_rule_from_dict({"type": "GroupedAlternativesRule"})


class TestMultiPoolRuleBuilder:
    """Testy budowniczego MultiPoolRequirementRule."""

    def test_builds_multi_pool_rule(self):
        """Buduje regułę wielokrotnych pul."""
        rule = build_rule_from_dict(
            {
                "type": "MultiPoolRequirementRule",
                "pools": [
                    {"required_count": 2, "peak_ids": "1,2,3"},
                    {"required_count": 1, "peak_ids": "4,5"},
                ],
            }
        )

        assert isinstance(rule, MultiPoolRequirementRule)
        assert len(rule.pools) == 2
        assert rule.pools[0].required_count == 2
        assert rule.pools[0].peak_ids == frozenset([1, 2, 3])

    def test_raises_error_when_pools_missing(self):
        """Rzuca błąd gdy brakuje listy pools."""
        with pytest.raises(ValueError, match="pools"):
            build_rule_from_dict({"type": "MultiPoolRequirementRule"})

    def test_handles_whitespace_in_peak_ids(self):
        """Obsługuje białe znaki w liście ID."""
        rule = build_rule_from_dict(
            {
                "type": "MultiPoolRequirementRule",
                "pools": [{"required_count": 1, "peak_ids": " 1 , 2 , 3 "}],
            }
        )

        assert rule.pools[0].peak_ids == frozenset([1, 2, 3])


class TestPrerequisiteBadgeRuleBuilder:
    """Testy budowniczego PrerequisiteBadgeRule."""

    def test_builds_prerequisite_badge_rule(self):
        """Buduje regułę wymogu wstępnego odznaki."""
        rule = build_rule_from_dict({"type": "PrerequisiteBadgeRule", "required_badge_code": "KGP"})

        assert isinstance(rule, PrerequisiteBadgeRule)
        assert rule.required_badge_code == "KGP"

    def test_strips_whitespace_from_code(self):
        """Usuwa białe znaki z kodu odznaki."""
        rule = build_rule_from_dict({"type": "PrerequisiteBadgeRule", "required_badge_code": "  KGP  "})

        assert rule.required_badge_code == "KGP"

    def test_raises_error_when_code_missing(self):
        """Rzuca błąd gdy brakuje parametru required_badge_code."""
        with pytest.raises(ValueError, match="required_badge_code"):
            build_rule_from_dict({"type": "PrerequisiteBadgeRule"})


class TestRegionCountRuleBuilder:
    """Testy budowniczego RegionCountRule."""

    def test_builds_region_count_rule(self):
        """Buduje regułę liczby obiektów w regionie."""
        rule = build_rule_from_dict({"type": "RegionCountRule", "region_id": 5, "required_count": 10})

        assert isinstance(rule, RegionCountRule)
        assert rule.region_id == 5
        assert rule.required_count == 10

    def test_raises_error_when_params_missing(self):
        """Rzuca błąd gdy brakuje wymaganych parametrów."""
        with pytest.raises(ValueError, match="region_id.*required_count"):
            build_rule_from_dict({"type": "RegionCountRule"})


class TestRuleBuilderUnitFailFast:
    """Jednostkowe testy Fail-Fast dla poszczególnych budowniczych reguł."""

    def test_time_limit_rule_raises_on_none_limit(self):
        """Rzuca błąd gdy brak limit_in_years."""
        with pytest.raises(ValueError, match="limit_in_years"):
            build_rule_from_dict({"type": "TimeLimitRule"})

    def test_min_age_rule_raises_on_none_age(self):
        """Rzuca błąd gdy brak min_age."""
        with pytest.raises(ValueError, match="min_age"):
            build_rule_from_dict({"type": "MinAgeRule"})

    def test_max_age_rule_raises_on_none_age(self):
        """Rzuca błąd gdy brak max_age."""
        with pytest.raises(ValueError, match="max_age"):
            build_rule_from_dict({"type": "MaxAgeRule"})

    def test_start_date_rule_raises_on_none_date(self):
        """Rzuca błąd gdy brak start_date."""
        with pytest.raises(ValueError, match="start_date"):
            build_rule_from_dict({"type": "StartDateRule"})

    def test_date_window_rule_raises_on_missing_dates(self):
        """Rzuca błąd gdy brak dat okna."""
        with pytest.raises(ValueError, match="start_date.*end_date"):
            build_rule_from_dict({"type": "DateWindowRule"})

    def test_mandatory_objects_rule_raises_on_missing_ids(self):
        """Rzuca błąd gdy brak mandatory_peak_ids."""
        with pytest.raises(ValueError, match="mandatory_peak_ids"):
            build_rule_from_dict({"type": "MandatoryObjectsRule"})

    def test_grouped_alternatives_rule_raises_on_missing_params(self):
        """Rzuca błąd gdy brak parametrów alternatyw."""
        with pytest.raises(ValueError, match="min_groups_required.*groups"):
            build_rule_from_dict({"type": "GroupedAlternativesRule"})

    def test_multi_pool_rule_raises_on_missing_pools(self):
        """Rzuca błąd gdy brak pools."""
        with pytest.raises(ValueError, match="pools"):
            build_rule_from_dict({"type": "MultiPoolRequirementRule"})

    def test_prerequisite_badge_rule_raises_on_missing_code(self):
        """Rzuca błąd gdy brak required_badge_code."""
        with pytest.raises(ValueError, match="required_badge_code"):
            build_rule_from_dict({"type": "PrerequisiteBadgeRule"})

    def test_region_count_rule_raises_on_missing_params(self):
        """Rzuca błąd gdy brak region_id lub required_count."""
        with pytest.raises(ValueError, match="region_id.*required_count"):
            build_rule_from_dict({"type": "RegionCountRule"})

    def test_unknown_rule_type_raises(self):
        """Rzuca błąd dla nieznanego typu reguły."""
        with pytest.raises(ValueError, match="Nieznany typ reguły 'GhostRule'"):
            build_rule_from_dict({"type": "GhostRule"})

    def test_rule_without_type_field_raises(self):
        """Rzuca błąd gdy reguła nie ma pola 'type'."""
        with pytest.raises(ValueError, match="Reguła bez pola 'type'"):
            build_rule_from_dict({"min_age": 18})
