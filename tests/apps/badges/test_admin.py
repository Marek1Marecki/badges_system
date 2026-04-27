"""Testy dla konfiguracji Django Admin."""

from unittest.mock import MagicMock, Mock, patch

from leaflet.admin import LeafletGeoAdmin

from apps.badges.admin import (
    AddToBadgeForm,
    BadgeAdmin,
    BadgeTierInline,
    BadgeVersionAdmin,
    CountryAdmin,
    MacroregionAdmin,
    MesoregionAdmin,
    ObjectRegionCacheInline,
    OrganizerAdmin,
    OsmTypeMappingAdmin,
    PendingMappingFilter,
    ProvinceAdmin,
    ReadOnlyMapAdmin,
    RegionLevelFilter,
    SubprovinceAdmin,
    TouristObjectAdmin,
    TouristRegionAdmin,
    VoivodeshipAdmin,
)
from apps.badges.models import (
    BadgeModel,
    BadgeTierModel,
    BadgeVersionModel,
    CountryModel,
    MacroregionModel,
    MesoregionModel,
    ObjectRegionCache,
    OsmTypeMapping,
    ProvinceModel,
    SubprovinceModel,
    TouristObject,
    VoivodeshipModel,
)


class TestReadOnlyMapAdmin:
    """Weryfikacja konfiguracji mapy tylko do odczytu (Leaflet)."""

    def test_read_only_map_admin_inheritance(self) -> None:
        """Sprawdza, czy panel dziedziczy po poprawnej klasie Leaflet."""
        assert issubclass(ReadOnlyMapAdmin, LeafletGeoAdmin), "Musi dziedziczyć po LeafletGeoAdmin"

    def test_read_only_map_admin_widget_config(self) -> None:
        """Sprawdza, czy edycja poligonów jest zablokowana i ustawiono środek mapy."""
        # W LeafletGeoAdmin kluczową flagą blokującą narzędzia rysowania jest `modifiable`
        assert ReadOnlyMapAdmin.modifiable is False, "Mapa musi być tylko do odczytu"

        # Konfiguracja Leaflet odbywa się przez słownik settings_overrides
        overrides = getattr(ReadOnlyMapAdmin, "settings_overrides", {})
        assert "DEFAULT_CENTER" in overrides, "Brak wyśrodkowania mapy na Polskę"
        assert overrides["DEFAULT_CENTER"] == (52.0, 19.0)
        assert overrides["DEFAULT_ZOOM"] == 5


class TestCountryAdmin:
    """Testy admina państw."""

    def test_country_admin_inheritance(self):
        """Test dziedziczenia CountryAdmin."""
        assert issubclass(CountryAdmin, ReadOnlyMapAdmin)

    def test_country_admin_list_display(self):
        """Test pól list_display."""
        expected = ("name", "code", "order")
        assert CountryAdmin.list_display == expected


class TestVoivodeshipAdmin:
    """Testy admina województw."""

    def test_voivodeship_admin_inheritance(self):
        """Test dziedziczenia VoivodeshipAdmin."""
        assert issubclass(VoivodeshipAdmin, ReadOnlyMapAdmin)

    def test_voivodeship_admin_list_display(self):
        """Test pól list_display."""
        expected = ("name", "code", "country")
        assert VoivodeshipAdmin.list_display == expected

    def test_voivodeship_admin_list_filter(self):
        """Test pól list_filter."""
        expected = ("country",)
        assert VoivodeshipAdmin.list_filter == expected


class TestProvinceAdmin:
    """Testy admina prowincji."""

    def test_province_admin_inheritance(self):
        """Test dziedziczenia ProvinceAdmin."""
        assert issubclass(ProvinceAdmin, ReadOnlyMapAdmin)

    def test_province_admin_list_display(self):
        """Test pól list_display."""
        expected = ("name", "code", "country")
        assert ProvinceAdmin.list_display == expected


class TestSubprovinceAdmin:
    """Testy admina podprowincji."""

    def test_subprovince_admin_inheritance(self):
        """Test dziedziczenia SubprovinceAdmin."""
        assert issubclass(SubprovinceAdmin, ReadOnlyMapAdmin)

    def test_subprovince_admin_list_display(self):
        """Test pól list_display."""
        expected = ("name", "code", "province")
        assert SubprovinceAdmin.list_display == expected


