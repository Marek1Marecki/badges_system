"""Testy architektury: reguły biznesowe muszą być niemutowalne (frozen dataclass)."""

import ast
from pathlib import Path

import pytest

RULES_DIR = Path("domain/rules")
BASE_RULE_NAME = "BadgeRule"


def _get_badge_rule_subclasses() -> list[tuple[Path, str]]:
    """Znajduje wszystkie klasy dziedziczące po BadgeRule."""
    subclasses = []
    for module in RULES_DIR.glob("*.py"):
        if module.name == "__init__.py":
            continue
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == BASE_RULE_NAME:
                        subclasses.append((module, node.name))
                    elif isinstance(base, ast.Attribute) and base.attr == BASE_RULE_NAME:
                        subclasses.append((module, node.name))
    return subclasses


def test_badge_rules_are_frozen_dataclasses() -> None:
    """Wszystkie reguły biznesowe muszą być @dataclass(frozen=True)."""
    violations = []
    for module, class_name in _get_badge_rule_subclasses():
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                has_frozen_decorator = any(
                    (isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "dataclass")
                    or (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == "dataclass")
                    or (isinstance(d, ast.Name) and d.id == "dataclass")
                    or (isinstance(d, ast.Attribute) and d.attr == "dataclass")
                    for d in node.decorator_list
                )
                if not has_frozen_decorator:
                    violations.append(f"{module}: {class_name}")
    assert not violations, "Reguły biznesowe nie są frozen dataclass:\n" + "\n".join(violations)
