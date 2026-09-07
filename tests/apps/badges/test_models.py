"""Testy dla modeli Django."""

from unittest.mock import MagicMock

from apps.badges.models import (
    BadgeModel,
    BadgeTierModel,
    BadgeVersionModel,
    RegionFlatModel,
    RegionLevel,
)
from apps.badges.rules_schema import RULES_SCHEMA


class TestRulesSchema:
    """Testy schematu reguł."""

    def test_rules_schema_structure(self):
        """Test struktury schematu reguł."""
        assert RULES_SCHEMA["type"] == "list"
        assert RULES_SCHEMA["title"] == "Reguły Biznesowe Odznaki"
        assert "items" in RULES_SCHEMA

        items = RULES_SCHEMA["items"]
        assert "oneOf" in items

        oneOf = items["oneOf"]
        assert len(oneOf) == 11

        # Check that each rule type has the expected structure
        for rule_def in oneOf:
            assert rule_def["type"] == "dict"
            assert "keys" in rule_def
            assert "type" in rule_def["keys"]

    def test_rule_type_choices(self):
        """Test wyborów typu reguły."""
        oneOf = RULES_SCHEMA["items"]["oneOf"]

        # Find TimeLimitRule
        time_limit_rule = next(rule for rule in oneOf if rule["keys"]["type"]["default"] == "TimeLimitRule")
        assert time_limit_rule["title"] == "Limit Czasowy"

        # Find RequiresClubJoinDateRule
        club_rule = next(rule for rule in oneOf if rule["keys"]["type"]["default"] == "RequiresClubJoinDateRule")
        assert club_rule["title"] == "Wymaga zapisu do Klubu"

        # Find MinAgeRule
        min_age_rule = next(rule for rule in oneOf if rule["keys"]["type"]["default"] == "MinAgeRule")
        assert min_age_rule["title"] == "Minimalny Wiek"

        # Find StartDateRule
        start_date_rule = next(rule for rule in oneOf if rule["keys"]["type"]["default"] == "StartDateRule")
        assert start_date_rule["title"] == "Szczyty zaliczane od daty"

        # Find MandatoryObjectsRule
        mandatory_rule = next(rule for rule in oneOf if rule["keys"]["type"]["default"] == "MandatoryObjectsRule")
        assert mandatory_rule["title"] == "Obowiązkowe konkretne obiekty"

        # Find GroupedAlternativesRule
        grouped_rule = next(rule for rule in oneOf if rule["keys"]["type"]["default"] == "GroupedAlternativesRule")
        assert grouped_rule["title"] == "Wymagane obiekty z RÓŻNYCH grup (Wiaderek)"

        # Find PrerequisiteBadgeRule
        prerequisite_rule = next(rule for rule in oneOf if rule["keys"]["type"]["default"] == "PrerequisiteBadgeRule")
        assert prerequisite_rule["title"] == "Wymaga posiadania innej odznaki"

        # Find DateWindowRule
        date_window_rule = next(rule for rule in oneOf if rule["keys"]["type"]["default"] == "DateWindowRule")
        assert date_window_rule["title"] == "Zamknięte Okno Czasowe (np. Jubileusz)"

    def test_limit_in_years_field(self):
        """Test pola limitu lat."""
        oneOf = RULES_SCHEMA["items"]["oneOf"]
        time_limit_rule = next(rule for rule in oneOf if rule["keys"]["type"]["default"] == "TimeLimitRule")

        limit_field = time_limit_rule["keys"]["limit_in_years"]
        assert limit_field["type"] == "integer"
        assert limit_field["title"] == "Limit (w latach)"


class TestRegionFlatModel:
    """Testy modelu RegionFlatModel (ADR-028)."""

    def test_region_flat_model_fields(self):
        """Test pól modelu RegionFlatModel."""
        assert hasattr(RegionFlatModel, "name")
        assert hasattr(RegionFlatModel, "translation")
        assert hasattr(RegionFlatModel, "code")
        assert hasattr(RegionFlatModel, "level")
        assert hasattr(RegionFlatModel, "path")
        assert hasattr(RegionFlatModel, "shape")
        assert hasattr(RegionFlatModel, "parent")
        assert hasattr(RegionFlatModel, "neighbors")
        assert hasattr(RegionFlatModel, "created_at")
        assert hasattr(RegionFlatModel, "updated_at")

    def test_region_flat_model_meta(self):
        """Test meta klasy RegionFlatModel."""
        assert RegionFlatModel._meta.db_table == "regions_flat"
        assert RegionFlatModel._meta.verbose_name == "Region (Flat)"
        assert RegionFlatModel._meta.verbose_name_plural == "Regiony (Flat)"

    def test_region_level_choices(self):
        """Test wartości wyboru RegionLevel."""
        assert RegionLevel.COUNTRY == "COUNTRY"
        assert RegionLevel.VOIVODESHIP == "VOIVODESHIP"
        assert RegionLevel.TOURIST_REGION == "TOURIST_REGION"

    def test_region_flat_model_str(self):
        """Test __str__ RegionFlatModel."""
        region = MagicMock()
        region.name = "Polska"
        region.code = "PL"
        result = RegionFlatModel.__str__(region)
        assert "Polska" in result
        assert "PL" in result


