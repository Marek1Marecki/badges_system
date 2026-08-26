"""Testy architektury: zapobieganie plikom z nadmierną liczbą modeli (God Class)."""

import ast
from pathlib import Path

import pytest

MODELS_DIR = Path("apps")
MODEL_THRESHOLD = 20


def _count_models_in_file(file_path: Path) -> int:
    """Liczy liczbę klas dziedziczących po klasie o nazwie kończącej się na 'Model'."""
    content = file_path.read_text(encoding="utf-8")
    tree = ast.parse(content)
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                base_name = ast.unparse(base)
                if base_name.endswith("Model"):
                    count += 1
                    break
    return count


@pytest.fixture()
def model_files() -> list[tuple[Path, int]]:
    files = []
    for app_dir in MODELS_DIR.iterdir():
        if not app_dir.is_dir():
            continue
        models_file = app_dir / "models.py"
        if models_file.exists():
            count = _count_models_in_file(models_file)
            files.append((models_file, count))
    return files


def test_no_god_class_models_file(model_files: list[tuple[Path, int]]) -> None:
    """Żaden plik models.py nie powinien przekraczać progu liczby modeli."""
    violations = []
    for file_path, count in model_files:
        if count > MODEL_THRESHOLD:
            violations.append(f"{file_path}: {count} modeli (próg: {MODEL_THRESHOLD})")
    assert not violations, "Pliki models.py przekraczają limit modeli:\n" + "\n".join(violations)
