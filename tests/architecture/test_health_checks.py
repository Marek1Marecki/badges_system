"""Testy architektury: wszystkie kontenery aplikacyjne muszą mieć healthcheck."""

from pathlib import Path

import pytest
import yaml

COMPOSE_DIR = Path(".")
COMPOSE_FILES = [
    "compose.yml",
    "compose.prod.yml",
    "compose.test.yml",
    "compose.e2e.yml",
    "compose.preprod.yml",
    "compose.override.yml",
]
EXEMPT_SERVICES = {"db", "redis"}


def _get_services_without_healthcheck(compose_file: Path) -> list[str]:
    """Zwraca listę nazw services bez healthcheck w danym compose pliku."""
    with open(compose_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        return []

    services = data.get("services", {})
    if not isinstance(services, dict):
        return []

    services_without_healthcheck = []
    for service_name, service_config in services.items():
        if service_name in EXEMPT_SERVICES:
            continue
        if not isinstance(service_config, dict):
            continue
        if "healthcheck" not in service_config:
            services_without_healthcheck.append(service_name)

    return services_without_healthcheck


@pytest.fixture()
def compose_files() -> list[Path]:
    return [COMPOSE_DIR / f for f in COMPOSE_FILES if (COMPOSE_DIR / f).exists()]


def test_all_application_services_have_healthcheck(compose_files: list[Path]) -> None:
    """Wszystkie kontenery aplikacyjne muszą mieć healthcheck."""
    violations = []
    for compose_file in compose_files:
        services = _get_services_without_healthcheck(compose_file)
        if services:
            violations.append(f"{compose_file}: {services}")
    assert not violations, "Services bez healthcheck:\n" + "\n".join(violations)
