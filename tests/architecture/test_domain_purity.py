"""Testy architektury: Domain purity."""

import ast
from pathlib import Path

import pytest


@pytest.fixture()
def domain_modules() -> list[Path]:
    return list(Path("domain").rglob("*.py"))


def test_domain_has_no_django_models(domain_modules: list[Path]) -> None:
    """Domain nie może zawierać modeli Django ORM."""
    violations = []
    for module in domain_modules:
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Attribute):
                        if base.attr == "Model":
                            violations.append(f"{module}: klasa {node.name} dziedziczy po Model")
                    elif isinstance(base, ast.Name):
                        if base.id == "Model":
                            violations.append(f"{module}: klasa {node.name} dziedziczy po Model")
    assert not violations, "Domain zawiera modele Django:\n" + "\n".join(violations)
