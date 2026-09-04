"""Waliduje Manifest Snapshotu danych referencyjnych (ADR-020, ADR-023).

Weryfikuje:
- Poprawność struktury JSON i obecność wymaganych pól.
- Pole `compatible_schema` zgadza się z oczekiwaną wersją schematu.
- Wszystkie pliki wymienione w `files` fizycznie istnieją.
- Sumy kontrolne SHA-256 zawartości plików zgadzają się z zapisanymi w
  manifeście (`checksums`).
"""

import gzip
import hashlib
import json
from pathlib import Path

import jsonschema
from django.core.management.base import BaseCommand, CommandError

REFERENCE_DATA_SCHEMA_VERSION = "1.0"
REQUIRED_MANIFEST_FIELDS = {
    "snapshot_version": str,
    "description": str,
    "files": list,
    "statistics": dict,
    "compatible_schema": str,
}

# AUDYT-133: JSON Schema walidujący pola semantyczne w reference data.
_BADGE_VERSION_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "reference" / "schema" / "rule_schema.json"
)


class Command(BaseCommand):
    """Komenda do walidacji manifestu danych referencyjnych."""

    help = (
        "Walidacja Manifestu Snapshotu danych referencyjnych "
        "(sha256 zawartości plików + pole compatible_schema). "
        "Kod wyjścia 0 = OK, 1 = błąd walidacji."
    )

    def add_arguments(self, parser):
        """

        Args:
          parser:

        Returns:

        """
        parser.add_argument(
            "--snapshot",
            default=None,
            help=(
                "Opcjonalny identyfikator snapshotu (zarezerwowane na przyszłe użycie — "
                "obecnie walidowany jest zawsze aktualny manifest)."
            ),
        )

    def handle(self, *args, **options):
        """

        Args:
          *args:
          **options:

        Returns:

        """
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
        self._validate_json_schema(manifest, data_dir)  # AUDYT-133

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Manifest jest poprawny (compatible_schema={manifest['compatible_schema']}, "
                f"{len(manifest['files'])} plików, checksums OK)."
            )
        )

    @staticmethod
    def _settings_base_dir() -> str:
        """Zwraca bazowy katalog ustawień."""
        from django.conf import settings

        return str(settings.BASE_DIR)

    @staticmethod
    def _load_json(path: Path) -> dict:
        """

        Args:
          path: Path:
          path: Path:

        Returns:

        """
        with open(path, encoding="utf-8") as f:
            return json.load(f)  # type: ignore[no-any-return]

    def _validate_structure(self, manifest: dict, manifest_path: Path) -> None:
        """

        Args:
          manifest: dict:
          manifest_path: Path:
          manifest: dict:
          manifest_path: Path:

        Returns:

        """
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
        """

        Args:
          manifest: dict:
          manifest: dict:

        Returns:

        """
        compatible = manifest.get("compatible_schema")
        if compatible != REFERENCE_DATA_SCHEMA_VERSION:
            raise CommandError(
                f"Niekompatybilny schemat manifestu: compatible_schema={compatible!r}, "
                f"oczekiwano {REFERENCE_DATA_SCHEMA_VERSION!r}. "
                "Zaktualizuj dane referencyjne za pomocą `export_reference_data`."
            )

    def _validate_files_exist(self, manifest: dict, data_dir: Path) -> None:
        """

        Args:
          manifest: dict:
          data_dir: Path:
          manifest: dict:
          data_dir: Path:

        Returns:

        """
        missing = [f for f in manifest["files"] if not (data_dir / f).exists()]
        if missing:
            raise CommandError(f"Brakujące pliki snapshotu wymienione w manifest: {', '.join(missing)}")

    def _validate_checksums(self, manifest: dict, data_dir: Path) -> None:
        """

        Args:
          manifest: dict:
          data_dir: Path:
          manifest: dict:
          data_dir: Path:

        Returns:

        """
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

    def _validate_json_schema(self, manifest: dict, data_dir: Path) -> None:
        """AUDYT-133: Walidacja semantyczna plików referencyjnych JSON Schema.

        Dla plików z ``badgeversionmodel`` sprawdza, że pole ``rules``
        jest niepustą listą słowników z kluczem ``type``. Zapobiega
        wgraniu pustych/niepoprawnych reguł, które unicestwią
        ``BadgeVersionDomain`` podczas hydracji.
        """
        try:
            with open(_BADGE_VERSION_SCHEMA_PATH, encoding="utf-8") as f:
                schema = json.load(f)
        except FileNotFoundError:
            self.stderr.write(
                self.style.WARNING(
                    f"Schema file not found ({_BADGE_VERSION_SCHEMA_PATH}); skipping JSON schema validation."
                )
            )
            return

        files_with_rules = [f for f in manifest["files"] if f.endswith("03_badges.json.gz")]
        errors: list[str] = []

        for filename in files_with_rules:
            file_path = data_dir / filename
            if not file_path.exists():
                continue
            entries = self._load_gzipped_json(file_path)
            badgevers = [e for e in entries if e.get("model") == "badges.badgeversionmodel"]

            for entry in badgevers:
                try:
                    rules = entry["fields"]["rules"]
                except (KeyError, TypeError):
                    errors.append(f"{filename} pk={entry.get('pk')}: brak pola rules")
                    continue
                try:
                    jsonschema.validate(rules, schema)
                except jsonschema.ValidationError as exc:
                    errors.append(f"{filename} pk={entry['pk']}: reguły nie przechodzą JSON Schema — {exc.message}")

        if errors:
            raise CommandError("Błędy walidacji JSON Schema:\n" + "\n".join(f"  - {e}" for e in errors))

    @staticmethod
    def _load_gzipped_json(file_path: Path) -> list[dict]:
        """Wczytuje skompresowany JSON (.json.gz) jako listę słowników (loaddata format)."""
        with gzip.open(file_path, "rt", encoding="utf-8") as f:
            return json.load(f)  # type: ignore[no-any-return]

    @staticmethod
    def _sha256(file_path: Path) -> str:
        """

        Args:
          file_path: Path:
          file_path: Path:

        Returns:

        """
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