class TestRegionFlatModelStr:
    """Testy __str__ modeli."""

    def test_region_flat_model_str(self):
        """Test __str__ RegionFlatModel."""
        region = MagicMock()
        region.name = "Polska"
        region.code = "PL"
        result = RegionFlatModel.__str__(region)
        assert "Polska" in result
        assert "PL" in result

    def test_badge_model_str(self):
        """Test __str__ BadgeModel."""
        badge = MagicMock()
        badge.name = "Korona Sudetów"
        result = BadgeModel.__str__(badge)
        assert "Korona Sudetów" in result

    def test_badge_version_model_str(self):
        """Test __str__ BadgeVersionModel."""
        badge = MagicMock()
        badge.name = "KGP"
        version = MagicMock()
        version.badge = badge
        version.version_code = "v2024"
        result = BadgeVersionModel.__str__(version)
        assert "KGP" in result
        assert "v2024" in result

    def test_object_region_cache_str(self):
        """Test __str__ ObjectRegionCache."""
        from apps.badges.models import ObjectRegionCache

        obj = MagicMock()
        obj.tourist_object.name = "Rysy"
        obj.region_name = "Tatry"
        obj.get_region_level_display.return_value = "Region"
        obj.distance_meters = 0

        result = ObjectRegionCache.__str__(obj)

        assert "Rysy" in result
        assert "Tatry" in result

    def test_object_region_cache_str_with_distance(self):
        """Test __str__ ObjectRegionCache z odległością."""
        from apps.badges.models import ObjectRegionCache

        obj = MagicMock()
        obj.tourist_object.name = "Rysy"
        obj.region_name = "Tatry"
        obj.get_region_level_display.return_value = "Region"
        obj.distance_meters = 150

        result = ObjectRegionCache.__str__(obj)

        assert "Rysy" in result
        assert "Bufor 150m" in result

    def test_organizer_model_str(self):
        """Test __str__ OrganizerModel."""
        from apps.badges.models import OrganizerModel

        organizer = MagicMock()
        organizer.name = "PTTK"
        result = OrganizerModel.__str__(organizer)
        assert "PTTK" in result

    def test_osm_type_mapping_str_ignored(self):
        """Test __str__ OsmTypeMapping gdy ignorowany."""
        from apps.badges.models import OsmTypeMapping

        mapping = MagicMock()
        mapping.osm_key = "tourism"
        mapping.osm_value = "hotel"
        mapping.target_type = "HOTEL"
        mapping.is_ignored = True
        result = OsmTypeMapping.__str__(mapping)
        assert "tourism=hotel" in result
        assert "HOTEL" in result
        assert "Ignorowany" in result

    def test_tourist_object_str_with_altitude(self):
        """Test __str__ TouristObject z wysokością."""
        from apps.badges.models import TouristObject

        obj = MagicMock()
        obj.name = "Rysy"
        obj.altitude = 2499
        obj.type = "peak"
        obj.is_active = True
        result = TouristObject.__str__(obj)
        assert "Rysy" in result
        assert "2499m" in result
        assert "peak" in result

    def test_tourist_object_str_inactive(self):
        """Test __str__ TouristObject nieaktywny."""
        from apps.badges.models import TouristObject

        obj = MagicMock()
        obj.name = "Stary szczyt"
        obj.altitude = None
        obj.type = "peak"
        obj.is_active = False
        result = TouristObject.__str__(obj)
        assert "Stary szczyt" in result
        assert "[peak]" in result
        assert "NIE ISTNIEJE" in result

    def test_badge_tier_model_str(self):
        """Test __str__ BadgeTierModel."""
        from apps.badges.models import BadgeTierModel

        tier = MagicMock()
        tier.version = "v2024"
        tier.get_name_display.return_value = "Standard"
        result = BadgeTierModel.__str__(tier)
        assert "v2024" in result
        assert "Standard" in result

    def test_proximity_candidate_str(self):
        """Test __str__ ProximityCandidate."""
        from apps.badges.models import ProximityCandidate

        obj_a = MagicMock()
        obj_a.name = "Rysy"
        obj_a.get_type_display.return_value = "Szczyt"
        obj_a.type = "peak"
        obj_b = MagicMock()
        obj_b.name = "Czarny Staw"
        obj_b.get_type_display.return_value = "Jezioro"
        obj_b.type = "lake"

        candidate = MagicMock()
        candidate.obj_a = obj_a
        candidate.obj_b = obj_b
        candidate.distance_meters = 250

        result = ProximityCandidate.__str__(candidate)

        assert "Rysy" in result
        assert "Czarny Staw" in result
        assert "250m" in result

    def test_osm_sync_conflict_str(self):
        """Test __str__ OsmSyncConflict."""
        from apps.badges.models import OsmSyncConflict

        obj = MagicMock()
        obj.tourist_object.name = "Rysy"
        obj.field_name = "name"
        obj.old_value = "Old Name"
        obj.new_value = "New Name"
        result = OsmSyncConflict.__str__(obj)
        assert "Rysy" in result
        assert "name" in result
        assert "Old Name" in result
        assert "New Name" in result

    def test_badge_news_item_str(self):
        """Test __str__ BadgeNewsItem."""
        from apps.badges.models import BadgeNewsItem

        item = MagicMock()
        item.get_change_type_display.return_value = "DODANO"
        item.badge_name = "KGP"
        result = BadgeNewsItem.__str__(item)
        assert "DODANO" in result
        assert "KGP" in result


