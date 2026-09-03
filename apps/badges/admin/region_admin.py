"""Panele administracyjne dla modeli geograficznych regionów."""

from django.contrib import admin
from leaflet.admin import LeafletGeoAdminMixin
from unfold.admin import ModelAdmin

from apps.badges.models import (
    CountryModel,
    MacroregionModel,
    MesoregionModel,
    ProvinceModel,
    SubprovinceModel,
    TouristRegionModel,
    VoivodeshipModel,
)
from apps.badges.tasks import build_region_geometries_bulk_task, build_tourist_region_geometry_task


class ReadOnlyMapAdmin(LeafletGeoAdminMixin, ModelAdmin):
    """Bazowa klasa admina pokazująca kształty GIS tylko do odczytu."""

    modifiable = False
    settings_overrides = {
        "DEFAULT_CENTER": (52.0, 19.0),
        "DEFAULT_ZOOM": 5,
    }


@admin.register(CountryModel)
class CountryAdmin(ReadOnlyMapAdmin):
    """Panel administracyjny dla państw."""

    list_display = ("name", "code", "order")


@admin.register(VoivodeshipModel)
class VoivodeshipAdmin(ReadOnlyMapAdmin):
    """Panel administracyjny dla województw."""

    list_display = ("name", "code", "country")
    list_filter = ("country",)


@admin.register(ProvinceModel)
class ProvinceAdmin(ReadOnlyMapAdmin):
    """Panel administracyjny dla prowincji fizykogeograficznych."""

    list_display = ("name", "code", "country")


@admin.register(SubprovinceModel)
class SubprovinceAdmin(ReadOnlyMapAdmin):
    """Panel administracyjny dla podprowincji fizykogeograficznych."""

    list_display = ("name", "code", "province")


@admin.register(MacroregionModel)
class MacroregionAdmin(ReadOnlyMapAdmin):
    """Panel administracyjny dla makroregionów."""

    list_display = ("name", "code", "subprovince")
    search_fields = ("name", "code")


@admin.register(MesoregionModel)
class MesoregionAdmin(ReadOnlyMapAdmin):
    """Panel administratory dla mezoregionów."""

    list_display = ("name", "code", "macroregion")
    search_fields = ("name", "code")


@admin.register(TouristRegionModel)
class TouristRegionAdmin(ReadOnlyMapAdmin):
    """Panel do budowy nadrzędnych Regionów Turystycznych (np.

    Sudety).
    """

    list_display = ("name", "code")
    search_fields = ("name", "code")

    # 4 potężne okienka do wybierania elementów składowych
    filter_horizontal = ("provinces", "subprovinces", "macroregions", "mesoregions")

    actions = ["rebuild_geometry"]

    def save_related(self, request, form, formsets, change):
        """Nadpisujemy save_related, a nie save_model.

        Dlaczego? Bo w Django relacje M2M (nasze filter_horizontal)
        są zapisywane DOPIERO PO zapisaniu samego modelu.
        Musimy wywołać Celery po zapisie M2M!

        Args:
          request:
          form:
          formsets:
          change:

        Returns:
        """
        super().save_related(request, form, formsets, change)
        from django.db import transaction

        transaction.on_commit(lambda: build_tourist_region_geometry_task.delay(form.instance.id))

    @admin.action(description="[Celery] Przebuduj geometrię i zaktualizuj szczyty (CQRS)")
    def rebuild_geometry(self, request, queryset):
        """Opcja ręcznego przeliczenia na żądanie — batch task (AUDYT-073)."""
        region_ids = list(queryset.values_list("id", flat=True))
        build_region_geometries_bulk_task.delay(region_ids)
        self.message_user(request, f"Wysłano {len(region_ids)} regionów do Celery.")
