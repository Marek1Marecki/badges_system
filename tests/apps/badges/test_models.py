"""Testy dla modeli Django."""



from apps.badges.models import (
    RULES_SCHEMA,
    BadgeModel,
    BadgeTierModel,
    BadgeVersionModel,
    CountryModel,
    MacroregionModel,
    MesoregionModel,
    ProvinceModel,
    RegionBaseModel,
    SubprovinceModel,
    VoivodeshipModel,
)


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
        
        # Find ActivityRule
        activity_rule = next(rule for rule in oneOf if rule["keys"]["type"]["default"] == "ActivityRule")
        assert activity_rule["title"] == "Ograniczenie Aktywności"
        
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

    def test_allowed_activities_field(self):
        """Test pola dozwolonych aktywności."""
        oneOf = RULES_SCHEMA["items"]["oneOf"]
        activity_rule = next(rule for rule in oneOf if rule["keys"]["type"]["default"] == "ActivityRule")
        
        activities_field = activity_rule["keys"]["allowed_activities"]
        assert activities_field["type"] == "array"
        assert activities_field["title"] == "Dozwolone aktywności"
        
        items = activities_field["items"]
        assert items["type"] == "string"
        assert "HIKING" in items["choices"]
        assert "CYCLING" in items["choices"]
        assert "SKIING" in items["choices"]

    def test_limit_in_years_field(self):
        """Test pola limitu lat."""
        oneOf = RULES_SCHEMA["items"]["oneOf"]
        time_limit_rule = next(rule for rule in oneOf if rule["keys"]["type"]["default"] == "TimeLimitRule")
        
        limit_field = time_limit_rule["keys"]["limit_in_years"]
        assert limit_field["type"] == "integer"
        assert limit_field["title"] == "Limit (w latach)"


class TestRegionBaseModel:
    """Testy abstrakcyjnego modelu bazowego."""

    def test_region_base_model_fields(self):
        """Test pól modelu bazowego."""
        # Test that the model has the expected fields
        # Note: We can't instantiate abstract models directly, but we can test their structure
        assert hasattr(RegionBaseModel, 'name')
        assert hasattr(RegionBaseModel, 'translation')
        assert hasattr(RegionBaseModel, 'code')
        assert hasattr(RegionBaseModel, 'link')
        assert hasattr(RegionBaseModel, 'shape')
        assert hasattr(RegionBaseModel, 'created_at')
        assert hasattr(RegionBaseModel, 'updated_at')

    def test_region_base_model_meta(self):
        """Test meta klasy modelu bazowego."""
        assert RegionBaseModel._meta.abstract is True


class TestCountryModel:
    """Testy modelu państwa."""

    def test_country_model_inheritance(self):
        """Test dziedziczenia CountryModel."""
        assert issubclass(CountryModel, RegionBaseModel)

    def test_country_model_meta(self):
        """Test meta klasy CountryModel."""
        assert CountryModel._meta.db_table == "odznaki_country"
        assert CountryModel._meta.verbose_name == "Państwo"
        assert CountryModel._meta.verbose_name_plural == "Państwa"

    def test_country_model_has_order_field(self):
        """Test pola order."""
        assert hasattr(CountryModel, 'order')


class TestVoivodeshipModel:
    """Testy modelu województwa."""

    def test_voivodeship_model_inheritance(self):
        """Test dziedziczenia VoivodeshipModel."""
        assert issubclass(VoivodeshipModel, RegionBaseModel)

    def test_voivodeship_model_meta(self):
        """Test meta klasy VoivodeshipModel."""
        assert VoivodeshipModel._meta.db_table == "odznaki_voivodeship"
        assert VoivodeshipModel._meta.verbose_name == "Województwo"
        assert VoivodeshipModel._meta.verbose_name_plural == "Województwa"

    def test_voivodeship_model_unique_constraints(self):
        """Test unikalnych ograniczeń."""
        unique_together = VoivodeshipModel._meta.unique_together
        assert ("country", "code") in unique_together
        assert ("country", "name") in unique_together

    def test_voivodeship_model_has_country_field(self):
        """Test pola country."""
        assert hasattr(VoivodeshipModel, 'country')


