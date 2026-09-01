"""Testy architektury: konwencja nazewnictwa DTO."""

import ast
from pathlib import Path

DTO_DIR = Path("application/dto")
ALLOWED_SUFFIXES = ("InputDTO", "RequestDTO", "ResponseDTO")
LEGACY_DTOS = {
    "TouristProfileDTO",
    "BadgeProgressDTO",
    "LogisticStatusUpdateDTO",
    "AscentDTO",
    "GpxAnalysisResultDTO",
    "BulkAscentResultDTO",
    "BadgeCodeNameDTO",
    "RankingItemDTO",
    "RegionRankingItemDTO",
    "ObjectRegionDTO",
    "TouristObjectGeoDTO",
    "BadgeNewsDTO",
}


def _get_dto_classes() -> list[tuple[Path, str]]:
    """Znajduje wszystkie klasy dziedziczące po BaseModel w application/dto/."""
    classes = []
    for module in DTO_DIR.glob("*.py"):
        if module.name == "__init__.py":
            continue
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "BaseModel":
                        classes.append((module, node.name))
                    elif isinstance(base, ast.Attribute) and base.attr == "BaseModel":
                        classes.append((module, node.name))
    return classes


def test_dto_naming_convention() -> None:
    """Nowe DTO powinny kończyć się na InputDTO, RequestDTO lub ResponseDTO."""
    dto_classes = _get_dto_classes()
    violations = []
    for module, class_name in dto_classes:
        if class_name in LEGACY_DTOS:
            continue
        if not any(class_name.endswith(suffix) for suffix in ALLOWED_SUFFIXES):
            violations.append(f"{module}: {class_name}")
    assert not violations, "Nowe DTO nie遵循 konwencji nazewnictwa:\n" + "\n".join(violations)
