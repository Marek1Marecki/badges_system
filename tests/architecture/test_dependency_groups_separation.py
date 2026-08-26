"""Testy architektury: separacja grup zależności — narzędzia dev/test nie mogą trafić do runtime."""

import re
from pathlib import Path

import pytest

PYPROJECT = Path("pyproject.toml")


def _parse_dependency_list(text: str, list_start: int) -> set[str]:
    """Parsuje listę zależności z pyproject.toml."""
    deps = set()
    i = list_start
    while i < len(text):
        line = text[i].strip()
        if line.startswith("]"):
            break
        if line and not line.startswith("#"):
            match = re.match(r'"(.+?)"', line)
            if match:
                deps.add(match.group(1))
        i += 1
    return deps


def _get_dependency_groups() -> tuple[set[str], set[str], set[str]]:
    """Zwraca (runtime, test, dev) zbiory nazw zależności z pyproject.toml."""
    text = PYPROJECT.read_text(encoding="utf-8").splitlines()

    runtime = set()
    test_group = set()
    dev_group = set()

    i = 0
    while i < len(text):
        line = text[i].strip()
        if line == "dependencies = [":
            runtime = _parse_dependency_list(text, i + 1)
        elif line == "test = [":
            test_group = _parse_dependency_list(text, i + 1)
        elif line == "dev = [":
            dev_group = _parse_dependency_list(text, i + 1)
        i += 1

    return runtime, test_group, dev_group


@pytest.fixture()
def dependency_groups() -> tuple[set[str], set[str], set[str]]:
    return _get_dependency_groups()


def test_dev_dependencies_not_in_runtime(dependency_groups: tuple[set[str], set[str], set[str]]) -> None:
    """Zależności z grupy dev nie mogą pojawiać się w runtime dependencies."""
    runtime, test_group, dev_group = dependency_groups
    violations = dev_group & runtime
    assert not violations, f"Zależności dev w runtime: {sorted(violations)}"


def test_test_dependencies_not_in_runtime(dependency_groups: tuple[set[str], set[str], set[str]]) -> None:
    """Zależności z grupy test nie mogą pojawiać się w runtime dependencies."""
    runtime, test_group, dev_group = dependency_groups
    violations = test_group & runtime
    assert not violations, f"Zależności test w runtime: {sorted(violations)}"