class TestMacroregionAdmin:
    """Testy admina makroregionów."""

    def test_macroregion_admin_inheritance(self):
        """Test dziedziczenia MacroregionAdmin."""
        assert issubclass(MacroregionAdmin, ReadOnlyMapAdmin)

    def test_macroregion_admin_list_display(self):
        """Test pól list_display."""
        expected = ("name", "code", "subprovince")
        assert MacroregionAdmin.list_display == expected

    def test_macroregion_admin_search_fields(self):
        """Test pól search_fields."""
        expected = ("name", "code")
        assert MacroregionAdmin.search_fields == expected


class TestMesoregionAdmin:
    """Testy admina mezoregionów."""

    def test_mesoregion_admin_inheritance(self):
        """Test dziedziczenia MesoregionAdmin."""
        assert issubclass(MesoregionAdmin, ReadOnlyMapAdmin)

    def test_mesoregion_admin_list_display(self):
        """Test pól list_display."""
        expected = ("name", "code", "macroregion")
        assert MesoregionAdmin.list_display == expected

    def test_mesoregion_admin_search_fields(self):
        """Test pól search_fields."""
        expected = ("name", "code")
        assert MesoregionAdmin.search_fields == expected


class TestBadgeAdmin:
    """Testy admina odznak."""

    def test_badge_admin_inheritance(self):
        """Test dziedziczenia BadgeAdmin."""
        from django.contrib import admin
        assert issubclass(BadgeAdmin, admin.ModelAdmin)

    def test_badge_admin_list_display(self):
        """Test pól list_display."""
        expected = ("name", "code", "organizer", "is_booklet_required")
        assert BadgeAdmin.list_display == expected


class TestBadgeVersionAdmin:
    """Testy admina wersji odznak."""

    def test_badge_version_admin_inheritance(self):
        """Test dziedziczenia BadgeVersionAdmin."""
        from django.contrib import admin
        assert issubclass(BadgeVersionAdmin, admin.ModelAdmin)

    def test_badge_version_admin_list_display(self):
        """Test pól list_display."""
        expected = ("badge", "version_code", "valid_from")
        assert BadgeVersionAdmin.list_display == expected

    def test_badge_version_admin_list_filter(self):
        """Test pól list_filter."""
        expected = ("badge", "valid_from")
        assert BadgeVersionAdmin.list_filter == expected


class TestAdminRegistrations:
    """Testy rejestracji adminów."""

    def test_country_model_is_registered(self):
        """Test że CountryModel jest zarejestrowany."""
        from django.contrib import admin
        assert admin.site.is_registered(CountryModel)

    def test_voivodeship_model_is_registered(self):
        """Test że VoivodeshipModel jest zarejestrowany."""
        from django.contrib import admin
        assert admin.site.is_registered(VoivodeshipModel)

    def test_province_model_is_registered(self):
        """Test że ProvinceModel jest zarejestrowany."""
        from django.contrib import admin
        assert admin.site.is_registered(ProvinceModel)

    def test_subprovince_model_is_registered(self):
        """Test że SubprovinceModel jest zarejestrowany."""
        from django.contrib import admin
        assert admin.site.is_registered(SubprovinceModel)

    def test_macroregion_model_is_registered(self):
        """Test że MacroregionModel jest zarejestrowany."""
        from django.contrib import admin
        assert admin.site.is_registered(MacroregionModel)

    def test_mesoregion_model_is_registered(self):
        """Test że MesoregionModel jest zarejestrowany."""
        from django.contrib import admin
        assert admin.site.is_registered(MesoregionModel)

    def test_badge_model_is_registered(self):
        """Test że BadgeModel jest zarejestrowany."""
        from django.contrib import admin
        assert admin.site.is_registered(BadgeModel)

    def test_badge_version_model_is_registered(self):
        """Test że BadgeVersionModel jest zarejestrowany."""
        from django.contrib import admin
        assert admin.site.is_registered(BadgeVersionModel)


class TestAddToBadgeForm:
    """Testy formularza AddToBadgeForm."""

    def test_form_fields(self):
        """Test pól formularza."""
        form = AddToBadgeForm()
        assert "badge_version" in form.fields
        assert form.fields["badge_version"].required is True

    def test_form_queryset_initialization(self):
        """Test inicjalizacji querysetu pól."""
        form = AddToBadgeForm()
        # Sprawdzamy czy queryset nie jest pusty po inicjalizacji
        assert form.fields["badge_version"].queryset.model == BadgeVersionModel


