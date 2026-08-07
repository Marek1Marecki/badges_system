"""Tworzy Snapshot (zrzut) danych referencyjnych z bazy do zarchiwizowanych plików."""

import gzip
import hashlib
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from badges.reference_data.constants import REFERENCE_DATA_SCHEMA_VERSION
from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Eksportuje cały Snapshot systemu PTTK (obiekty, odznaki, regiony) oraz generuje Manifest."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Symuluje eksport wyświetlając statystyki, bez faktycznego tworzenia plików.",
        )
        parser.add_argument(
            "--with-pg-dump",
            action="store_true",
            help="Dodatkowo tworzy binarny dump PostgreSQL (pg_dump -Fc) do szybkiego restore w E2E.",
        )

    def _compress_file(self, file_path: Path) -> Path:
        """Kompresuje plik JSON do GZIP i usuwa oryginał."""
        gz_path = file_path.with_suffix(".json.gz")
        with open(file_path, "rb") as f_in:
            with gzip.open(gz_path, "wb", compresslevel=9) as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(file_path)
        return gz_path

    @staticmethod
    def _sha256(file_path: Path) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def _get_model_count(self, app_label: str, model_name: str) -> int:
        """Pobiera ilość rekordów w tabeli."""
        model = apps.get_model(app_label, model_name)
        return int(model.objects.count())

    def handle(self, *args, **options):
        is_dry_run = options["dry_run"]
        output_dir = Path(settings.BASE_DIR) / "data" / "reference"

        if is_dry_run:
            self.stdout.write(self.style.WARNING("=== TRYB DRY RUN (Symulacja Eksportu) ==="))

        self.stdout.write(self.style.WARNING("Zbieranie statystyk bazy danych..."))

        # Statystyki do Manifestu (liczone przed zrzutem)
        region_models = [
            "CountryModel",
            "VoivodeshipModel",
            "ProvinceModel",
            "SubprovinceModel",
            "MacroregionModel",
            "MesoregionModel",
            "TouristRegionModel",
        ]

        stats = {
            "regions": sum(self._get_model_count("badges", model) for model in region_models),
            "tourist_objects": self._get_model_count("badges", "TouristObject"),
            "badges": self._get_model_count("badges", "BadgeModel"),
            "badge_versions": self._get_model_count("badges", "BadgeVersionModel"),
            "osm_mappings": self._get_model_count("badges", "OsmTypeMapping"),
            "badge_news": self._get_model_count("badges", "BadgeNewsItem"),
        }

        self.stdout.write(self.style.SUCCESS(f"Obecny stan bazy: {json.dumps(stats, indent=2)}"))

        if is_dry_run:
            self.stdout.write(self.style.SUCCESS("\n✅ Symulacja zakończona. Żadne pliki nie zostały nadpisane."))
            return

        # Właściwy Export
        output_dir.mkdir(parents=True, exist_ok=True)
        self.stdout.write(self.style.WARNING("\nRozpoczynam tworzenie plików (Eksport)..."))

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
        self.stdout.write(self.style.SUCCESS(f"✅ Regiony -> {gz_regions.name}"))

        # 2. Baza Obiektów PTTK
        objects_file = output_dir / "02_tourist_objects.json"
        call_command("dumpdata", "badges.TouristObject", indent=2, output=str(objects_file))
        gz_objects = self._compress_file(objects_file)
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
        self.stdout.write(self.style.SUCCESS(f"✅ Regulaminy -> {gz_badges.name}"))

        # 4. Słowniki konfiguracyjne systemu (Mapowania OSM)
        osm_mappings_file = output_dir / "04_osm_mappings.json"
        call_command("dumpdata", "badges.OsmTypeMapping", indent=2, output=str(osm_mappings_file))
        gz_mappings = self._compress_file(osm_mappings_file)
        self.stdout.write(self.style.SUCCESS(f"✅ Mapowania OSM -> {gz_mappings.name}"))

        # 5. Archiwum Aktualności
        news_file = output_dir / "05_badge_news.json"
        call_command("dumpdata", "badges.BadgeNewsItem", indent=2, output=str(news_file))
        gz_news = self._compress_file(news_file)
        self.stdout.write(self.style.SUCCESS(f"✅ Archiwum Aktualności -> {gz_news.name}"))

        # --- GENEROWANIE MANIFESTU ---
        gz_files = [gz_regions.name, gz_objects.name, gz_badges.name, gz_mappings.name, gz_news.name]
        checksums = {name: self._sha256(output_dir / name) for name in gz_files}

        snapshot_version = datetime.now(UTC).strftime("%Y-%m-%d")  # noqa: TID251

        manifest_data = {
            "snapshot_version": snapshot_version,
            "description": "Pełny, spójny Snapshot Systemu Referencyjnego PTTK",
            "compatible_schema": REFERENCE_DATA_SCHEMA_VERSION,
            "files": gz_files,
            "checksums": checksums,
            "statistics": stats,
        }

        manifest_path = output_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=4)

        self.stdout.write(self.style.SUCCESS(f"\n🎉 Snapshot zakończony. Utworzono {manifest_path.name}!"))

        if options.get("with_pg_dump"):
            self._create_pg_dump(output_dir)

    def _create_pg_dump(self, output_dir: Path) -> None:
        db = settings.DATABASES["default"]
        dump_path = output_dir / "postgis_dump.custom"
        env = os.environ.copy()
        env["PGPASSWORD"] = db.get("PASSWORD", "")
        cmd = [
            "pg_dump",
            "-Fc",
            "-U",
            db.get("USER", "postgres"),
            "-h",
            db.get("HOST", "localhost"),
            "-p",
            str(db.get("PORT", 5432)),
            "-d",
            db.get("NAME", "postgres"),
            "-f",
            str(dump_path),
        ]
        self.stdout.write(self.style.WARNING(f"\nTworzę pg_dump: {' '.join(cmd)}"))
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)  # noqa: S603
        if result.returncode != 0:
            self.stderr.write(self.style.ERROR(f"pg_dump failed: {result.stderr}"))
            return
        self.stdout.write(self.style.SUCCESS(f"✅ PostgreSQL dump -> {dump_path.name}"))
