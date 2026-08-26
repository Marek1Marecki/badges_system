"""Testy architektury: kierunki zależności między warstwami."""

import ast
from pathlib import Path

import pytest

LAYERS = ["domain", "application", "infrastructure", "apps", "bootstrap", "config"]
FORBIDDEN_DIRECTIONS = {
    ("domain", "application"),
    ("domain", "infrastructure"),
    ("domain", "apps"),
    ("domain", "bootstrap"),
    ("domain", "config"),
    ("application", "infrastructure"),
    ("application", "apps"),
    ("application", "bootstrap"),
    ("application", "config"),
    ("infrastructure", "bootstrap"),
}


def _get_layer(module: Path) -> str | None:
    for layer in LAYERS:
        if module.parts[: len(Path(layer).parts)] == Path(layer).parts:
            return layer
    return None


def _collect_imports(module: Path) -> set[str]:
    tree = ast.parse(module.read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
    return imports


@pytest.fixture()
def layer_imports() -> dict[str, list[tuple[Path, set[str]]]]:
    result: dict[str, list[tuple[Path, set[str]]]] = {layer: [] for layer in LAYERS}
    for layer in LAYERS:
        for module in Path(layer).rglob("*.py"):
            result[layer].append((module, _collect_imports(module)))
    return result


def test_no_forbidden_dependencies(layer_imports: dict[str, list[tuple[Path, set[str]]]]) -> None:
    """Warstwy nie mogą importować z warstw wyższych w hierarchii."""
    violations = []
    for source_layer, modules in layer_imports.items():
        for module, imports in modules:
            for imported in imports:
                if imported in LAYERS:
                    if (source_layer, imported) in FORBIDDEN_DIRECTIONS:
                        violations.append(f"{module}: {source_layer} -> {imported}")
    assert not violations, "Wykryto zabronione zależności:\n" + "\n".join(violations)
