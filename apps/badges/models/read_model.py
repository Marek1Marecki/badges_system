"""Modele denormalizowanego Read Modelu (CQRS).

Zawiera ``ObjectRegionCache`` — płaską tabelę odczytu łączącą
punkt (``TouristObject``) z regionami na podstawie ST_DWithin,
oraz ``RegionLevelType`` — słownik poziomów regionów.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.badges.models.osm import TouristObject


class RegionLevelType(models.TextChoices):
    """Poziomy słownika geograficznego do filtrowania w CQRS."""

    COUNTRY = "COUNTRY", _("Państwo")
    VOIVODESHIP = "VOIVODESHIP", _("Województwo")
    PROVINCE = "PROVINCE", _("Prowincja")
    SUBPROVINCE = "SUBPROVINCE", _("Podprowincja")
    MACROREGION = "MACROREGION", _("Makroregion")
    MESOREGION = "MESOREGION", _("Mezoregion")
    TOURIST_REGION = "TOURIST_REGION", _("Region Turystyczny")


class ObjectRegionCache(models.Model):
    """Płaska tabela odczytu (CQRS Read Model) wypełniana asynchronicznie przez Celery.

    Łączy punkt (TouristObject) z dowolnym z 6 typów regionów na podstawie ST_DWithin.
    Zamiast 6 tabel M2M, mamy jedną, błyskawiczną w odpytywaniu.

    Args:

    Returns:
    """

    tourist_object = models.ForeignKey(TouristObject, on_delete=models.CASCADE, related_name="cached_regions")

    # Przechowujemy typ poziomu (np. COUNTRY) i fizyczne ID wiersza z
    # odpowiedniej tabeli (np. ID Polski z CountryModel)
    region_level = models.CharField(max_length=20, choices=RegionLevelType.choices)
    region_id = models.BigIntegerField(help_text="ID wiersza z tabeli odpowiadającej poziomowi region_level.")
    region_name = models.CharField(
        max_length=100,
        help_text="Zdenormalizowana nazwa regionu do błyskawicznego wyświetlania (np. w panelu).",
    )

    # 0.0 oznacza, że obiekt leży ściśle wewnątrz poligonu (ST_Intersects)
    # Wartość > 0.0 oznacza bufor przygraniczny (ST_DWithin)
    distance_meters = models.FloatField(
        default=0.0, help_text="Odległość od krawędzi regionu w metrach (0.0 = wewnątrz)."
    )

    class Meta:
        """Konfiguracja modelu ObjectRegionCache."""

        db_table = "odznaki_object_region_cache"
        # Uniemożliwiamy zduplikowanie przypisania tego samego regionu do obiektu
        unique_together = ("tourist_object", "region_level", "region_id")
        # Indeksy potężnie przyspieszające odczyt CQRS dla paneli analitycznych
        indexes = [
            models.Index(fields=["tourist_object", "region_level"]),
            models.Index(fields=["region_level", "region_id"]),
        ]

    def __str__(self) -> str:
        """Reprezentacja tekstowa cache regionu."""
        dist_str = f" (Bufor {self.distance_meters}m)" if self.distance_meters > 0 else ""
        return f"{self.tourist_object.name} -> {self.region_name} [{self.get_region_level_display()}]{dist_str}"
