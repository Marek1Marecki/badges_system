"""Modele geograficznych regionów i hierarchii administracyjnych.

Zawiera modele bazowe oraz konkretne modele regionów (kraj, województwo,
itd.) oraz słownik poziomów regionów dla CQRS Read Model.
"""

from django.contrib.gis.db import models as gis_models


class RegionBaseModel(gis_models.Model):
    """Abstrakcyjny model bazowy dla wszystkich regionów geograficznych."""

    name = gis_models.CharField(max_length=100, verbose_name="Nazwa")
    translation = gis_models.CharField(max_length=100, verbose_name="Tłumaczenie")
    code = gis_models.CharField(max_length=10, verbose_name="Kod")
    link = gis_models.CharField(max_length=200, verbose_name="Link (Wiki)")
    shape = gis_models.MultiPolygonField(srid=4326, null=True, blank=True, verbose_name="Kształt")

    created_at = gis_models.DateTimeField(auto_now_add=True)
    updated_at = gis_models.DateTimeField(auto_now=True)

    class Meta:
        """Konfiguracja modelu RegionBaseModel."""

        abstract = True

    def __str__(self) -> str:
        """Reprezentacja tekstowa regionu: nazwa i kod."""
        return f"{self.name} ({self.code})"


class PhysicalRegionMixin(gis_models.Model):
    """Domieszka (Mixin) dodająca relacje sąsiedztwa dla fizycznych obiektów GIS."""

    neighbors = gis_models.ManyToManyField("self", blank=True, verbose_name="Sąsiedzi")

    class Meta:
        """Konfiguracja PhysicalRegionMixin."""

        abstract = True


class CountryModel(RegionBaseModel, PhysicalRegionMixin):
    """Model państwa."""

    order = gis_models.IntegerField(default=0)

    class Meta:
        """Konfiguracja modelu CountryModel."""

        db_table = "odznaki_country"
        verbose_name = "Państwo"
        verbose_name_plural = "Państwa"


class VoivodeshipModel(RegionBaseModel, PhysicalRegionMixin):
    """Model województwa (tylko dla Polski)."""

    country = gis_models.ForeignKey(CountryModel, on_delete=gis_models.CASCADE)

    class Meta:
        """Konfiguracja modelu VoivodeshipModel."""

        db_table = "odznaki_voivodeship"
        unique_together = [("country", "code"), ("country", "name")]
        verbose_name = "Województwo"
        verbose_name_plural = "Województwa"


class ProvinceModel(RegionBaseModel, PhysicalRegionMixin):
    """Model prowincji fizykogeograficznej."""

    country = gis_models.ForeignKey(CountryModel, on_delete=gis_models.CASCADE)

    class Meta:
        """Konfiguracja modelu ProvinceModel."""

        db_table = "odznaki_province"
        unique_together = [("country", "code")]
        verbose_name = "Prowincja"
        verbose_name_plural = "Prowincje"


class SubprovinceModel(RegionBaseModel, PhysicalRegionMixin):
    """Model podprowincji fizykogeograficznej."""

    province = gis_models.ForeignKey(ProvinceModel, on_delete=gis_models.CASCADE)

    class Meta:
        """Konfiguracja modelu SubprovinceModel."""

        db_table = "odznaki_subprovince"
        unique_together = [("province", "code")]
        verbose_name = "Podprowincja"
        verbose_name_plural = "Podprowincje"


class MacroregionModel(RegionBaseModel, PhysicalRegionMixin):
    """Model makroregionu."""

    subprovince = gis_models.ForeignKey(SubprovinceModel, on_delete=gis_models.CASCADE, null=True, blank=True)

    class Meta:
        """Konfiguracja modelu MacroregionModel."""

        db_table = "odznaki_macroregion"
        verbose_name = "Makroregion"
        verbose_name_plural = "Makroregiony"


class MesoregionModel(RegionBaseModel, PhysicalRegionMixin):
    """Model mezoregionu."""

    macroregion = gis_models.ForeignKey(MacroregionModel, on_delete=gis_models.CASCADE, null=True, blank=True)

    class Meta:
        """Konfiguracja modelu MesoregionModel."""

        db_table = "odznaki_mesoregion"
        verbose_name = "Mezoregion"
        verbose_name_plural = "Mezoregiony"


class TouristRegionModel(RegionBaseModel):
    """Region turystyczny budowany agregacyjnie z mniejszych jednostek (Write Model)."""

    provinces = gis_models.ManyToManyField(ProvinceModel, blank=True, verbose_name="Prowincje")
    subprovinces = gis_models.ManyToManyField(SubprovinceModel, blank=True, verbose_name="Podprowincje")
    macroregions = gis_models.ManyToManyField(MacroregionModel, blank=True, verbose_name="Makroregiony")
    mesoregions = gis_models.ManyToManyField(MesoregionModel, blank=True, verbose_name="Mezoregiony")

    class Meta:
        """Konfiguracja modelu TouristRegionModel."""

        db_table = "odznaki_tourist_region"
        verbose_name = "Region Turystyczny"
        verbose_name_plural = "Regiony Turystyczne"
