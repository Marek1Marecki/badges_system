"""Testy architektury: obsługa wyjątków w API musi zapewniać kontekst."""

import ast
from pathlib import Path

import pytest

API_VIEWS_FILE = Path("apps/api/views.py")


def _get_exception_handler_blocks(file_path: Path) -> list[tuple[str, int, list[str]]]:
    """Zwraca listę (nazwa_klasy, linia, lista_złapanych_wyjątków) dla metod post/patch."""
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    blocks = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name in ("post", "patch"):
                    caught = []
                    for child in ast.walk(item):
                        if isinstance(child, ast.ExceptHandler):
                            if child.type:
                                caught.append(ast.unparse(child.type))
                    blocks.append((node.name, item.lineno, caught))
    return blocks


@pytest.fixture()
def api_exception_blocks() -> list[tuple[str, int, list[str]]]:
    return _get_exception_handler_blocks(API_VIEWS_FILE)


def test_api_views_handle_application_exception(api_exception_blocks: list[tuple[str, int, list[str]]]) -> None:
    """Wszystkie metody post/patch muszą łapać ApplicationException."""
    violations = []
    for class_name, lineno, caught in api_exception_blocks:
        if not any("ApplicationException" in c for c in caught):
            violations.append(f"{class_name}.post/patch() (linia {lineno}) nie łapie ApplicationException")
    assert not violations, "Widoki API nie obsługują ApplicationException:\n" + "\n".join(violations)


def test_api_exception_handlers_have_request_id_context(api_exception_blocks: list[tuple[str, int, list[str]]]) -> None:
    """Bloki except ApplicationException muszą przekazywać request_id do odpowiedzi."""
    violations = []
    tree = ast.parse(API_VIEWS_FILE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name in ("post", "patch"):
                    for child in ast.walk(item):
                        if isinstance(child, ast.ExceptHandler):
                            if child.type and "ApplicationException" in ast.unparse(child.type):
                                has_request_id = False
                                for stmt in child.body:
                                    if isinstance(stmt, ast.Return):
                                        if isinstance(stmt.value, ast.Call):
                                            func = stmt.value.func
                                            if isinstance(func, ast.Name) and func.id in {"_problem_detail", "_handle_application_exception"}:
                                                has_request_id = True
                                            elif isinstance(func, ast.Attribute) and func.attr in {"_problem_detail", "_handle_application_exception"}:
                                                has_request_id = True
                                if not has_request_id:
                                    violations.append(
                                        f"{node.name}.{item.name}() (linia {child.lineno}): "
                                        "brak _problem_detail lub _handle_application_exception z request_id w obsłudze ApplicationException"
                                    )
    assert not violations, "Brak kontekstu request_id w obsłudze ApplicationException:\n" + "\n".join(violations)