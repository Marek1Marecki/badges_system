"""Jednorazowy skrypt do pre-kalkulacji sąsiadów geograficznych.

Realizuje Opcję 3 z analizy architektonicznej: zamiast liczyć ST_Distance w locie, wylicza to raz i zapisuje jako twardą
relację M2M w bazie danych.
"""

from django.contrib.gis.measure import D
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.badges.models import (
    CountryModel,
    MacroregionModel,
    MesoregionModel,
    ProvinceModel,
    SubprovinceModel,
    TouristRegionModel,
    VoivodeshipModel,
)


class Command(BaseCommand):
    """"""

    help = "Przelicza i zapisuje sąsiadów (z tolerancją 50m) dla wszystkich regionów."

    def handle(self, *args, **options):
        """

        Args:
          *args:
          **options:

        Returns:

        """
        # Lista modeli do przeliczenia
        models_to_process = [
            CountryModel,
            VoivodeshipModel,
            ProvinceModel,
            SubprovinceModel,
            MacroregionModel,
            MesoregionModel,
            TouristRegionModel,
        ]

        for Model in models_to_process:
            self.stdout.write(f"\nRozpoczynam analizę dla {Model.__name__}...")

            all_objects = list(Model.objects.all())
            if not all_objects:
                self.stdout.write(self.style.WARNING("  Brak obiektów. Pomijam."))
                continue

            with transaction.atomic():
                for obj in all_objects:
                    if not obj.shape:
                        continue

                    # Baza szuka fizycznych sąsiadów w promieniu 50m (pomijając samego siebie)
                    neighbors_qs = Model.objects.filter(shape__distance_lte=(obj.shape, D(m=50))).exclude(id=obj.id)

                    # Nadpisujemy relację M2M w bazie danych
                    obj.neighbors.set(neighbors_qs)

            self.stdout.write(self.style.SUCCESS(f"  Zakończono! Zaktualizowano {len(all_objects)} obiektów."))

        self.stdout.write(self.style.SUCCESS("\nPre-kalkulacja sąsiadów zakończona pomyślnie!"))
