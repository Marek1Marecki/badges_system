"""Testy dla badge_rules_schema."""

from apps.badges.rules_schema import RULES_SCHEMA


class TestBadgeRulesSchema:
    """Testy schematu RULES_SCHEMA."""

    def test_rules_schema_structure(self):
        """Test struktury RULES_SCHEMA."""
        assert RULES_SCHEMA["type"] == "list"
        assert "title" in RULES_SCHEMA
        assert "items" in RULES_SCHEMA

    def test_rules_schema_has_oneof(self):
        """Test że RULES_SCHEMA ma oneOf."""
        items = RULES_SCHEMA["items"]
        assert "oneOf" in items
        assert isinstance(items["oneOf"], list)

    def test_rules_schema_contains_time_limit_rule(self):
        """Test że schemat zawiera TimeLimitRule."""
        items = RULES_SCHEMA["items"]["oneOf"]
        time_limit_rule = next((r for r in items if "Limit Czasowy" in r.get("title", "")), None)
        assert time_limit_rule is not None
        assert time_limit_rule["type"] == "dict"
        assert "keys" in time_limit_rule
        assert "limit_in_years" in time_limit_rule["keys"]

    def test_rules_schema_contains_min_age_rule(self):
        """Test że schemat zawiera MinAgeRule."""
        items = RULES_SCHEMA["items"]["oneOf"]
        min_age_rule = next((r for r in items if "Minimalny Wiek" in r.get("title", "")), None)
        assert min_age_rule is not None
        assert "min_age" in min_age_rule["keys"]

    def test_rules_schema_contains_max_age_rule(self):
        """Test że schemat zawiera MaxAgeRule."""
        items = RULES_SCHEMA["items"]["oneOf"]
        max_age_rule = next((r for r in items if "Maksymalny Wiek" in r.get("title", "")), None)
        assert max_age_rule is not None
        assert "max_age" in max_age_rule["keys"]

    def test_rules_schema_contains_start_date_rule(self):
        """Test że schemat zawiera StartDateRule."""
        items = RULES_SCHEMA["items"]["oneOf"]
        start_date_rule = next((r for r in items if "Szczyty zaliczane od daty" in r.get("title", "")), None)
        assert start_date_rule is not None
        assert "start_date" in start_date_rule["keys"]

    def test_rules_schema_contains_date_window_rule(self):
        """Test że schemat zawiera DateWindowRule."""
        items = RULES_SCHEMA["items"]["oneOf"]
        date_window_rule = next((r for r in items if "Zamknięte Okno Czasowe" in r.get("title", "")), None)
        assert date_window_rule is not None
        assert "start_date" in date_window_rule["keys"]
        assert "end_date" in date_window_rule["keys"]

    def test_rules_schema_contains_mandatory_objects_rule(self):
        """Test że schemat zawiera MandatoryObjectsRule."""
        items = RULES_SCHEMA["items"]["oneOf"]
        mandatory_rule = next((r for r in items if "Obowiązkowe konkretne obiekty" in r.get("title", "")), None)
        assert mandatory_rule is not None
        assert "mandatory_peak_ids" in mandatory_rule["keys"]

    def test_rules_schema_contains_grouped_alternatives_rule(self):
        """Test że schemat zawiera GroupedAlternativesRule."""
        items = RULES_SCHEMA["items"]["oneOf"]
        grouped_rule = next((r for r in items if "Wymagane obiekty z RÓŻNYCH grup" in r.get("title", "")), None)
        assert grouped_rule is not None
        assert "groups" in grouped_rule["keys"]
        assert "min_groups_required" in grouped_rule["keys"]

    def test_rules_schema_contains_prerequisite_badge_rule(self):
        """Test że schemat zawiera PrerequisiteBadgeRule."""
        items = RULES_SCHEMA["items"]["oneOf"]
        prereq_rule = next((r for r in items if "Wymaga posiadania innej odznaki" in r.get("title", "")), None)
        assert prereq_rule is not None
        assert "required_badge_code" in prereq_rule["keys"]

    def test_rules_schema_contains_multi_pool_requirement_rule(self):
        """Test że schemat zawiera MultiPoolRequirementRule."""
        items = RULES_SCHEMA["items"]["oneOf"]
        multi_pool_rule = next((r for r in items if "Wymagane ilości z RÓŻNYCH podzbiorów" in r.get("title", "")), None)
        assert multi_pool_rule is not None
        assert "pools" in multi_pool_rule["keys"]

    def test_rules_schema_all_rules_have_type_field(self):
        """Test że wszystkie reguły mają pole type (ukryte)."""
        items = RULES_SCHEMA["items"]["oneOf"]
        for rule in items:
            assert "keys" in rule
            assert "type" in rule["keys"]
            assert rule["keys"]["type"]["widget"] == "hidden"
