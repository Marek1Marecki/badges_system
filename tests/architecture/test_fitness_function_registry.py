"""Testy architektury: weryfikacja kompletności rejestru fitness functions."""

import ast
import re
from pathlib import Path

import pytest

FITNESS_FUNCTIONS_FILE = Path("docs/architecture/fitness-functions.md")
GOVERNANCE_FILE = Path("docs/architecture/governance.md")


def _require_docs_files() -> None:
    """Pomija testy, jeśli pliki dokumentacji nie są dostępne.

    W obrazie Docker `docs/` jest wykluczone przez `.dockerignore` (linia 36),
    więc testy uruchomione w kontenerze nie mają dostępu do tych plików.
    Testy nadal wykonują się w CI jobie `static-analysis-and-unit-tests`
    (host) oraz lokalnie.
    """
    if not FITNESS_FUNCTIONS_FILE.exists() or not GOVERNANCE_FILE.exists():
        pytest.skip("Pliki dokumentacji governance nie są dostępne w tym środowisku")


def _extract_ff_ids_from_fitness_functions() -> set[str]:
    """Zwraca zbiór ID FF z rejestru w fitness-functions.md."""
    _require_docs_files()
    content = FITNESS_FUNCTIONS_FILE.read_text(encoding="utf-8")
    ids = set()
    for match in re.finditer(r"### (FF-\d+):", content):
        ids.add(match.group(1))
    return ids


def _extract_ff_ids_from_governance() -> set[str]:
    """Zwraca zbiór ID FF z tabel w governance.md."""
    _require_docs_files()
    content = GOVERNANCE_FILE.read_text(encoding="utf-8")
    ids = set()
    for match in re.finditer(r"FF-(\d+)", content):
        ids.add(f"FF-{match.group(1)}")
    return ids


def test_fitness_functions_registry_complete() -> None:
    """Wszystkie FF z governance.md muszą mieć wpis w rejestrze fitness-functions.md."""
    _require_docs_files()
    registry_ids = _extract_ff_ids_from_fitness_functions()
    governance_ids = _extract_ff_ids_from_governance()
    missing = governance_ids - registry_ids
    assert not missing, f"FF w governance.md bez wpisu w rejestrze: {sorted(missing)}"


def test_fitness_functions_have_required_fields() -> None:
    """Każdy wpis FF w rejestrze musi mieć wymagane sekcje."""
    _require_docs_files()
    content = FITNESS_FUNCTIONS_FILE.read_text(encoding="utf-8")
    required_fields = [
        "**Nazwa**",
        "**Tool**",
        "**Chroni**",
        "**Powiązanie**",
        "**Opis:**",
    ]
    violations = []
    for match in re.finditer(r"### (FF-\d+): ([^\n]+)", content):
        ff_id = match.group(1)
        ff_name = match.group(2)
        section_start = match.end()
        next_heading = content.find("\n### ", section_start)
        if next_heading == -1:
            next_heading = content.find("\n## ", section_start)
        if next_heading == -1:
            next_heading = len(content)
        section = content[section_start:next_heading]
        missing_fields = [field for field in required_fields if field not in section]
        if missing_fields:
            violations.append(
                f"{ff_id} ({ff_name}): brakuje pól: {', '.join(missing_fields)}"
            )
    assert not violations, "FF bez wymaganych pól:\n" + "\n".join(violations)