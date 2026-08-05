"""Waliduje Manifest Snapshotu danych referencyjnych (ADR-020, ADR-023).

Weryfikuje:
- Poprawność struktury JSON i obecność wymaganych pól.
- Pole `compatible_schema` zgadza się z oczekiwaną wersją schematu.
- Wszystkie pliki wymienione w `files` fizycznie istnieją.
- Sumy kontrolne SHA-256 zawartości plików zgadzają się z zapisanymi w
  manifeście (`checksums`).
"""

import hashlib
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

REFERENCE_DATA_SCHEMA_VERSION = "1.0"
REQUIRED_MANIFEST_FIELDS = {
    "snapshot_version": str,
    "description": str,
    "files": list,
    "statistics": dict,
    "compatible_schema": str,
}


class Command(BaseCommand):
    help = (
        "Walidacja Manifestu Snapshotu danych referencyjnych "
        "(sha256 zawartości plików + pole compatible_schema). "
        "Kod wyjścia 0 = OK, 1 = błąd walidacji."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--snapshot",
            default=None,
            help=(
                "Opcjonalny identyfikator snapshotu (zarezerwowane na przyszłe użycie — "
                "obecnie walidowany jest zawsze aktualny manifest)."
            ),
        )

    def handle(self, *args, **options):
        data_dir = Path(self._settings_base_dir()) / "data" / "reference"
        manifest_path = data_dir / "manifest.json"

        if not manifest_path.exists():
            raise CommandError(f"Brak pliku manifest.json w {data_dir}")

        try:
            manifest = self._load_json(manifest_path)
        except (json.JSONDecodeError, ValueError) as exc:
            raise CommandError(f"manifest.json nie jest poprawnym JSON: {exc}") from exc

        self._validate_structure(manifest, manifest_path)
        self._validate_schema_version(manifest)
        self._validate_files_exist(manifest, data_dir)
        self._validate_checksums(manifest, data_dir)

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Manifest jest poprawny (compatible_schema={manifest['compatible_schema']}, "
                f"{len(manifest['files'])} plików, checksums OK)."
            )
        )

    @staticmethod
    def _settings_base_dir() -> str:
        from django.conf import settings

        return str(settings.BASE_DIR)

    @staticmethod
    def _load_json(path: Path) -> dict:
        with open(path, encoding="utf-8") as f:
            return json.load(f)  # type: ignore[no-any-return]

    def _validate_structure(self, manifest: dict, manifest_path: Path) -> None:
        missing = [
            field
            for field, expected_type in REQUIRED_MANIFEST_FIELDS.items()
            if field not in manifest or not isinstance(manifest[field], expected_type)
        ]
        if missing:
            raise CommandError(
                f"Manifest {manifest_path} nie zawiera wymaganych pól lub ma błędny typ: {', '.join(missing)}"
            )

        files = manifest["files"]
        if not files:
            raise CommandError("Pole 'files' w manifest jest puste — snapshot musi zawierać co najmniej jeden plik.")

    def _validate_schema_version(self, manifest: dict) -> None:
        compatible = manifest.get("compatible_schema")
        if compatible != REFERENCE_DATA_SCHEMA_VERSION:
            raise CommandError(
                f"Niekompatybilny schemat manifestu: compatible_schema={compatible!r}, "
                f"oczekiwano {REFERENCE_DATA_SCHEMA_VERSION!r}. "
                "Zaktualizuj dane referencyjne za pomocą `export_reference_data`."
            )

    def _validate_files_exist(self, manifest: dict, data_dir: Path) -> None:
        missing = [f for f in manifest["files"] if not (data_dir / f).exists()]
        if missing:
            raise CommandError(f"Brakujące pliki snapshotu wymienione w manifest: {', '.join(missing)}")

    def _validate_checksums(self, manifest: dict, data_dir: Path) -> None:
        checksums = manifest.get("checksums")
        if not checksums:
            raise CommandError(
                "Manifest nie zawiera pola 'checksums' (dict filename->sha256). "
                "Wyeksportuj snapshot ponownie za pomocą `export_reference_data`."
            )

        if not isinstance(checksums, dict):
            raise CommandError("Pole 'checksums' w manifest musi być słownikiem (filename -> sha256).")

        errors = []
        for filename in manifest["files"]:
            expected = checksums.get(filename)
            if expected is None:
                errors.append(f"{filename}: brak checksum w manifest")
                continue

            file_path = data_dir / filename
            actual = self._sha256(file_path)
            if actual != expected:
                errors.append(
                    f"{filename}: checksum mismatch (oczekiwano {expected[:16]}..., otrzymano {actual[:16]}...)"
                )

        if errors:
            raise CommandError("Błąd walidacji sum kontrolnych:\n" + "\n".join(f"  - {e}" for e in errors))

    @staticmethod
    def _sha256(file_path: Path) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
