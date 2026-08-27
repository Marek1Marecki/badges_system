#!/usr/bin/env python3
"""Update docs/security-backlog.md from Trivy JSON report.

Usage:
    python scripts/update_security_backlog.py trivy-report.json

Reads the Trivy report, classifies vulnerabilities by severity and
availability, and regenerates the security-backlog.md file.

Outputs to docs/security-backlog.md by default. Use --output to override.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any, cast


def load_trivy_report(path: Path) -> dict[str, Any]:
    """

    Args:
      path: Path:
      path: Path:

    Returns:

    """
    with open(path) as f:
        return cast(dict[str, Any], json.load(f))


def extract_vulns(data: dict) -> list[dict]:
    """

    Args:
      data: dict:
      data: dict:

    Returns:

    """
    vulns: list[dict] = []
    for result in data.get("Results", []):
        for v in result.get("Vulnerabilities", []):
            vulns.append(v)
    return vulns


def classify_vulns(vulns: list[dict]) -> dict[str, list[dict]]:
    """

    Args:
      vulns: list[dict]:
      vulns: list[dict]:

    Returns:

    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for v in vulns:
        severity = v.get("Severity", "UNKNOWN")
        if severity not in ("CRITICAL", "HIGH"):
            continue
        status = v.get("Status", "affected")
        if status == "fix_deferred":
            key = f"{severity} + fix_deferred"
        elif status == "will_not_fix":
            key = f"{severity} + will_not_fix"
        else:
            key = f"{severity} + affected"
        groups[key].append(v)
    return dict(groups)


def pkg_table(vulns: list[dict], max_rows: int = 50) -> str:
    """

    Args:
      vulns: list[dict]:
      max_rows: int:  (Default value = 50)
      vulns: list[dict]:
      max_rows: int:  (Default value = 50)

    Returns:

    """
    by_pkg: dict[str, list[dict]] = defaultdict(list)
    for v in vulns:
        by_pkg[v.get("PkgName", "unknown")].append(v)

    rows: list[str] = []
    for pkg, pkg_vulns in sorted(by_pkg.items(), key=lambda x: -len(x[1])):
        v0 = pkg_vulns[0]
        severity = v0.get("Severity", "UNKNOWN")
        status = v0.get("Status", "affected")
        if status == "fix_deferred":
            avail = "fix_deferred"
        elif status == "will_not_fix":
            avail = "will_not_fix"
        else:
            avail = "affected"
        rows.append(
            f"| {v0.get('VulnerabilityID', '')} | {pkg} | {severity} | {avail} | upgrade / exception | — | {_next_review()} |"
        )
        if len(rows) >= max_rows:
            rows.append("| … | … | … | … | … | — | … |")
            break
    return "\n".join(rows)


def top_packages(vulns: list[dict], n: int = 10) -> str:
    """

    Args:
      vulns: list[dict]:
      n: int:  (Default value = 10)
      vulns: list[dict]:
      n: int:  (Default value = 10)

    Returns:

    """
    c = Counter(v.get("PkgName", "unknown") for v in vulns)
    lines: list[str] = []
    for pkg, count in c.most_common(n):
        lines.append(f"  {count} - {pkg}")
    return "\n".join(lines)


def _next_review() -> str:
    """Oblicza datę kolejnego przeglądu."""
    today = date.today()
    target = today + timedelta(days=42)
    return target.strftime("%Y-%m-%d")


