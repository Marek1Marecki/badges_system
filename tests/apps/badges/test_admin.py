"""Testy dla konfiguracji Django Admin."""


from leaflet.admin import LeafletGeoAdmin

from apps.badges.admin import (
    BadgeAdmin,
    BadgeVersionAdmin,
    CountryAdmin,
    MacroregionAdmin,
    MesoregionAdmin,
    ProvinceAdmin,
    ReadOnlyMapAdmin,
    SubprovinceAdmin,
    VoivodeshipAdmin,
)
from apps.badges.models import (
    BadgeModel,
    BadgeVersionModel,
    CountryModel,
    MacroregionModel,
    MesoregionModel,
    ProvinceModel,
    SubprovinceModel,
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
        expected = ("name", "code", "organizer")
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
