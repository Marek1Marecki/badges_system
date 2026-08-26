"""Testy architektury: adaptery repozytoriów implementują porty."""

import ast
from pathlib import Path

import pytest

PORTS_DIR = Path("application/ports")
ADAPTERS_DIR = Path("infrastructure/adapters/persistence")


def _get_protocol_methods(port_file: Path) -> dict[str, set[str]]:
    """Zwraca słownik {nazwa_protokolu: zestaw_nazw_metod} z pliku z portami."""
    tree = ast.parse(port_file.read_text(encoding="utf-8"))
    protocols = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = set()
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    methods.add(item.name)
            protocols[node.name] = methods
    return protocols


def _get_adapter_methods(adapter_file: Path) -> set[str]:
    """Zwraca zestaw nazw metod z klasy adaptera."""
    tree = ast.parse(adapter_file.read_text(encoding="utf-8"))
    methods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    methods.add(item.name)
    return methods


def _match_adapter_to_port(adapter_file: Path, port_methods: dict[str, set[str]]) -> str | None:
    """Dopasowuje adapter do portu po nazwie klasy."""
    adapter_name = adapter_file.stem
    for protocol_name in port_methods:
        if protocol_name.replace("Port", "").lower() in adapter_name.lower():
            return protocol_name
    return None


@pytest.fixture()
def port_methods_by_file() -> dict[Path, dict[str, set[str]]]:
    result = {}
    for port_file in PORTS_DIR.glob("*_port.py"):
        result[port_file] = _get_protocol_methods(port_file)
    return result


def test_repository_adapters_implement_ports(port_methods_by_file: dict[Path, dict[str, set[str]]]) -> None:
    """Adaptery repozytoriów muszą implementować wszystkie metody z odpowiadającego portu."""
    violations = []
    for port_file, protocols in port_methods_by_file.items():
        for protocol_name, port_methods in protocols.items():
            adapter_name = protocol_name.replace("Port", "").lower()
            adapter_file = ADAPTERS_DIR / f"django_{adapter_name}_repo.py"
            if not adapter_file.exists():
                continue
            adapter_methods = _get_adapter_methods(adapter_file)
            missing = port_methods - adapter_methods
            if missing:
                violations.append(
                    f"{adapter_file}: brakuje metod z {protocol_name}: {sorted(missing)}"
                )
    assert not violations, "Adaptery nie implementują portów:\n" + "\n".join(violations)
