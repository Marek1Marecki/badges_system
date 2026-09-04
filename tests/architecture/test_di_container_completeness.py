"""Testy architektury: wszystkie UseCase'y i Serwisy muszą być zarejestrowane w kontenerze DI."""

import ast
import re
from pathlib import Path

USECASES_DIR = Path("application/use_cases")
SERVICES_DIR = Path("application/services")
CONTAINER_FILE = Path("bootstrap/container.py")


def _get_classes_from_dir(directory: Path, suffixes: tuple[str, ...]) -> set[str]:
    """Znajduje wszystkie klasy kończące się na podane sufiksy w danym katalogu."""
    classes = set()
    for module in directory.glob("*.py"):
        if module.name == "__init__.py":
            continue
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.endswith(suffixes):
                classes.add(node.name)
    return classes


def _get_usecase_classes() -> set[str]:
    return _get_classes_from_dir(USECASES_DIR, ("UseCase", "Command", "Query"))


def _get_service_classes() -> set[str]:
    return _get_classes_from_dir(SERVICES_DIR, ("Service",))


def _camel_to_snake(name: str) -> str:
    """Konwertuje CamelCase na snake_case, usuwa typowe przyrostki (tylko dla UseCase/Command/Query)."""
    for suffix in ("UseCase", "Command", "Query"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _get_container_fields() -> set[str]:
    """Znajduje wszystkie pola w AppContainer."""
    tree = ast.parse(CONTAINER_FILE.read_text(encoding="utf-8"))
    fields = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "AppContainer":
            for item in node.body:
                if isinstance(item, ast.AnnAssign):
                    if isinstance(item.target, ast.Name):
                        fields.add(item.target.id)
    return fields


def test_all_usecases_registered_in_container() -> None:
    """Wszystkie UseCase'y muszą być zarejestrowane w AppContainer."""
    usecases = _get_usecase_classes()
    container_fields = _get_container_fields()
    missing = {uc for uc in usecases if _camel_to_snake(uc) not in container_fields}
    assert not missing, f"UseCase'y nie zarejestrowane w kontenerze: {sorted(missing)}"


def test_all_services_registered_in_container() -> None:
    """Wszystkie Serwisy muszą być zarejestrowane w AppContainer."""
    services = _get_service_classes()
    container_fields = _get_container_fields()
    missing = {svc for svc in services if _camel_to_snake(svc) not in container_fields}
    assert not missing, f"Serwisy nie zarejestrowane w kontenerze: {sorted(missing)}"


def test_container_fields_match_registered_classes() -> None:
    """Pola AppContainer muszą odpowiadać nazwom UseCase'ów i Serwisów (snake_case)."""
    usecases = _get_usecase_classes()
    services = _get_service_classes()
    expected_fields = {_camel_to_snake(name) for name in usecases | services}
    container_fields = _get_container_fields()
    extra = container_fields - expected_fields
    assert not extra, f"Niespodziewane pola w AppContainer: {sorted(extra)}"