class TestObjectRegionCacheInline:
    """Testy inline'a ObjectRegionCache."""

    def test_inline_configuration(self):
        """Test konfiguracji inline'a."""
        from django.contrib.admin import AdminSite
        inline = ObjectRegionCacheInline(ObjectRegionCache, AdminSite())
        assert inline.model == ObjectRegionCache
        assert inline.extra == 0
        assert inline.can_delete is False

    def test_inline_readonly_fields(self):
        """Test pól readonly."""
        from django.contrib.admin import AdminSite
        inline = ObjectRegionCacheInline(ObjectRegionCache, AdminSite())
        expected_readonly = ("region_level", "region_id", "region_name", "distance_meters")
        assert inline.readonly_fields == expected_readonly

    def test_inline_has_add_permission(self):
        """Test uprawnień do dodawania."""
        from django.contrib.admin import AdminSite
        inline = ObjectRegionCacheInline(ObjectRegionCache, AdminSite())
        assert inline.has_add_permission(None) is False


class TestRegionLevelFilter:
    """Testy filtra RegionLevelFilter."""

    def test_filter_attributes(self):
        """Test atrybutów filtra."""
        with patch.object(RegionLevelFilter, "lookups", return_value=[]):
            filter_obj = RegionLevelFilter(None, {"region_cache": "test"}, TouristObject, None)
        assert filter_obj.title == "Region (CQRS Cache)"
        assert filter_obj.parameter_name == "region_cache"

    def test_filter_lookups(self):
        """Test metody lookups."""
        with patch('apps.badges.admin.ObjectRegionCache.objects') as mock_objects:
            mock_objects.values_list.return_value.distinct.return_value.order_by.return_value = ["Polska", "Czechy"]
            with patch.object(RegionLevelFilter, "lookups", return_value=[]):
                filter_obj = RegionLevelFilter(None, {}, TouristObject, None)
            
            lookups = filter_obj.lookups(None, None)
            
            expected = [("Polska", "Polska"), ("Czechy", "Czechy")]
            assert lookups == expected

    def test_filter_queryset_with_value(self):
        """Test filtrowania querysetu z wartością."""
        with patch.object(RegionLevelFilter, "lookups", return_value=[]):
            filter_obj = RegionLevelFilter(None, {"region_cache": "Polska"}, TouristObject, None)
        
        mock_queryset = Mock()
        mock_filtered = Mock()
        mock_queryset.filter.return_value.distinct.return_value = mock_filtered
        
        result = filter_obj.queryset(None, mock_queryset)
        
        assert result == mock_filtered
        mock_queryset.filter.assert_called_once_with(cached_regions__region_name=filter_obj.value())

    def test_filter_queryset_without_value(self):
        """Test filtrowania querysetu bez wartości."""
        with patch.object(RegionLevelFilter, "lookups", return_value=[]):
            filter_obj = RegionLevelFilter(None, {}, TouristObject, None)
        
        mock_queryset = Mock()
        result = filter_obj.queryset(None, mock_queryset)
        
        assert result == mock_queryset


