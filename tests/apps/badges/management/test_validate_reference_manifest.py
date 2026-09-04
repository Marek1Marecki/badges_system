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

    def test_fails_when_rules_empty(self, base_data_dir: Path) -> None:
        """Puste rules — ValidationError, bo minItems=1."""
        _write_badge_versions(base_data_dir, [{"pk": 1, "rules": []}])
        cmd = Command()
        manifest = json.loads((base_data_dir / "manifest.json").read_text(encoding="utf-8"))
        with pytest.raises(CommandError) as exc_info:
            cmd._validate_json_schema(manifest, base_data_dir)
        assert "JSON Schema" in str(exc_info.value)

    def test_fails_when_rules_missing_type_key(self, base_data_dir: Path) -> None:
        """Rules bez klucza 'type' — ValidationError."""
        _write_badge_versions(base_data_dir, [{"pk": 1, "rules": [{"name": "no-type"}]}])
        cmd = Command()
        manifest = json.loads((base_data_dir / "manifest.json").read_text(encoding="utf-8"))
        with pytest.raises(CommandError) as exc_info:
            cmd._validate_json_schema(manifest, base_data_dir)
        assert "JSON Schema" in str(exc_info.value)
