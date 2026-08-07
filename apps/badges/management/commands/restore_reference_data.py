"""Odtwarza dane referencyjne systemu z Snapshotu (Single Source of Truth)."""

import json
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Odtwarza autorytatywny stan systemu PTTK z plików Snapshotu i weryfikuje Manifest."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Symuluje proces odtwarzania sprawdzając poprawność plików Manifestu, bez modyfikacji bazy danych.",
        )

    def handle(self, *args, **options):
        is_dry_run = options["dry_run"]
        data_dir = Path(settings.BASE_DIR) / "data" / "reference"

        if is_dry_run:
            self.stdout.write(self.style.WARNING("=== TRYB DRY RUN (Symulacja Przywracania) ==="))

        if not data_dir.exists():
            self.stdout.write(self.style.ERROR(f"Katalog {data_dir} nie istnieje!"))
            return

        # 1. ODCZYT MANIFESTU
        manifest_path = data_dir / "manifest.json"
        files_to_load = []

        if manifest_path.exists():
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
                files_to_load = manifest.get("files", [])

            self.stdout.write(self.style.WARNING(f"Znaleziono Snapshot z dnia: {manifest.get('snapshot_version')}"))
            self.stdout.write(
                self.style.SUCCESS(f"Statystyki z Manifestu: {json.dumps(manifest.get('statistics', {}), indent=2)}")
            )
        else:
            self.stdout.write(self.style.ERROR("Brak pliku manifest.json! Używam domyślnej listy plików."))
            files_to_load = [
                "01_regions.json.gz",
                "02_tourist_objects.json.gz",
                "03_badges.json.gz",
                "04_osm_mappings.json.gz",
                "05_badge_news.json.gz",
            ]

        self.stdout.write(self.style.WARNING("\nPliki gotowe do załadowania:"))
        for filename in files_to_load:
            file_path = data_dir / filename
            if file_path.exists():
                self.stdout.write(self.style.SUCCESS(f" [OK] {filename}"))
            else:
                self.stdout.write(self.style.ERROR(f" [BRAK] {filename}"))

        if is_dry_run:
            self.stdout.write(
                self.style.SUCCESS("\n✅ Symulacja zakończona. Baza danych PostGIS nie została naruszona.")
            )
            return

        self.stdout.write(self.style.WARNING("\nRozpoczynam Przywracanie Systemu (Restore)..."))

        # 2. ODTWARZANIE W JEDNEJ TRANSAKCJI
        with transaction.atomic():
            for filename in files_to_load:
                file_path = data_dir / filename
                if not file_path.exists():
                    self.stdout.write(self.style.ERROR(f"KRYTYCZNY BŁĄD: Brakuje pliku z manifestu: {filename}"))
                    raise FileNotFoundError(f"Przerwano transakcję. Brak pliku: {filename}")

                if filename.endswith(".json.gz") or filename.endswith(".json"):
                    self.stdout.write(f"Wczytywanie {filename}...")
                    call_command("loaddata", str(file_path))
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Pominięto {filename} (nie jest fixture'em Django — ładuj przez pg_restore)."
                        )
                    )

        self.stdout.write(self.style.SUCCESS("\n✅ Wgrano dane słownikowe PTTK."))

        # 3. ODBUDOWA STRUKTUR
        self.stdout.write(self.style.WARNING("\nRozpoczynam odbudowę struktur GIS (Cache & M2M)..."))

        try:
            call_command("calculate_neighbors")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Błąd przeliczania sąsiadów: {e}"))

        # 4. Przeliczamy przynależność obiektów do regionów (CQRS)
        from apps.badges.models import TouristObject
        from bootstrap import get_container

        try:
            use_case = get_container().calculate_object_regions
            object_ids = list(TouristObject.objects.values_list("id", flat=True))
            total_objects = len(object_ids)

            self.stdout.write(
                self.style.WARNING(
                    f"Rozpoczynamy przeliczanie przestrzenne CQRS dla {total_objects} "
                    f"obiektów (To może potrwać kilka minut)..."
                )
            )

            for index, obj_id in enumerate(object_ids, 1):
                use_case.execute(object_id=obj_id)
                # Drukujemy log co 50 obiektów, żeby pokazać, że skrypt nie wisi!
                if index % 50 == 0 or index == total_objects:
                    self.stdout.write(f"  ...przetworzono {index}/{total_objects} szczytów")

            self.stdout.write(self.style.SUCCESS(f"✅ Odbudowano tabelę CQRS dla {total_objects} obiektów."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Błąd przeliczania CQRS: {e}"))

        self.stdout.write(self.style.SUCCESS("\n🎉 Odtwarzanie Snapshotu zakończone sukcesem!"))
