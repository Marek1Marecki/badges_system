"""Architecture Scorecard Generator.

Aggregates architecture compliance KPIs into a single JSON scorecard.
This is a Diagnostic tool — it reports metrics, does not enforce them.
Gate-level enforcement remains in: make check (ruff, mypy, lint-imports,
pytest, audit_contracts.py) and make complexity-check (radon + xenon).

Generated at: scripts/architecture-scorecard.py
Output:       architecture_scorecard.json (in repo root)
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = ROOT / "architecture_scorecard.json"

ROOT = Path(__file__).resolve().parents[1]
PY_DIRS = ["domain", "application", "infrastructure", "apps", "bootstrap", "scripts"]
OUTPUT_FILE = ROOT / "architecture_scorecard.json"
MAX_DOMAIN_COMPLEXITY = 10
MAX_APPLICATION_COMPLEXITY = 15
MAX_SCRIPTS_COMPLEXITY = 25


def _run_radon(args: list[str]) -> dict:
    """Run radon with JSON output and return parsed results."""
    cmd = ["uv", "run", "radon", *args, "-j"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=ROOT)
        if result.returncode == 0:
            return json.loads(result.stdout) if result.stdout.strip() else {}
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return {}


def _compute_complexity_score(radon_cc: dict) -> dict:
    """Compute aggregate complexity metrics from radon CC JSON output."""
    total_blocks = 0
    avg_complexity = 0.0
    max_complexity = 0
    worst_hotspot = None
    rank_counts: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0}

    if not radon_cc:
        return {
            "average_complexity": 0.0,
            "max_complexity": 0,
            "total_blocks": 0,
            "rank_distribution": rank_counts,
            "worst_hotspot": None,
            "status": "unknown",
        }

    complexities = []
    for file_path, blocks in radon_cc.items():
        for block in blocks:
            if isinstance(block, dict):
                cc = block.get("complexity", 0)
                rank = block.get("rank", "A")
                total_blocks += 1
                complexities.append(cc)
                if rank in rank_counts:
                    rank_counts[rank] += 1
                if cc > max_complexity:
                    max_complexity = cc
                    worst_hotspot = {
                        "file": file_path,
                        "function": block.get("name", ""),
                        "line": block.get("lineno", 0),
                        "complexity": cc,
                        "rank": rank,
                    }

    if complexities:
        avg_complexity = round(sum(complexities) / len(complexities), 2)

    threshold_breach = max_complexity > MAX_SCRIPTS_COMPLEXITY
    status = "pass" if not threshold_breach else "fail"

    return {
        "average_complexity": avg_complexity,
        "max_complexity": max_complexity,
        "total_blocks": total_blocks,
        "rank_distribution": rank_counts,
        "worst_hotspot": worst_hotspot,
        "status": status,
    }


def _compute_maintainability_score(radon_mi: dict) -> dict:
    """Compute maintainability index metrics from radon MI JSON output."""
    if not radon_mi:
        return {"average_mi": 0.0, "files_below_threshold": 0, "status": "unknown"}

    mi_values = []
    files_below_c = 0
    worst_file = None
    for file_path, data in radon_mi.items():
        mi = data.get("mi", 100)
        rank = data.get("rank", "A")
        mi_values.append(mi)
        if rank in ("C", "D", "E", "F"):
            files_below_c += 1
            if worst_file is None or mi < worst_file["mi"]:
                worst_file = {"file": file_path, "mi": round(mi, 2), "rank": rank}

    avg_mi = round(sum(mi_values) / len(mi_values), 2) if mi_values else 0.0

    return {
        "average_mi": avg_mi,
        "files_below_threshold": files_below_c,
        "worst_file": worst_file,
        "status": "pass" if files_below_c == 0 else "warn",
    }


def _compute_layer_purity() -> dict:
    """Compute layer purity metrics from radon complexity per layer."""
    layer_stats = {}
    for layer in PY_DIRS:
        radon_cc = _run_radon(["cc", layer, "-a", "-nc"])
        radon_mi = _run_radon(["mi", layer])
        radon_raw = _run_radon(["raw", layer, "-j"])

        complexity_data = _compute_complexity_score(radon_cc)
        maintainability_data = _compute_maintainability_score(radon_mi)

        total_loc = 0
        if radon_raw:
            for file_data in radon_raw.values():
                total_loc += file_data.get("lloc", 0)

        layer_stats[layer] = {
            "loc": total_loc,
            "complexity": complexity_data["average_complexity"],
            "mi": maintainability_data["average_mi"],
            "max_complexity": complexity_data["max_complexity"],
        }

    return layer_stats


def _compute_security_coverage(radon_cc: dict) -> dict:
    """Compute security-related metrics: no-sensitive-data-in-logs detection."""
    sensitive_keywords = {
        "password",
        "passwd",
        "secret",
        "token",
        "api_key",
        "apikey",
        "authorization",
        "credentials",
        "private_key",
        "session_key",
        "session_token",
    }

    violations = []
    for file_path, _blocks in radon_cc.items():
        src_path = ROOT / file_path
        if not src_path.exists():
            continue
        try:
            content = src_path.read_text(encoding="utf-8")
            for line_num, line in enumerate(content.splitlines(), 1):
                lower_line = line.lower()
                for kw in sensitive_keywords:
                    if kw in lower_line and "log" in lower_line:
                        if "logger" in lower_line or "log." in lower_line or "logging" in lower_line:
                            violations.append({"file": file_path, "line": line_num, "keyword": kw})
        except (OSError, UnicodeDecodeError):
            pass

    return {
        "sensitive_data_in_logs_violations": len(violations),
        "violations": violations[:5],
        "status": "pass" if not violations else "fail",
    }


def _compute_tdd_compliance() -> dict:
    """Compute test-to-code ratios per layer."""
    test_counts = {}
    for layer in PY_DIRS:
        test_dir = ROOT / "tests" / layer
        if test_dir.exists():
            test_files = list(test_dir.rglob("test_*.py"))
            test_counts[layer] = len(test_files)
        else:
            test_counts[layer] = 0

    code_files = {}
    for layer in PY_DIRS:
        layer_path = ROOT / layer
        if layer_path.exists():
            py_files = [f for f in layer_path.rglob("*.py") if not f.name.startswith("test_")]
            code_files[layer] = len(py_files)
        else:
            code_files[layer] = 0

    ratios = {}
    total_tests = sum(test_counts.values())
    total_code = sum(code_files.values())
    overall_ratio = round(total_tests / total_code, 2) if total_code > 0 else 0.0

    for layer in PY_DIRS:
        ratio = round(test_counts.get(layer, 0) / code_files[layer], 2) if code_files.get(layer, 0) > 0 else 0.0
        ratios[layer] = {"test_files": test_counts.get(layer, 0), "code_files": code_files[layer], "ratio": ratio}

    return {
        "test_to_code_ratio": overall_ratio,
        "total_test_files": total_tests,
        "total_code_files": total_code,
        "breakdown": ratios,
        "status": "pass" if overall_ratio >= 0.5 else "warn",
    }


def _compute_architecture_violations() -> dict:
    """Run audit_contracts.py and capture pass/fail counts."""
    cmd = ["uv", "run", "python", str(ROOT / "scripts" / "audit_contracts.py")]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=ROOT)
        output = result.stdout + result.stderr
        if "Audit PASSED" in output:
            return {"violations": 0, "status": "pass", "output": output.strip()[-200:]}
        if "Audit FAILED" in output:
            match = re.search(r"(\d+) violation", output)
            count = int(match.group(1)) if match else 1
            return {"violations": count, "status": "fail", "output": output.strip()[-200:]}
    except subprocess.TimeoutExpired:
        return {"violations": -1, "status": "timeout", "output": "Timed out"}

    return {"violations": -1, "status": "unknown", "output": "No output"}


def _compute_import_linter_status() -> dict:
    """Run lint-imports and capture contract status."""
    cmd = ["uv", "run", "lint-imports"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=ROOT)
        output = result.stdout + result.stderr
        if result.returncode == 0:
            kept_match = re.search(r"(\d+) kept", output)
            broken_match = re.search(r"(\d+) broken", output)
            kept = int(kept_match.group(1)) if kept_match else 0
            broken = int(broken_match.group(1)) if broken_match else 0
            return {
                "kept": kept,
                "broken": broken,
                "status": "pass" if broken == 0 else "fail",
                "output": output.strip()[-200:],
            }
    except subprocess.TimeoutExpired:
        return {"kept": 0, "broken": 0, "status": "timeout", "output": "Timed out"}
    return {"kept": 0, "broken": 0, "status": "unknown", "output": "No output"}


def _compute_type_check_status() -> dict:
    """Run mypy and capture error count."""
    cmd = ["uv", "run", "mypy", *PY_DIRS]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=ROOT)
        output = result.stdout + result.stderr
        error_match = re.search(r"Found (\d+) error", output)
        error_count = int(error_match.group(1)) if error_match else 0
        return {
            "error_count": error_count,
            "status": "pass" if error_count == 0 else "fail",
            "output": output.strip()[-200:],
        }
    except subprocess.TimeoutExpired:
        return {"error_count": -1, "status": "timeout", "output": "Timed out"}
    return {"error_count": -1, "status": "unknown", "output": "No output"}


def _compute_lint_status() -> dict:
    """Run ruff check and capture error/warning counts."""
    cmd = ["uv", "run", "ruff", "check", *PY_DIRS]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=ROOT)
        output = result.stdout + result.stderr
        if result.returncode == 0:
            return {"issues": 0, "status": "pass", "output": "All checks passed"}
        error_match = re.search(r"(\d+) error", output)
        error_count = int(error_match.group(1)) if error_match else 0
        return {"issues": error_count, "status": "fail", "output": output.strip()[-200:]}
    except subprocess.TimeoutExpired:
        return {"issues": -1, "status": "timeout", "output": "Timed out"}
    return {"issues": -1, "status": "unknown", "output": "No output"}


def generate_scorecard() -> dict:
    """Generate the full architecture scorecard."""
    timestamp = datetime.now(timezone.utc).isoformat()  # noqa: TID251

    radon_cc_all = _run_radon(["cc", *PY_DIRS, "-a", "-nc"])
    radon_mi_all = _run_radon(["mi", *PY_DIRS])

    overall_complexity = _compute_complexity_score(radon_cc_all)
    overall_maintainability = _compute_maintainability_score(radon_mi_all)
    layer_metrics = _compute_layer_purity()
    security_metrics = _compute_security_coverage(radon_cc_all)
    tdd_metrics = _compute_tdd_compliance()
    arch_violations = _compute_architecture_violations()
    import_linter = _compute_import_linter_status()
    mypy_results = _compute_type_check_status()
    lint_results = _compute_lint_status()

    metrics = {
        "timestamp": timestamp,
        "complexity": overall_complexity,
        "maintainability": overall_maintainability,
        "layer_metrics": layer_metrics,
        "security": security_metrics,
        "tdd": tdd_metrics,
        "architecture_contracts": arch_violations,
        "import_linter": import_linter,
        "type_check": mypy_results,
        "lint": lint_results,
    }

    scores = []
    if overall_complexity.get("status") == "pass":
        scores.append(1.0)
    elif overall_complexity.get("status") == "fail":
        scores.append(0.0)

    if overall_maintainability.get("status") == "pass":
        scores.append(1.0)
    elif overall_maintainability.get("status") == "warn":
        scores.append(0.5)

    if arch_violations.get("status") == "pass":
        scores.append(1.0)
    elif arch_violations.get("status") == "fail":
        scores.append(0.0)

    if import_linter.get("status") == "pass":
        scores.append(1.0)
    elif import_linter.get("status") == "fail":
        scores.append(0.0)

    if mypy_results.get("status") == "pass":
        scores.append(1.0)
    elif mypy_results.get("status") == "fail":
        scores.append(0.0)

    if lint_results.get("status") == "pass":
        scores.append(1.0)
    elif lint_results.get("status") == "fail":
        scores.append(0.0)

    if security_metrics.get("status") == "pass":
        scores.append(1.0)
    elif security_metrics.get("status") == "fail":
        scores.append(0.0)

    health_score = round(sum(scores) / len(scores) * 100, 1) if scores else 0.0

    return {
        "metadata": {
            "name": "Architecture Compliance Scorecard",
            "description": "Consolidated KPI report for architecture health",
            "generated_at": timestamp,
            "schema_version": "1.0",
        },
        "health_score": health_score,
        "metrics": metrics,
    }


def main() -> int:
    scorecard = generate_scorecard()
    OUTPUT_FILE.write_text(json.dumps(scorecard, indent=2), encoding="utf-8")
    print(f"Architecture scorecard written to: {OUTPUT_FILE.relative_to(ROOT)}")
    print(f"Health Score: {scorecard['health_score']}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
