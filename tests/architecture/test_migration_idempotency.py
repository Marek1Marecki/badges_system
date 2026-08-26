"""Testy architektury: migracje nie mogą mieszać operacji DDL w jednym pliku."""

import ast
from pathlib import Path

import pytest

MIGRATIONS_DIR = Path("apps")
CONFLICTING_OPERATIONS = {
    "AddField", "RemoveField", "RenameField", "AlterField",
    "AddIndex", "RemoveIndex", "AddConstraint", "RemoveConstraint",
}


def _get_migration_operations(module_path: Path) -> set[str]:
    """Zwraca zbiór nazw operacji DDL w migracji."""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    operations = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if node.targets[0].id == "operations":
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Call):
                            func = elt.func
                            if isinstance(func, ast.Attribute):
                                operations.add(func.attr)
                            elif isinstance(func, ast.Name):
                                operations.add(func.id)
    return operations


def _has_conflicting_operations(operations: set[str]) -> bool:
    """Sprawdza, czy w zbiorze operacji są wzajemnie sprzeczne pary."""
    expanding = {"AddField", "AddIndex", "AddConstraint"}
    contracting = {"RemoveField", "RemoveIndex", "RemoveConstraint"}
    has_expanding = bool(operations & expanding)
    has_contracting = bool(operations & contracting)
    return has_expanding and has_contracting


@pytest.fixture()
def migration_files() -> list[Path]:
    files = []
    for app_dir in MIGRATIONS_DIR.iterdir():
        if not app_dir.is_dir():
            continue
        migrations = app_dir / "migrations"
        if not migrations.exists():
            continue
        for migration_file in migrations.glob("*.py"):
            if migration_file.name == "__init__.py":
                continue
            files.append(migration_file)
    return files


def test_migrations_do_not_mix_conflicting_operations(migration_files: list[Path]) -> None:
    """Migracje nie powinny mieszać operacji ekspansji i kontrakcji DDL w jednym pliku."""
    violations = []
    for migration_file in migration_files:
        operations = _get_migration_operations(migration_file)
        if _has_conflicting_operations(operations):
            violations.append(f"{migration_file}: {sorted(operations)}")
    assert not violations, "Migracje mieszają sprzeczne operacje DDL:\n" + "\n".join(violations)
