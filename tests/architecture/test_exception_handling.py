"""Testy architektury: widoki API muszą łapać ApplicationException."""

import ast
from pathlib import Path

import pytest

API_VIEWS_FILE = Path("apps/api/views.py")
EXEMPT_METHODS = {"post", "patch"}


def _extract_mutation_methods(file_path: Path) -> list[tuple[str, str]]:
    """Zwraca listę (nazwa_klasy, nazwa_metody) dla metod POST/PATCH w widokach."""
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    methods = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name in EXEMPT_METHODS:
                    methods.append((node.name, item.name))
    return methods


def _method_handles_application_exception(file_path: Path, class_name: str, method_name: str) -> bool:
    """Sprawdza, czy metoda ma except ApplicationException."""
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == method_name:
                    for child in ast.walk(item):
                        if isinstance(child, ast.ExceptHandler):
                            if isinstance(child.type, ast.Name) and child.type.id == "ApplicationException":
                                return True
                            elif isinstance(child.type, ast.Attribute) and child.type.attr == "ApplicationException":
                                return True
    return False


@pytest.fixture()
def mutation_methods() -> list[tuple[str, str]]:
    return _extract_mutation_methods(API_VIEWS_FILE)


def test_api_views_handle_application_exception(mutation_methods: list[tuple[str, str]]) -> None:
    """Wszystkie widoki modyfikujące stan muszą łapać ApplicationException."""
    violations = []
    for class_name, method_name in mutation_methods:
        if not _method_handles_application_exception(API_VIEWS_FILE, class_name, method_name):
            violations.append(f"{class_name}.{method_name}() nie łapie ApplicationException")
    assert not violations, "Widoki API nie łapią ApplicationException:\n" + "\n".join(violations)
