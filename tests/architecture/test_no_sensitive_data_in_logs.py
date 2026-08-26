"""Testy architektury: wykrywanie potencjalnego logowania wrażliwych danych."""

import ast
from pathlib import Path

import pytest

SENSITIVE_KEYWORDS = {
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "credentials",
    "private_key",
    "session_id",
    "session_token",
    "session_key",
}


def _collect_log_calls(module: Path) -> list[tuple[int, str]]:
    """Zwraca listę (linia, komunikat) dla wywołań logger.info/warning/error/exception."""
    tree = ast.parse(module.read_text(encoding="utf-8"))
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in {"info", "warning", "error", "exception", "debug"}:
                if isinstance(func.value, ast.Name) and func.value.id == "logger":
                    args = node.args
                    if args and isinstance(args[0], ast.Constant) and isinstance(args[0].value, str):
                        message = args[0].value.lower()
                        for keyword in SENSITIVE_KEYWORDS:
                            if keyword in message:
                                hits.append((node.lineno, message))
                                break
    return hits


@pytest.fixture()
def application_modules() -> list[Path]:
    modules = []
    for path in [Path("application"), Path("infrastructure"), Path("apps")]:
        if path.exists():
            modules.extend(path.rglob("*.py"))
    return modules


def test_no_sensitive_data_in_log_messages(application_modules: list[Path]) -> None:
    """Logi nie powinien zawierać wrażliwych słów kluczowych w komunikatach."""
    violations = []
    for module in application_modules:
        hits = _collect_log_calls(module)
        for lineno, message in hits:
            violations.append(f"{module}:{lineno}: {message}")
    assert not violations, "Wykryto potencjalne logowanie wrażliwych danych:\n" + "\n".join(violations)