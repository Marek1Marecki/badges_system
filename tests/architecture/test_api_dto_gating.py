"""Testy architektury: API widoki modyfikujące stan powinny używać DTO Pydantic."""

import ast
from pathlib import Path

import pytest

API_VIEWS_FILE = Path("apps/api/views.py")


def _extract_mutation_methods_that_parse_body(file_path: Path) -> list[tuple[str, str]]:
    """Zwraca listę (nazwa_klasy, nazwa_metody) dla metod POST/PATCH, które parsują request.body lub JSON."""
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    methods = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name in ("post", "patch"):
                    # Szukaj użycia request.body lub json.loads
                    parses_json = False
                    uses_files_only = False
                    for child in ast.walk(item):
                        if isinstance(child, ast.Attribute):
                            if child.attr == "body":
                                parses_json = True
                            elif child.attr == "FILES":
                                uses_files_only = True
                        elif isinstance(child, ast.Call):
                            func = child.func
                            if isinstance(func, ast.Attribute) and func.attr == "loads":
                                parses_json = True
                    if parses_json and not uses_files_only:
                        methods.append((node.name, item.name))
    return methods


def _method_uses_dto_for_validation(file_path: Path, class_name: str, method_name: str) -> bool:
    """Sprawdza, czy metoda używa DTO do walidacji (szuka BaseModel)."""
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == method_name:
                    for child in ast.walk(item):
                        if isinstance(child, ast.Call):
                            func = child.func
                            if isinstance(func, ast.Name):
                                if "DTO" in func.id or "Model" in func.id:
                                    return True
                            elif isinstance(func, ast.Attribute):
                                if "DTO" in func.attr or "Model" in func.attr:
                                    return True
    return False


@pytest.fixture()
def mutation_methods_that_parse_body() -> list[tuple[str, str]]:
    return _extract_mutation_methods_that_parse_body(API_VIEWS_FILE)


def test_api_views_use_dto_for_mutation(
    mutation_methods_that_parse_body: list[tuple[str, str]],
) -> None:
    """Widoki modyfikujące stan, które parsują request.body, muszą używać DTO Pydantic."""
    violations = []
    for class_name, method_name in mutation_methods_that_parse_body:
        if not _method_uses_dto_for_validation(API_VIEWS_FILE, class_name, method_name):
            violations.append(f"{class_name}.{method_name}() parsuje body bez DTO")
    assert not violations, "Widoki API nie używają DTO:\n" + "\n".join(violations)
