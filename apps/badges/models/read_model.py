"""Modele denormalizowanego Read Modelu (CQRS).

Zawiera ``ObjectRegionCache`` — płaską tabelę odczytu łączącą
punkt (``TouristObject``) z regionami na podstawie ST_DWithin.
"""

from django.db import models

from apps.badges.models.osm import TouristObject
from apps.badges.models.region import RegionFlatModel, RegionLevel


class ObjectRegionCache(models.Model):
    """Płaska tabela odczytu (CQRS Read Model) wypełniana asynchronicznie przez Celery.

    Łączy punkt (TouristObject) z dowolnym z 6 typów regionów na podstawie ST_DWithin.
    Zamiast 6 tabel M2M, mamy jedną, błyskawiczną w odczytywaniu.

    Args:

    Returns:
    """

    tourist_object = models.ForeignKey(TouristObject, on_delete=models.CASCADE, related_name="cached_regions")

    # Przechowujemy typ poziomu (np. COUNTRY) i FK do RegionFlatModel
    region_level = models.CharField(max_length=20, choices=RegionLevel.choices)
    region = models.ForeignKey(
        RegionFlatModel,
        on_delete=models.CASCADE,
        related_name="cached_objects",
        db_column="region_id",
        help_text="Region z regions_flat (ADR-028).",
    )
    region_name = models.CharField(
        max_length=100,
        help_text="Zdenormalizowana nazwa regionu do błyskawicznego wyświetlenia (np. w panelu).",
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
        unique_together = ("tourist_object", "region_level", "region")
        # Indeksy potężnie przyspieszające odczyt CQRS dla paneli analitycznych
        indexes = [
            models.Index(fields=["tourist_object", "region_level"]),
            models.Index(fields=["region_level", "region"]),
        ]

    def __str__(self) -> str:
        """Reprezentacja tekstowa cache regionu."""
        dist_str = f" (Bufor {self.distance_meters}m)" if self.distance_meters > 0 else ""
        return f"{self.tourist_object.name} -> {self.region_name} [{self.get_region_level_display()}]{dist_str}"