def build_backlog(groups: dict[str, list[dict]]) -> str:
    """

    Args:
      groups: dict[str:
      list[dict]]:
      groups: dict[str:

    Returns:

    """
    today = date.today().isoformat()
    total = sum(len(v) for v in groups.values())

    lines: list[str] = [
        "# Security Backlog",
        "",
        "Rejestr wszystkich CVE znalezionych w skanach Trivy w fazie development.",
        "Backlog jest przeglądany co 2–4 tygodnie.",
        "",
        "Priorytet:",
        "1. `affected` + dostępny fix",
        "2. `fix_deferred`",
        "3. `will_not_fix`",
        "",
        f"## Obecny stan ({today})",
        "",
        "### Podsumowanie",
        "",
        "| Kategoria | Liczba | Działanie |",
        "|-----------|--------|-----------|",
    ]

    for key in (
        "CRITICAL + affected",
        "CRITICAL + fix_deferred",
        "CRITICAL + will_not_fix",
        "HIGH + affected",
        "HIGH + fix_deferred",
        "HIGH + will_not_fix",
    ):
        count = len(groups.get(key, []))
        action = {
            "CRITICAL + affected": "backlog remediation",
            "CRITICAL + fix_deferred": "security exception",
            "CRITICAL + will_not_fix": "security exception",
            "HIGH + affected": "backlog remediation",
            "HIGH + fix_deferred": "security exception",
            "HIGH + will_not_fix": "security exception",
        }.get(key, "review")
        lines.append(f"| {key} | {count} | {action} |")

    lines += [
        f"| **RAZEM** | **{total}** | — |",
        "",
        "### CRITICAL — affected (fix dostępny, brak w Debian 12)",
        "",
        "| CVE | Package | Action | Owner | Target |",
        "|-----|---------|--------|-------|--------|",
    ]

    if groups.get("CRITICAL + affected"):
        lines.append(pkg_table(groups["CRITICAL + affected"]))
    else:
        lines.append("| — | — | — | — | — |")

    lines += [
        "",
        "### CRITICAL — will_not_fix",
        "",
        "| CVE | Package | Action | Owner | Target |",
        "|-----|---------|--------|-------|--------|",
    ]

    if groups.get("CRITICAL + will_not_fix"):
        lines.append(pkg_table(groups["CRITICAL + will_not_fix"]))
    else:
        lines.append("| — | — | — | — | — |")

    lines += [
        "",
        "### CRITICAL — fix_deferred",
        "",
        "| CVE | Package | Action | Owner | Target |",
        "|-----|---------|--------|-------|--------|",
    ]

    if groups.get("CRITICAL + fix_deferred"):
        lines.append(pkg_table(groups["CRITICAL + fix_deferred"]))
    else:
        lines.append("| — | — | — | — | — |")

    lines += [
        "",
        "### HIGH — affected",
        "",
        "| CVE | Package | Action | Owner | Target |",
        "|-----|---------|--------|-------|--------|",
    ]

    if groups.get("HIGH + affected"):
        lines.append(pkg_table(groups["HIGH + affected"]))
    else:
        lines.append("| — | — | — | — | — |")

    lines += [
        "",
        "### HIGH — will_not_fix",
        "",
        "| CVE | Package | Action | Owner | Target |",
        "|-----|---------|--------|-------|--------|",
    ]

    if groups.get("HIGH + will_not_fix"):
        lines.append(pkg_table(groups["HIGH + will_not_fix"]))
    else:
        lines.append("| — | — | — | — | — |")

    lines += [
        "",
        "### HIGH — fix_deferred",
        "",
        "| CVE | Package | Action | Owner | Target |",
        "|-----|---------|--------|-------|--------|",
    ]

    if groups.get("HIGH + fix_deferred"):
        lines.append(pkg_table(groups["HIGH + fix_deferred"]))
    else:
        lines.append("| — | — | — | — | — |")

    lines += [
        "",
        "## Klasyfikacja obszarów",
        "",
        "| Obszar | Priorytet | Pierwsza akcja |",
        "|--------|-----------|----------------|",
        "| GDAL | 🔴 wysoki | ustalić dostępność fixa + rzeczywistą ekspozycję |",
        "| perl-base | 🔴 wysoki | ustalić, dlaczego jest w production |",
        "| libaom3/libheif1 | 🔴 wysoki | ustalić dependency chain i możliwość usunięcia |",
        "| libcurl/OpenSSL | 🟠 średni/wysoki | ustalić źródło systemowych bibliotek |",
        "| will_not_fix | 🟠 | formalny risk assessment |",
        "",
        "## Proces",
        "",
        "1. Co 2–4 tygodnie zespół przegląda ten dokument",
        "2. Dla każdego CVE:",
        "   - sprawdź czy pojawił się fix",
        "   - sprawdź czy aplikacja nadal nie używa dotkniętej funkcji",
        "   - zaktualizuj status",
        "3. Wyjątki z przekroczonym terminem przeglądu wracają do polityki domyślnej",
        "",
        f"<!-- Last updated: {today} from Trivy scan -->",
    ]

    return "\n".join(lines) + "\n"


def main() -> int:
    """Główna funkcja skryptu aktualizującego backlog bezpieczeństwa."""
    parser = argparse.ArgumentParser(description="Update security-backlog.md from Trivy JSON report")
    parser.add_argument("report", type=Path, help="Path to trivy-report.json")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/security-backlog.md"),
        help="Output markdown file (default: docs/security-backlog.md)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print to stdout instead of writing file",
    )
    args = parser.parse_args()

    if not args.report.exists():
        print(f"ERROR: report not found: {args.report}", file=sys.stderr)
        return 1

    data = load_trivy_report(args.report)
    vulns = extract_vulns(data)
    groups = classify_vulns(vulns)

    total = sum(len(v) for v in groups.values())
    print(f"Loaded {len(vulns)} vulnerabilities from {args.report}")
    for key in (
        "CRITICAL + affected",
        "CRITICAL + fix_deferred",
        "CRITICAL + will_not_fix",
        "HIGH + affected",
        "HIGH + fix_deferred",
        "HIGH + will_not_fix",
    ):
        count = len(groups.get(key, []))
        print(f"  {key}: {count}")

    if total == 0:
        print("No HIGH/CRITICAL vulnerabilities found. Backlog would be empty.")
        return 0

    content = build_backlog(groups)

    if args.dry_run:
        print(content)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
        print(f"Written to {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
