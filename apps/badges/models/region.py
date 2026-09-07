"""Modele geograficznych regionów i hierarchii administracyjnych.

Zawiera modele bazowe oraz konkretne modele regionów (kraj, województwo,
itd.) oraz słownik poziomów regionów dla CQRS Read Model.
"""

from django.contrib.gis.db import models as gis_models
from django.db import models


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


class RegionLevel(models.TextChoices):
    """Poziomy hierarchii w płaskim modelu RegionFlat (ADR-028)."""

    COUNTRY = "COUNTRY", "Państwo"
    VOIVODESHIP = "VOIVODESHIP", "Województwo"
    PROVINCE = "PROVINCE", "Prowincja"
    SUBPROVINCE = "SUBPROVINCE", "Podprowincja"
    MACROREGION = "MACROREGION", "Makroregion"
    MESOREGION = "MESOREGION", "Mezoregion"
    TOURIST_REGION = "TOURIST_REGION", "Region Turystyczny"


class LtreeField(models.TextField):
    """Custom Django field dla PostgreSQL `ltree`.

    ADR-028 — `path` przechowuje hierarchiczną ścieżkę (np.
    `pl.slaskie.karpacz`). Nie używamy zewnętrznej biblioteki
    (django-ltree); pole dziedziczy z `TextField` i rzutuje `db_type`.
    Operacje na `ltree` (<@, ~, ancestors) wykonywane są via raw SQL
    albo `extra()` w querysetach read-modelu.
    """

    def db_type(self, connection) -> str:
        """Zwraca typ bazy `ltree` — wymaga `CREATE EXTENSION ltree`."""
        return "ltree"


class RegionFlatModel(gis_models.Model):
    """Płaska tabela regionów ADR-028 — single-table hierarchy na bazie `ltree`.

    - `parent_id` (FK) = dla Django Admin (write/Command).
    - `path` (ltree) = dla odczytów (Query), indeks GiST.
    - `level` = ENUM (RegionLevel) — zastępuje 7 osbistnych tabel.

    Migracja jednorazowa (RunPython, ADR-024) mapuje istniejące 7 tabele
    (Country/Voivodeship/Province/Subprovince/Macroregion/Mesoregion)
    do tej tabeli.
    """

    name = gis_models.CharField(max_length=100, verbose_name="Nazwa")
    translation = gis_models.CharField(max_length=100, verbose_name="Tłumaczenie", blank=True)
    code = gis_models.CharField(max_length=10, verbose_name="Kod")
    link = gis_models.CharField(max_length=200, blank=True, verbose_name="Link (Wiki)")
    shape = gis_models.MultiPolygonField(srid=4326, null=True, blank=True, verbose_name="Kształt")
    level = gis_models.CharField(max_length=20, choices=RegionLevel.choices)
    parent = gis_models.ForeignKey(
        "self",
        on_delete=gis_models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Rodzic",
    )
    path = LtreeField(verbose_name="Ścieżka ltree", db_index=True)

    created_at = gis_models.DateTimeField(auto_now_add=True)
    updated_at = gis_models.DateTimeField(auto_now=True)

    neighbors = gis_models.ManyToManyField("self", blank=True, verbose_name="Sąsiedzi")

    class Meta:
        """Konfiguracja modelu RegionFlatModel."""

        db_table = "regions_flat"
        verbose_name = "Region (Flat)"
        verbose_name_plural = "Regiony (Flat)"
        constraints = [
            models.UniqueConstraint(fields=["level", "code"], name="uq_regions_flat_level_code"),
        ]

    def __str__(self) -> str:
        """Reprezentacja tekstowa: nazwa (kod)."""
        return f"{self.name} ({self.code})"