class TestProvinceModel:
    """Testy modelu prowincji."""

    def test_province_model_inheritance(self):
        """Test dziedziczenia ProvinceModel."""
        assert issubclass(ProvinceModel, RegionBaseModel)

    def test_province_model_meta(self):
        """Test meta klasy ProvinceModel."""
        assert ProvinceModel._meta.db_table == "odznaki_province"
        assert ProvinceModel._meta.verbose_name == "Prowincja"
        assert ProvinceModel._meta.verbose_name_plural == "Prowincje"

    def test_province_model_unique_constraints(self):
        """Test unikalnych ograniczeń."""
        unique_together = ProvinceModel._meta.unique_together
        assert ("country", "code") in unique_together

    def test_province_model_has_country_field(self):
        """Test pola country."""
        assert hasattr(ProvinceModel, 'country')


class TestSubprovinceModel:
    """Testy modelu podprowincji."""

    def test_subprovince_model_inheritance(self):
        """Test dziedziczenia SubprovinceModel."""
        assert issubclass(SubprovinceModel, RegionBaseModel)

    def test_subprovince_model_meta(self):
        """Test meta klasy SubprovinceModel."""
        assert SubprovinceModel._meta.db_table == "odznaki_subprovince"
        assert SubprovinceModel._meta.verbose_name == "Podprowincja"
        assert SubprovinceModel._meta.verbose_name_plural == "Podprowincje"

    def test_subprovince_model_unique_constraints(self):
        """Test unikalnych ograniczeń."""
        unique_together = SubprovinceModel._meta.unique_together
        assert ("province", "code") in unique_together

    def test_subprovince_model_has_province_field(self):
        """Test pola province."""
        assert hasattr(SubprovinceModel, 'province')


class TestMacroregionModel:
    """Testy modelu makroregionu."""

    def test_macroregion_model_inheritance(self):
        """Test dziedziczenia MacroregionModel."""
        assert issubclass(MacroregionModel, RegionBaseModel)

    def test_macroregion_model_meta(self):
        """Test meta klasy MacroregionModel."""
        assert MacroregionModel._meta.db_table == "odznaki_macroregion"
        assert MacroregionModel._meta.verbose_name == "Makroregion"
        assert MacroregionModel._meta.verbose_name_plural == "Makroregiony"

    def test_macroregion_model_has_subprovince_field(self):
        """Test pola subprovince."""
        assert hasattr(MacroregionModel, 'subprovince')


class TestMesoregionModel:
    """Testy modelu mezoregionu."""

    def test_mesoregion_model_inheritance(self):
        """Test dziedziczenia MesoregionModel."""
        assert issubclass(MesoregionModel, RegionBaseModel)

    def test_mesoregion_model_meta(self):
        """Test meta klasy MesoregionModel."""
        assert MesoregionModel._meta.db_table == "odznaki_mesoregion"
        assert MesoregionModel._meta.verbose_name == "Mezoregion"
        assert MesoregionModel._meta.verbose_name_plural == "Mezoregiony"

    def test_mesoregion_model_has_macroregion_field(self):
        """Test pola macroregion."""
        assert hasattr(MesoregionModel, 'macroregion')




class TestBadgeModel:
    """Testy modelu odznaki."""

    def test_badge_model_fields(self):
        """Test pól modelu BadgeModel."""
        assert hasattr(BadgeModel, 'code')
        assert hasattr(BadgeModel, 'name')

    def test_badge_model_code_field(self):
        """Test pola code."""
        code_field = BadgeModel._meta.get_field('code')
        assert code_field.max_length == 50
        assert code_field.unique is True
        assert code_field.verbose_name == "Kod"

    def test_badge_model_name_field(self):
        """Test pola name."""
        name_field = BadgeModel._meta.get_field('name')
        assert name_field.max_length == 255
        assert name_field.verbose_name == "Nazwa Odznaki"

    def test_badge_model_str_method(self):
        """Test metody __str__."""
        assert hasattr(BadgeModel, '__str__')


