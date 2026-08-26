"""Testy architektury: brak primitive obsession w return typach use cases."""

import ast
from pathlib import Path

import pytest

USECASES_DIR = Path("application/use_cases")
ALLOWED_DICT_RETURNS = {
    "explore_map.execute",
    "verify_badge.execute",
    "bulk_log_ascents.execute",
}


def _get_return_annotation(node: ast.FunctionDef) -> str | None:
    if node.returns:
        return ast.unparse(node.returns)
    return None


def _is_primitive_annotation(annotation: str) -> bool:
    primitive_types = {"dict", "Any", "list", "tuple", "set"}
    for primitive in primitive_types:
        if annotation == primitive or annotation.startswith(f"dict[") or annotation.startswith("list["):
            return True
    return False


def _get_usecase_functions() -> list[tuple[Path, ast.FunctionDef]]:
    """Zwraca listę funkcji z application/use_cases/."""
    functions = []
    for module in USECASES_DIR.glob("*.py"):
        if module.name == "__init__.py":
            continue
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append((module, node))
    return functions


def test_no_primitive_obsession_in_usecase_returns() -> None:
    """Use Case'y nie powinny zwracać surowych dict lub Any — wymagają DTO."""
    violations = []
    for module, func in _get_usecase_functions():
        annotation = _get_return_annotation(func)
        if annotation and _is_primitive_annotation(annotation):
            key = f"{module.stem}.{func.name}"
            if key in ALLOWED_DICT_RETURNS:
                continue
            violations.append(f"{module}:{func.lineno} {func.name}() -> {annotation}")
    assert not violations, "Use Case'y zwracają prymitywy:\n" + "\n".join(violations)