class TestPendingMappingFilter:
    """Testy filtra PendingMappingFilter."""

    def test_filter_attributes(self):
        """Test atrybutów filtra."""
        filter_obj = PendingMappingFilter(None, {"status": "pending"}, OsmTypeMapping, None)
        assert filter_obj.title == "Status mapowania"
        assert filter_obj.parameter_name == "status"

    def test_filter_lookups(self):
        """Test metody lookups."""
        filter_obj = PendingMappingFilter(None, {}, OsmTypeMapping, None)
        lookups = filter_obj.lookups(None, None)
        
        expected = (
            ("pending", "Oczekujące na decyzję (Inbox)"),
            ("mapped", "Zmapowane (Gotowe)"),
            ("ignored", "Ignorowane"),
        )
        assert lookups == expected

    def test_filter_queryset_pending(self):
        """Test filtrowania na 'pending'."""
        filter_obj = PendingMappingFilter(None, {"status": "pending"}, OsmTypeMapping, None)
        filter_obj.value = Mock(return_value="pending")
        
        mock_queryset = Mock()
        mock_filter1 = MagicMock()
        mock_filter2 = MagicMock()
        mock_queryset.filter.side_effect = [mock_filter1, mock_filter2]
        mock_filter1.__or__.return_value = "or_result"
        
        result = filter_obj.queryset(None, mock_queryset)
        
        mock_queryset.filter.assert_any_call(target_type__isnull=True, is_ignored=False)
        mock_queryset.filter.assert_any_call(target_type__exact="", is_ignored=False)
        assert mock_queryset.filter.call_count == 2

    def test_filter_queryset_mapped(self):
        """Test filtrowania na 'mapped'."""
        filter_obj = PendingMappingFilter(None, {"status": "mapped"}, OsmTypeMapping, None)
        filter_obj.value = Mock(return_value="mapped")
        
        mock_queryset = Mock()
        mock_exclude1 = Mock()
        mock_exclude2 = Mock()
        mock_filter = Mock()
        mock_queryset.exclude.return_value = mock_exclude1
        mock_exclude1.exclude.return_value = mock_exclude2
        mock_exclude2.filter.return_value = mock_filter
        
        result = filter_obj.queryset(None, mock_queryset)
        
        mock_queryset.exclude.assert_called_once_with(target_type__isnull=True)
        mock_exclude1.exclude.assert_called_once_with(target_type__exact="")
        mock_exclude2.filter.assert_called_once_with(is_ignored=False)

    def test_filter_queryset_ignored(self):
        """Test filtrowania na 'ignored'."""
        filter_obj = PendingMappingFilter(None, {"status": "ignored"}, OsmTypeMapping, None)
        filter_obj.value = Mock(return_value="ignored")
        
        mock_queryset = Mock()
        mock_filter = Mock()
        mock_queryset.filter.return_value = mock_filter
        
        result = filter_obj.queryset(None, mock_queryset)
        
        mock_queryset.filter.assert_called_once_with(is_ignored=True)

    def test_filter_queryset_no_value(self):
        """Test filtrowania bez wartości."""
        filter_obj = PendingMappingFilter(None, {}, OsmTypeMapping, None)
        filter_obj.value = Mock(return_value=None)
        
        mock_queryset = Mock()
        result = filter_obj.queryset(None, mock_queryset)
        
        assert result == mock_queryset


class TestOsmTypeMappingAdmin:
    """Testy admina OsmTypeMapping."""

    def test_osm_type_mapping_admin_inheritance(self):
        """Test dziedziczenia OsmTypeMappingAdmin."""
        from django.contrib import admin
        assert issubclass(OsmTypeMappingAdmin, admin.ModelAdmin)

    def test_osm_type_mapping_admin_list_display(self):
        """Test pól list_display."""
        expected = ("osm_key", "osm_value", "target_type", "is_ignored")
        assert OsmTypeMappingAdmin.list_display == expected

    def test_osm_type_mapping_admin_list_editable(self):
        """Test pól list_editable."""
        expected = ("target_type", "is_ignored")
        assert OsmTypeMappingAdmin.list_editable == expected

    def test_osm_type_mapping_admin_list_filter(self):
        """Test pól list_filter."""
        assert OsmTypeMappingAdmin.list_filter[0] == PendingMappingFilter
        assert "osm_key" in OsmTypeMappingAdmin.list_filter

    def test_osm_type_mapping_admin_search_fields(self):
        """Test pól search_fields."""
        expected = ("osm_key", "osm_value", "target_type")
        assert OsmTypeMappingAdmin.search_fields == expected


