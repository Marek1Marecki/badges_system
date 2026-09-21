"""Testy dla komendy validate_reference_manifest (AUDYT-133)."""

import gzip
import json
from pathlib import Path

import pytest
from django.core.management.base import CommandError

from apps.badges.management.commands.validate_reference_manifest import Command


@pytest.fixture
def base_data_dir(tmp_path: Path) -> Path:
    """Minimalny katalog danych referencyjnych dla testu."""
    data_dir = tmp_path / "reference"
    data_dir.mkdir()
    manifest = {
        "snapshot_version": "2026-01-01T00:00:00Z",
        "description": "test",
        "compatible_schema": "1.0",
        "files": ["03_badges.json.gz"],
        "checksums": {},
        "statistics": {},
    }
    (data_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return data_dir


def _write_badge_versions(data_dir: Path, versions: list[dict]) -> None:
    """Pisze 03_badges.json.gz z listą badge versions."""
    payload = [
        {
            "model": "badges.badgeversionmodel",
            "pk": v["pk"],
            "fields": {
                "badge": 1,
                "version_code": "v1",
                "valid_from": "2020-01-01",
                "rules": v.get("rules", []),
                "pool_peaks": [1, 2],
            },
        }
        for v in versions
    ]
    with gzip.open(data_dir / "03_badges.json.gz", "wt", encoding="utf-8") as f:
        json.dump(payload, f)


class TestValidateJsonSchema:
    """AUDYT-133: walidacja JSON Schema dla pól 'rules'."""

    def test_passes_when_rules_valid(self, base_data_dir: Path) -> None:
        """Poprawne reguły — brak błędów walidacji (brak wyjątku)."""
        _write_badge_versions(base_data_dir, [{"pk": 1, "rules": [{"type": "MinAgeRule"}]}])
        cmd = Command()
        manifest = json.loads((base_data_dir / "manifest.json").read_text(encoding="utf-8"))
        # Should not raise
        cmd._validate_json_schema(manifest, base_data_dir)

    def test_allows_empty_rules_for_wildcard(self, base_data_dir: Path) -> None:
        """Puste rules — dopuszczalne dla badge'ów wildcard (pool_peaks, ADR-012)."""
        _write_badge_versions(base_data_dir, [{"pk": 1, "rules": []}])
        cmd = Command()
        manifest = json.loads((base_data_dir / "manifest.json").read_text(encoding="utf-8"))
        # Should not raise
        cmd._validate_json_schema(manifest, base_data_dir)

    def test_fails_when_rules_missing_type_key(self, base_data_dir: Path) -> None:
        """Rules bez klucza 'type' — ValidationError."""
        _write_badge_versions(base_data_dir, [{"pk": 1, "rules": [{"name": "no-type"}]}])
        cmd = Command()
        manifest = json.loads((base_data_dir / "manifest.json").read_text(encoding="utf-8"))
        with pytest.raises(CommandError) as exc_info:
            cmd._validate_json_schema(manifest, base_data_dir)
        assert "JSON Schema" in str(exc_info.value)


class TestValidateStructure:
    """Testy metody _validate_structure."""

    def test_valid_structure(self, base_data_dir: Path) -> None:
        """Poprawna struktura manifestu — brak wyjątku."""
        _write_badge_versions(base_data_dir, [{"pk": 1, "rules": [{"type": "MinAgeRule"}]}])
        cmd = Command()
        manifest = json.loads((base_data_dir / "manifest.json").read_text(encoding="utf-8"))
        cmd._validate_structure(manifest, base_data_dir / "manifest.json")

    def test_missing_required_field(self, base_data_dir: Path) -> None:
        """Brak wymaganego pola — CommandError."""
        cmd = Command()
        manifest = {"description": "test", "files": [], "compatible_schema": "1.0"}
        with pytest.raises(CommandError, match="nie zawiera wymaganych pól"):
            cmd._validate_structure(manifest, base_data_dir / "manifest.json")

    def test_wrong_field_type(self, base_data_dir: Path) -> None:
        """Błędny typ pola — CommandError."""
        cmd = Command()
        manifest = {"snapshot_version": "2026-01-01", "description": "test", "files": "not-a-list", "statistics": {}, "compatible_schema": "1.0"}
        with pytest.raises(CommandError, match="błędny typ"):
            cmd._validate_structure(manifest, base_data_dir / "manifest.json")

    def test_empty_files_list(self, base_data_dir: Path) -> None:
        """Pusta lista files — CommandError."""
        cmd = Command()
        manifest = {"snapshot_version": "2026-01-01", "description": "test", "files": [], "statistics": {}, "compatible_schema": "1.0"}
        with pytest.raises(CommandError, match="manifest jest puste"):
            cmd._validate_structure(manifest, base_data_dir / "manifest.json")


class TestValidateSchemaVersion:
    """Testy metody _validate_schema_version."""

    def test_valid_schema_version(self):
        """Poprawna wersja schematu — brak wyjątku."""
        cmd = Command()
        cmd._validate_schema_version({"compatible_schema": "1.0"})

    def test_invalid_schema_version(self):
        """Nieprawidłowa wersja schematu — CommandError."""
        cmd = Command()
        with pytest.raises(CommandError, match="Niekompatybilny schemat"):
            cmd._validate_schema_version({"compatible_schema": "2.0"})


class TestValidateFilesExist:
    """Testy metody _validate_files_exist."""

    def test_all_files_exist(self, base_data_dir: Path) -> None:
        """Wszystkie pliki istnieją — brak wyjątku."""
        _write_badge_versions(base_data_dir, [{"pk": 1, "rules": [{"type": "MinAgeRule"}]}])
        cmd = Command()
        manifest = json.loads((base_data_dir / "manifest.json").read_text(encoding="utf-8"))
        cmd._validate_files_exist(manifest, base_data_dir)

    def test_missing_files(self, base_data_dir: Path) -> None:
        """Brakujące pliki — CommandError."""
        cmd = Command()
        manifest = {"files": ["nonexistent.json.gz"]}
        with pytest.raises(CommandError, match="Brakujące pliki"):
            cmd._validate_files_exist(manifest, base_data_dir)


class TestValidateChecksums:
    """Testy metody _validate_checksums."""

    def test_valid_checksums(self, base_data_dir: Path) -> None:
        """Poprawne checksums — brak wyjątku."""
        _write_badge_versions(base_data_dir, [{"pk": 1, "rules": [{"type": "MinAgeRule"}]}])
        cmd = Command()
        import hashlib
        file_path = base_data_dir / "03_badges.json.gz"
        expected_checksum = hashlib.sha256(file_path.read_bytes()).hexdigest()
        manifest = {
            "files": ["03_badges.json.gz"],
            "checksums": {"03_badges.json.gz": expected_checksum},
        }
        cmd._validate_checksums(manifest, base_data_dir)

    def test_missing_checksums_field(self, base_data_dir: Path) -> None:
        """Brak pola checksums — CommandError."""
        cmd = Command()
        manifest = {"files": ["03_badges.json.gz"], "statistics": {}}
        with pytest.raises(CommandError, match="nie zawiera pola 'checksums'"):
            cmd._validate_checksums(manifest, base_data_dir)

    def test_checksums_not_dict(self, base_data_dir: Path) -> None:
        """checksums nie jest słownikiem — CommandError."""
        cmd = Command()
        manifest = {"files": ["03_badges.json.gz"], "checksums": "not-a-dict", "statistics": {}}
        with pytest.raises(CommandError, match="musi być słownikiem"):
            cmd._validate_checksums(manifest, base_data_dir)

    def test_missing_checksum_for_file(self, base_data_dir: Path) -> None:
        """Brak checksum dla pliku — CommandError."""
        cmd = Command()
        manifest = {"files": ["03_badges.json.gz"], "checksums": {"other.json.gz": "abc"}, "statistics": {}}
        with pytest.raises(CommandError, match="brak checksum w manifest"):
            cmd._validate_checksums(manifest, base_data_dir)

    def test_checksum_mismatch(self, base_data_dir: Path) -> None:
        """Nieprawidłowy checksum — CommandError."""
        _write_badge_versions(base_data_dir, [{"pk": 1, "rules": [{"type": "MinAgeRule"}]}])
        cmd = Command()
        manifest = {
            "files": ["03_badges.json.gz"],
            "checksums": {"03_badges.json.gz": "wrong_checksum"},
            "statistics": {},
        }
        with pytest.raises(CommandError, match="checksum mismatch"):
            cmd._validate_checksums(manifest, base_data_dir)
