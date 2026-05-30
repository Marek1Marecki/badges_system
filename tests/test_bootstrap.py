"""Testy jednostkowe dla kontenera DI.

Sprawdzamy że kontener poprawnie buduje use case'y i że reset_container()
zapewnia izolację między testami.

Testy NIE uderzają w bazę — używają FakeBadgeRepository (priorytet 4).
Do czasu powstania fakes/ sprawdzamy tylko strukturę kontenera.
"""

import pytest

from application.use_cases.verify_badge import VerifyBadgeUseCase
from bootstrap import build_container, get_container, reset_container


@pytest.fixture(autouse=True)
def clean_container() -> None:
    """Resetuje kontener przed każdym testem — izolacja stanu globalnego."""
    reset_container()
    yield
    reset_container()


@pytest.mark.integration
def test_build_container_returns_verify_badge_use_case() -> None:
    """Kontener zawiera klucz 'verify_badge' z poprawnym typem."""
    container = build_container()
    assert "verify_badge" in container
    assert isinstance(container["verify_badge"], VerifyBadgeUseCase)


@pytest.mark.integration
def test_get_container_is_lazy_singleton() -> None:
    """get_container() zwraca ten sam obiekt przy kolejnych wywołaniach."""
    container_first = get_container()
    container_second = get_container()
    assert container_first is container_second


@pytest.mark.integration
def test_reset_container_clears_singleton() -> None:
    """reset_container() wymusza odbudowanie kontenera przy następnym wywołaniu."""
    container_first = get_container()
    reset_container()
    container_second = get_container()
    # Po resecie to nowy obiekt — nie ten sam
    assert container_first is not container_second