class TestTouristObjectAdmin:
    """Testy admina TouristObject."""

    def test_tourist_object_admin_inheritance(self):
        """Test dziedziczenia TouristObjectAdmin."""
        assert issubclass(TouristObjectAdmin, LeafletGeoAdmin)

    def test_tourist_object_admin_form(self):
        """Test formularza admina."""
        from apps.badges.forms import TouristObjectAdminForm
        assert TouristObjectAdmin.form == TouristObjectAdminForm

    def test_tourist_object_admin_list_display(self):
        """Test pól list_display."""
        expected = ("name", "type", "altitude", "osm_id", "code", "is_active")
        assert TouristObjectAdmin.list_display == expected

    def test_tourist_object_admin_list_filter(self):
        """Test pól list_filter."""
        expected_fields = ("is_active", "type", RegionLevelFilter)
        assert TouristObjectAdmin.list_filter == expected_fields

    def test_tourist_object_admin_search_fields(self):
        """Test pól search_fields."""
        expected = ("name", "alt_name", "osm_id", "code")
        assert TouristObjectAdmin.search_fields == expected

    def test_tourist_object_admin_actions(self):
        """Test akcji admina."""
        expected_actions = ["recalculate_regions_async", "add_to_badge_version", "show_ids_for_json"]
        assert TouristObjectAdmin.actions == expected_actions

    def test_tourist_object_admin_modifiable(self):
        """Test modifiable."""
        assert TouristObjectAdmin.modifiable is True

    def test_tourist_object_admin_settings_overrides(self):
        """Test ustawień mapy."""
        expected_overrides = {
            "DEFAULT_CENTER": (52.0, 19.0),
            "DEFAULT_ZOOM": 5,
        }
        assert TouristObjectAdmin.settings_overrides == expected_overrides

    def test_tourist_object_admin_inlines(self):
        """Test inline'ów."""
        assert TouristObjectAdmin.inlines == [ObjectRegionCacheInline]

    def test_tourist_object_admin_fieldsets_structure(self):
        """Test struktury fieldsets."""
        fieldsets = TouristObjectAdmin.fieldsets
        assert len(fieldsets) == 5
        
        # Sprawdzamy tytuły sekcji
        titles = [fs[0] for fs in fieldsets]
        expected_titles = [
            "Złoty Standard (Curated)",
            "Stan fizyczny i cykl życia",
            "Ewidencja i Relacje",
            "Integracja z OSM (Data Lake)",
            "Dane Wyliczane w Tle (CQRS)",
        ]
        assert titles == expected_titles


class TestOrganizerAdmin:
    """Testy admina Organizer."""

    def test_organizer_admin_inheritance(self):
        """Test dziedziczenia OrganizerAdmin."""
        from django.contrib import admin
        assert issubclass(OrganizerAdmin, admin.ModelAdmin)

    def test_organizer_admin_list_display(self):
        """Test pól list_display."""
        expected = ("name", "is_booklet_required", "has_publication_consent", "club_rules_link")
        assert OrganizerAdmin.list_display == expected

    def test_organizer_admin_list_filter(self):
        """Test pól list_filter."""
        expected = ("is_booklet_required", "has_publication_consent")
        assert OrganizerAdmin.list_filter == expected

    def test_organizer_admin_search_fields(self):
        """Test pól search_fields."""
        expected = ("name",)
        assert OrganizerAdmin.search_fields == expected


class TestBadgeTierInline:
    """Testy inline'a BadgeTier."""

    def test_badge_tier_inline_configuration(self):
        """Test konfiguracji inline'a."""
        from django.contrib.admin import AdminSite
        inline = BadgeTierInline(BadgeTierModel, AdminSite())
        assert inline.model.__name__ == "BadgeTierModel"
        assert inline.extra == 1

    def test_badge_tier_inline_fields(self):
        """Test pól inline'a."""
        expected_fields = ("name", "order", "required_peaks_count", "badge_image")
        assert BadgeTierInline.fields == expected_fields


class TestTouristRegionAdmin:
    """Testy admina TouristRegion."""

    def test_tourist_region_admin_inheritance(self):
        """Test dziedziczenia TouristRegionAdmin."""
        assert issubclass(TouristRegionAdmin, ReadOnlyMapAdmin)

    def test_tourist_region_admin_list_display(self):
        """Test pól list_display."""
        expected = ("name", "code")
        assert TouristRegionAdmin.list_display == expected

    def test_tourist_region_admin_search_fields(self):
        """Test pól search_fields."""
        expected = ("name", "code")
        assert TouristRegionAdmin.search_fields == expected

    def test_tourist_region_admin_filter_horizontal(self):
        """Test pól filter_horizontal."""
        expected = ("provinces", "subprovinces", "macroregions", "mesoregions")
        assert TouristRegionAdmin.filter_horizontal == expected

    def test_tourist_region_admin_actions(self):
        """Test akcji admina."""
        expected_actions = ["rebuild_geometry"]
        assert TouristRegionAdmin.actions == expected_actions
