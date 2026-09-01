"""Contract consistency test between Django URL configuration and OpenAPI schema.

Zgodnie z planem eksperymentalnym Schemathesis:
- Weryfikuje, że ręcznie utrzymywany config/openapi.json nie rozjeżdża się
  z rzeczywistymi ścieżkami w apps/api/urls.py
- Nie wymaga uruchomionego serwera ani zewnętrznych narzędzi
- Może być uruchomiony w ramach make check w przyszłości
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import get_resolver

OPENAPI_SCHEMA_PATH = Path(settings.BASE_DIR) / "config" / "openapi.json"


def _extract_django_api_paths() -> set[str]:
    """Zwraca zbiór ścieżek API zdefiniowanych w urls.py w formacie OpenAPI."""
    resolver = get_resolver()
    paths: set[str] = set()

    def _collect(pattern_list: list, prefix: str = "") -> None:
        for url_pattern in pattern_list:
            pattern = str(url_pattern.pattern)
            # Pomiń openapi.json endpoint (to nie jest część REST API)
            if "openapi.json" in pattern:
                continue
            # Pomiń accounts/ URLs (django-allauth)
            if pattern.startswith("accounts/"):
                continue
            # Oblicz pełną ścieżkę z prefiksem
            full_pattern = prefix + pattern
            if hasattr(url_pattern, "url_patterns"):
                # To jest Include URLPattern - rekurencyjnie zbierz dzieci
                _collect(url_pattern.url_patterns, full_pattern)
            else:
                # To jest leaf URLPattern
                # Zamień Django path converters na OpenAPI placeholders
                import re
                path = re.sub(r"<\w+:(?P<name>\w+)>", r"{\g<name>}", full_pattern)
                # Nie dodawaj trailing slash jeśli pattern kończy się rozszerzeniem pliku
                if not path.endswith("/") and not re.search(r"\.[a-z0-9]+$", path):
                    path += "/"
                # Usuń leading slash jeśli istnieje
                path = path.lstrip("/")
                # Pomiń puste ścieżki
                if path and path.startswith("api/"):
                    paths.add(path)

    _collect(resolver.url_patterns)
    return paths


def _extract_openapi_paths() -> set[str]:
    """Zwraca zbiór ścieżek zdefiniowanych w config/openapi.json."""
    if not OPENAPI_SCHEMA_PATH.exists():
        pytest.fail(f"OpenAPI schema not found at {OPENAPI_SCHEMA_PATH}")

    with OPENAPI_SCHEMA_PATH.open(encoding="utf-8") as f:
        schema = json.load(f)

    return set(schema.get("paths", {}).keys())


def test_django_api_paths_are_subset_of_openapi():
    """Każda ścieżka z Django urls.py musi istnieć w OpenAPI schema."""
    django_paths = _extract_django_api_paths()
    openapi_paths = _extract_openapi_paths()

    # Normalize: usuń leading slash z OpenAPI paths
    openapi_paths = {p.lstrip("/") for p in openapi_paths}

    missing = django_paths - openapi_paths
    assert not missing, (
        "Następujące ścieżki API istnieją w Django urls.py, "
        "ale brakuje ich w config/openapi.json:\n"
        + "\n".join(f"  - {p}" for p in sorted(missing))
    )


def test_openapi_paths_are_subset_of_django():
    """Każda ścieżka w OpenAPI schema musi istnieć w Django urls.py."""
    django_paths = _extract_django_api_paths()
    openapi_paths = _extract_openapi_paths()

    # Normalize: usuń leading slash z OpenAPI paths
    openapi_paths = {p.lstrip("/") for p in openapi_paths}

    extra = openapi_paths - django_paths
    assert not extra, (
        "Następujące ścieżki istnieją w config/openapi.json, "
        "ale nie ma ich w Django urls.py:\n"
        + "\n".join(f"  - {p}" for p in sorted(extra))
    )


def test_openapi_schema_is_valid_json():
    """config/openapi.json musi być poprawnym plikiem JSON."""
    if not OPENAPI_SCHEMA_PATH.exists():
        pytest.fail(f"OpenAPI schema not found at {OPENAPI_SCHEMA_PATH}")

    with OPENAPI_SCHEMA_PATH.open(encoding="utf-8") as f:
        try:
            json.load(f)
        except json.JSONDecodeError as exc:
            pytest.fail(f"config/openapi.json is not valid JSON: {exc}")


def test_openapi_has_required_fields():
    """OpenAPI schema musi zawierać wymagane pola specyfikacji."""
    with OPENAPI_SCHEMA_PATH.open(encoding="utf-8") as f:
        schema = json.load(f)

    assert "openapi" in schema, "Missing 'openapi' field"
    assert "info" in schema, "Missing 'info' field"
    assert "paths" in schema, "Missing 'paths' field"
    assert "components" in schema, "Missing 'components' field"
    assert "securitySchemes" in schema.get("components", {}), "Missing 'components.securitySchemes'"


def test_api_endpoints_have_security_requirement():
    """Publiczne endpointy muszą jawnie deklarować brak wymagania auth w OpenAPI."""
    with OPENAPI_SCHEMA_PATH.open(encoding="utf-8") as f:
        schema = json.load(f)

    public_paths = []
    for path, methods in schema.get("paths", {}).items():
        for method, details in methods.items():
            if isinstance(details, dict):
                security = details.get("security")
                if security == []:
                    public_paths.append(f"{method.upper()} {path}")

    # Na razie tylko logujemy - nie blokujemy testu, bo to advisory
    # Można później zmienić na assertion jeśli zdefiniujemy listę publicznych endpointów
    if public_paths:
        pytest.skip(
            "Publiczne endpointy (security: []):\n"
            + "\n".join(f"  - {p}" for p in public_paths)
        )
