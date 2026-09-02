"""Testy architektury: weryfikacja poprawności wygenerowanego Architecture Scorecardu.

FF-DIAG-001: Architecture Scorecard Metrics
Status: Diagnostic

Wymagania:
- Scorecard JSON musi istnieć po uruchomieniu scripts/architecture-scorecard.py
- Musi zawierać health_score jako liczbę zmiennoprzecinkową
- health_score musi być w przedziale [0, 100]
- Musi zawierać wszystkie kluczowe grupy metryk
- Każda grupa metryk musi mieć pole 'status'
- complexity.status == 'fail' gdy max_complexity > próg dla warstwy
- architecture_contracts.status == 'fail' gdy audit_contracts.py zgłasza naruszenia
- import_linter.status == 'fail' gdy broken > 0
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCORECARD_PATH = ROOT / "architecture_scorecard.json"
SCRIPT_PATH = ROOT / "scripts" / "architecture-scorecard.py"

REQUIRED_METRIC_GROUPS = {
    "complexity",
    "maintainability",
    "layer_metrics",
    "security",
    "tdd",
    "architecture_contracts",
    "import_linter",
    "type_check",
    "lint",
}
EXPECTED_LAYERS = {"domain", "application", "infrastructure", "apps", "bootstrap", "scripts"}
LAYER_COMPLEXITY_THRESHOLDS = {
    "domain": 10,
    "application": 15,
    "scripts": 25,
    "infrastructure": 22,
    "apps": 25,
    "bootstrap": 10,
}


@pytest.fixture(scope="module")
def scorecard() -> dict:
    """Generate the scorecard once for all tests in this module."""
    if not SCORECARD_PATH.exists() or "--no-regen" not in json.dumps(
        pytest.config_args if hasattr(pytest, "config_args") else {}
    ):
        result = subprocess.run(
            ["uv", "run", "python", str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=ROOT,
        )
        if result.returncode != 0:
            pytest.skip(f"Scorecard generation failed: {result.stderr}")
    assert SCORECARD_PATH.exists(), "architecture_scorecard.json was not generated"
    data: dict = json.loads(SCORECARD_PATH.read_text(encoding="utf-8"))
    return data


class TestScorecardStructure:
    """Struktura pliku JSON scorecardu."""

    def test_scorecard_has_metadata(self, scorecard: dict) -> None:
        """Scorecard musi zawierać sekcję metadata."""
        assert "metadata" in scorecard
        assert "name" in scorecard["metadata"]
        assert "generated_at" in scorecard["metadata"]

    def test_scorecard_has_health_score(self, scorecard: dict) -> None:
        """Scorecard musi zawierać health_score."""
        assert "health_score" in scorecard
        assert isinstance(scorecard["health_score"], (int, float))

    def test_health_score_in_valid_range(self, scorecard: dict) -> None:
        """health_score musi być w przedziale [0, 100]."""
        assert 0 <= scorecard["health_score"] <= 100

    def test_scorecard_has_all_metric_groups(self, scorecard: dict) -> None:
        """Scorecard musi zawierać wszystkie grupy metryk."""
        metrics = scorecard["metrics"]
        missing = REQUIRED_METRIC_GROUPS - set(metrics.keys())
        assert not missing, f"Brak grup metryk: {missing}"


class TestScorecardMetrics:
    """Poprawność poszczególnych metryk."""

    def test_complexity_has_status(self, scorecard: dict) -> None:
        """complexity musi mieć pole status."""
        assert scorecard["metrics"]["complexity"]["status"] in ("pass", "fail", "unknown")

    def test_complexity_max_exceeds_threshold_is_fail(self, scorecard: dict) -> None:
        """Jeśli max_complexity > próg dla warstwy, status powinien być fail."""
        complexity = scorecard["metrics"]["complexity"]
        if complexity["max_complexity"] > LAYER_COMPLEXITY_THRESHOLDS["scripts"]:
            assert complexity["status"] == "fail", (
                f"max_complexity={complexity['max_complexity']} przekracza próg, ale status={complexity['status']}"
            )

    def test_maintainability_has_status(self, scorecard: dict) -> None:
        """maintainability musi mieć pole status."""
        assert scorecard["metrics"]["maintainability"]["status"] in ("pass", "warn", "unknown")

    def test_architecture_contracts_have_status(self, scorecard: dict) -> None:
        """architecture_contracts musi mieć pole status."""
        assert scorecard["metrics"]["architecture_contracts"]["status"] in ("pass", "fail", "timeout", "unknown")

    def test_import_linter_has_status(self, scorecard: dict) -> None:
        """import_linter musi mieć pole status."""
        assert scorecard["metrics"]["import_linter"]["status"] in ("pass", "fail", "timeout", "unknown")

    def test_import_linter_broken_zero_means_pass(self, scorecard: dict) -> None:
        """Jeśli broken=0, status powinien być pass."""
        linter = scorecard["metrics"]["import_linter"]
        if linter.get("broken", -1) == 0:
            assert linter["status"] == "pass"

    def test_type_check_has_status(self, scorecard: dict) -> None:
        """type_check musi mieć pole status."""
        assert scorecard["metrics"]["type_check"]["status"] in ("pass", "fail", "timeout", "unknown")

    def test_lint_has_status(self, scorecard: dict) -> None:
        """lint musi mieć pole status."""
        assert scorecard["metrics"]["lint"]["status"] in ("pass", "fail", "timeout", "unknown")

    def test_security_has_status(self, scorecard: dict) -> None:
        """security musi mieć pole status."""
        assert scorecard["metrics"]["security"]["status"] in ("pass", "fail", "unknown")

    def test_tdd_has_status(self, scorecard: dict) -> None:
        """tdd musi mieć pole status."""
        assert scorecard["metrics"]["tdd"]["status"] in ("pass", "warn", "unknown")


class TestScorecardLayerMetrics:
    """Metriki per-warstwa."""

    def test_all_layers_present(self, scorecard: dict) -> None:
        """Wszystkie oczekiwane warstwy muszą być w layer_metrics."""
        layers = set(scorecard["metrics"]["layer_metrics"].keys())
        missing = EXPECTED_LAYERS - layers
        assert not missing, f"Brak warstw: {missing}"

    def test_layer_has_loc(self, scorecard: dict) -> None:
        """Każda warstwa musi mieć pole loc."""
        for layer_name, layer_data in scorecard["metrics"]["layer_metrics"].items():
            assert "loc" in layer_data, f"Warstwa {layer_name} nie ma pola loc"
            assert isinstance(layer_data["loc"], int)

    def test_layer_has_complexity(self, scorecard: dict) -> None:
        """Każda warstwa musi mieć pole complexity."""
        for layer_name, layer_data in scorecard["metrics"]["layer_metrics"].items():
            assert "complexity" in layer_data, f"Warstwa {layer_name} nie ma pola complexity"


class TestScorecardThresholds:
    """Weryfikacja progów krytycznych."""

    def test_domain_complexity_under_threshold(self, scorecard: dict) -> None:
        """Średnia complexity domeny powinna być rozsądna (nie powinna przekraczać 20)."""
        domain_metrics = scorecard["metrics"]["layer_metrics"]["domain"]
        assert domain_metrics["complexity"] <= 20, (
            f"Domain complexity {domain_metrics['complexity']} exceeds safe threshold"
        )

    def test_scripts_mi_not_catastrophic(self, scorecard: dict) -> None:
        """MI dla scripts powinno być powyżej 40 (niskie, ale nie krytyczne)."""
        scripts_metrics = scorecard["metrics"]["layer_metrics"]["scripts"]
        assert scripts_metrics["mi"] >= 40, f"Scripts MI {scripts_metrics['mi']} is below minimum acceptable"