class TestBadgeModel:
    """Testy modelu odznaki."""

    def test_badge_model_fields(self):
        """Test pól modelu BadgeModel."""
        assert hasattr(BadgeModel, "code")
        assert hasattr(BadgeModel, "name")

    def test_badge_model_code_field(self):
        """Test pola code."""
        code_field = BadgeModel._meta.get_field("code")
        assert code_field.max_length == 50
        assert code_field.unique is True
        assert code_field.verbose_name == "Kod"

    def test_badge_model_name_field(self):
        """Test pola name."""
        name_field = BadgeModel._meta.get_field("name")
        assert name_field.max_length == 255
        assert name_field.verbose_name == "Nazwa Odznaki"

    def test_badge_model_str_method(self):
        """Test metody __str__."""
        assert hasattr(BadgeModel, "__str__")


class TestBadgeVersionModel:
    """Testy modelu wersji odznaki."""

    def test_badge_version_model_fields(self):
        """Test pól modelu BadgeVersionModel."""
        assert hasattr(BadgeVersionModel, "badge")
        assert hasattr(BadgeVersionModel, "version_code")
        assert hasattr(BadgeVersionModel, "valid_from")
        assert hasattr(BadgeVersionModel, "rules")
        assert hasattr(BadgeVersionModel, "pool_peaks")

    def test_badge_version_model_badge_field(self):
        """Test pola badge."""
        badge_field = BadgeVersionModel._meta.get_field("badge")
        assert badge_field.remote_field.related_name == "versions"

    def test_badge_version_model_version_code_field(self):
        """Test pola version_code."""
        version_field = BadgeVersionModel._meta.get_field("version_code")
        assert version_field.max_length == 50
        assert version_field.verbose_name == "Wersja (np. v2024)"

    def test_badge_version_model_valid_from_field(self):
        """Test pola valid_from."""
        valid_from_field = BadgeVersionModel._meta.get_field("valid_from")
        assert valid_from_field.verbose_name == "Obowiązuje od"

    def test_badge_version_model_rules_field(self):
        """Test pola rules."""
        rules_field = BadgeVersionModel._meta.get_field("rules")
        assert rules_field.schema == RULES_SCHEMA
        assert rules_field.verbose_name == "Reguły biznesowe"

    def test_badge_version_model_str_method(self):
        """Test metody __str__."""
        assert hasattr(BadgeVersionModel, "__str__")


class TestBadgeTierModel:
    """Testy modelu stopnia odznaki."""

    def test_badge_tier_model_fields(self):
        """Test pól modelu BadgeTierModel."""
        assert hasattr(BadgeTierModel, "version")
        assert hasattr(BadgeTierModel, "name")
        assert hasattr(BadgeTierModel, "order")
        assert hasattr(BadgeTierModel, "badge_image")
        assert hasattr(BadgeTierModel, "required_peaks_count")

    def test_badge_tier_model_required_peaks_count_field(self):
        """Test pola required_peaks_count."""
        required_field = BadgeTierModel._meta.get_field("required_peaks_count")
        assert required_field.null is True
        assert required_field.blank is True
        assert "Puste = wymaga zdobycia WSZYSTKIECH szczytów z puli tej wersji." in required_field.help_text

    def test_badge_tier_model_version_field(self):
        """Test pola version."""
        version_field = BadgeTierModel._meta.get_field("version")
        assert version_field.remote_field.related_name == "tiers"
        assert version_field.verbose_name == "Wersja odznaki"

    def test_badge_tier_model_order_field(self):
        """Test pola order."""
        order_field = BadgeTierModel._meta.get_field("order")
        assert order_field.default == 1
        assert order_field.verbose_name == "Kolejność zdobywania (1=najniższy)"

    def test_badge_tier_model_name_field(self):
        """Test pola name."""
        name_field = BadgeTierModel._meta.get_field("name")
        assert name_field.max_length == 50
        assert name_field.verbose_name == "Stopień"

    def test_badge_tier_model_badge_image_field(self):
        """Test pola badge_image."""
        image_field = BadgeTierModel._meta.get_field("badge_image")
        assert image_field.null is True
        assert image_field.blank is True
        assert image_field.verbose_name == "Zdjęcie blachy (Odznaki)"

    def test_badge_tier_model_str_method(self):
        """Test metody __str__."""
        assert hasattr(BadgeTierModel, "__str__")