class TestBadgeVersionModel:
    """Testy modelu wersji odznaki."""

    def test_badge_version_model_fields(self):
        """Test pól modelu BadgeVersionModel."""
        assert hasattr(BadgeVersionModel, 'badge')
        assert hasattr(BadgeVersionModel, 'version_code')
        assert hasattr(BadgeVersionModel, 'valid_from')
        assert hasattr(BadgeVersionModel, 'rules')
        assert hasattr(BadgeVersionModel, 'pool_peaks')

    def test_badge_version_model_badge_field(self):
        """Test pola badge."""
        badge_field = BadgeVersionModel._meta.get_field('badge')
        assert badge_field.remote_field.related_name == "versions"

    def test_badge_version_model_version_code_field(self):
        """Test pola version_code."""
        version_field = BadgeVersionModel._meta.get_field('version_code')
        assert version_field.max_length == 50
        assert version_field.verbose_name == "Wersja (np. v2024)"

    def test_badge_version_model_valid_from_field(self):
        """Test pola valid_from."""
        valid_from_field = BadgeVersionModel._meta.get_field('valid_from')
        assert valid_from_field.verbose_name == "Obowiązuje od"


    def test_badge_version_model_rules_field(self):
        """Test pola rules."""
        rules_field = BadgeVersionModel._meta.get_field('rules')
        assert rules_field.schema == RULES_SCHEMA
        assert rules_field.verbose_name == "Reguły biznesowe"

    def test_badge_version_model_str_method(self):
        """Test metody __str__."""
        assert hasattr(BadgeVersionModel, '__str__')


class TestBadgeTierModel:
    """Testy modelu stopnia odznaki."""

    def test_badge_tier_model_fields(self):
        """Test pól modelu BadgeTierModel."""
        assert hasattr(BadgeTierModel, 'version')
        assert hasattr(BadgeTierModel, 'name')
        assert hasattr(BadgeTierModel, 'order')
        assert hasattr(BadgeTierModel, 'badge_image')
        assert hasattr(BadgeTierModel, 'required_peaks_count')

    def test_badge_tier_model_required_peaks_count_field(self):
        """Test pola required_peaks_count."""
        required_field = BadgeTierModel._meta.get_field('required_peaks_count')
        assert required_field.null is True
        assert required_field.blank is True
        assert "Puste = wymaga zdobycia WSZYSTKIECH szczytów z puli tej wersji." in required_field.help_text

    def test_badge_tier_model_version_field(self):
        """Test pola version."""
        version_field = BadgeTierModel._meta.get_field('version')
        assert version_field.remote_field.related_name == "tiers"
        assert version_field.verbose_name == "Wersja odznaki"

    def test_badge_tier_model_order_field(self):
        """Test pola order."""
        order_field = BadgeTierModel._meta.get_field('order')
        assert order_field.default == 1
        assert order_field.verbose_name == "Kolejność zdobywania (1=najniższy)"

    def test_badge_tier_model_name_field(self):
        """Test pola name."""
        name_field = BadgeTierModel._meta.get_field('name')
        assert name_field.max_length == 50
        assert name_field.verbose_name == "Stopień"

    def test_badge_tier_model_badge_image_field(self):
        """Test pola badge_image."""
        image_field = BadgeTierModel._meta.get_field('badge_image')
        assert image_field.null is True
        assert image_field.blank is True
        assert image_field.verbose_name == "Zdjęcie blachy (Odznaki)"

    def test_badge_tier_model_str_method(self):
        """Test metody __str__."""
        assert hasattr(BadgeTierModel, '__str__')
