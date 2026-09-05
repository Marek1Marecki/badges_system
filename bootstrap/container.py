"""Wstrzykiwanie zależności i konfiguracja kontenera (Dependency Injection).

Punkt spinający adaptery infrastruktury z przypadkami użycia z warstwy aplikacji.
Po refaktoryzacji AUDYT-065 logika budowy jest podzielona:
- `adapters_factory.py` — inicjalizacja adaptery infrastruktury,
- `usecase_factory.py` — budowa Use Case'ów i serwisów,
- `container.py` — tylko singleton i dostęp (Composition Root).

Zwraca formalny, typowany obiekt `AppContainer` zamiast generycznego
słownika, dzięki czemu Mypy gwarantuje bezpieczeństwo typów we wszystkich
widokach i taskach (Eliminacja String-Keys).
"""

from bootstrap.adapters_factory import create_adapters
from bootstrap.app_container import AppContainer
from bootstrap.usecase_factory import create_usecases

_container_instance: AppContainer | None = None


def build_container() -> AppContainer:
    """Inicjalizuje wszystkie adaptery i wstrzykuje je do Use Case'ów.

    Logika podzielona na fabryki (AUDYT-065):
    1. `create_adapters()` — buduje adaptery infrastruktury (ORM, cache, itp.).
    2. `create_usecases()` — kompiluje Use Case'y i serwisy z adapterami.
    """
    global _container_instance
    if _container_instance is not None:
        return _container_instance

    adapters = create_adapters()
    _container_instance = create_usecases(adapters)
    return _container_instance


def get_container() -> AppContainer:
    """Zwraca instancję kontenera DI (singleton)."""
    return build_container()


def reset_container() -> None:
    """Resetuje stan kontenera DI (głównie dla testów)."""
    global _container_instance
    _container_instance = None


configure_app = build_container
