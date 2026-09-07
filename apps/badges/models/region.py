"""Płaska struktura regionów ADR-028 — single-table hierarchy na bazie `ltree`.

Zastępuje 7 historycznych tabel (Country/Voivodeship/Province/Subprovince/
Macroregion/Mesoregion/TouristRegion). Dane zostały migrowane w migracjach
0004 (ETL) i 0005 (M2M neighbors).
"""

from django.contrib.gis.db import models as gis_models
from django.db import models


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
