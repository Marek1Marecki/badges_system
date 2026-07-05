"""Tworzy Snapshot (zrzut) danych referencyjnych z bazy do zarchiwizowanych plików."""

import gzip
import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Eksportuje cały Snapshot systemu PTTK (obiekty, odznaki, regiony) oraz generuje Manifest."

    def _compress_file(self, file_path: Path) -> Path:
        """Kompresuje plik JSON do GZIP i usuwa oryginał."""
        gz_path = file_path.with_suffix(".json.gz")
        with open(file_path, "rb") as f_in:
            with gzip.open(gz_path, "wb", compresslevel=9) as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(file_path)
        return gz_path

    def _get_model_count(self, app_label: str, model_name: str) -> int:
        """Pobiera ilość rekordów w tabeli."""
        model = apps.get_model(app_label, model_name)
        return int(model.objects.count())

    def handle(self, *args, **options):
        output_dir = Path(settings.BASE_DIR) / "data" / "reference"
        output_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write(self.style.WARNING("Rozpoczynam tworzenie Snapshotu bazy referencyjnej..."))

        # Statystyki do Manifestu
        stats = {}

        # 1. Terytoria (GIS)
        regions_file = output_dir / "01_regions.json"
        call_command(
            "dumpdata",
            "badges.CountryModel",
            "badges.VoivodeshipModel",
            "badges.ProvinceModel",
            "badges.SubprovinceModel",
            "badges.MacroregionModel",
            "badges.MesoregionModel",
            "badges.TouristRegionModel",
            indent=2,
            output=str(regions_file),
        )
        gz_regions = self._compress_file(regions_file)
        stats["regions"] = self._get_model_count("badges", "MesoregionModel") + self._get_model_count(
            "badges", "MacroregionModel"
        )
        self.stdout.write(self.style.SUCCESS(f"✅ Regiony -> {gz_regions.name}"))

        # 2. Baza Obiektów PTTK
        objects_file = output_dir / "02_tourist_objects.json"
        call_command("dumpdata", "badges.TouristObject", indent=2, output=str(objects_file))
        gz_objects = self._compress_file(objects_file)
        stats["tourist_objects"] = self._get_model_count("badges", "TouristObject")
        self.stdout.write(self.style.SUCCESS(f"✅ Obiekty -> {gz_objects.name}"))

        # 3. System Odznak
        badges_file = output_dir / "03_badges.json"
        call_command(
            "dumpdata",
            "badges.OrganizerModel",
            "badges.BadgeModel",
            "badges.BadgeVersionModel",
            "badges.BadgeTierModel",
            indent=2,
            output=str(badges_file),
        )
        gz_badges = self._compress_file(badges_file)
        stats["badges"] = self._get_model_count("badges", "BadgeModel")
        stats["badge_versions"] = self._get_model_count("badges", "BadgeVersionModel")
        self.stdout.write(self.style.SUCCESS(f"✅ Regulaminy -> {gz_badges.name}"))

        # 4. Słowniki konfiguracyjne systemu (Mapowania OSM)
        osm_mappings_file = output_dir / "04_osm_mappings.json"
        call_command("dumpdata", "badges.OsmTypeMapping", indent=2, output=str(osm_mappings_file))
        gz_mappings = self._compress_file(osm_mappings_file)
        stats["osm_mappings"] = self._get_model_count("badges", "OsmTypeMapping")
        self.stdout.write(self.style.SUCCESS(f"✅ Mapowania OSM -> {gz_mappings.name}"))

        # 5. Archiwum Aktualności
        news_file = output_dir / "05_badge_news.json"
        call_command("dumpdata", "badges.BadgeNewsItem", indent=2, output=str(news_file))
        gz_news = self._compress_file(news_file)
        stats["badge_news"] = self._get_model_count("badges", "BadgeNewsItem")
        self.stdout.write(self.style.SUCCESS(f"✅ Archiwum Aktualności -> {gz_news.name}"))

        # --- GENEROWANIE MANIFESTU ---
        manifest_data = {
            "snapshot_version": datetime.now(UTC).isoformat(),  # noqa: TID251
            "description": "Pełny, spójny Snapshot Systemu Referencyjnego PTTK",
            "files": [gz_regions.name, gz_objects.name, gz_badges.name, gz_mappings.name, gz_news.name],
            "statistics": stats,
        }

        manifest_path = output_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=4)

        self.stdout.write(self.style.SUCCESS(f"\n🎉 Snapshot zakończony. Utworzono {manifest_path.name}!"))
