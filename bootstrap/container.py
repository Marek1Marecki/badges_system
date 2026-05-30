"""Kontener zależności (Dependency Injection)."""

from __future__ import annotations

_container: dict | None = None


def configure_app() -> None:
    """Inicjalizuje logowanie i waliduje konfigurację przy starcie."""
    from infrastructure.config import AppSettings
    from infrastructure.logging import configure_logging

    settings = AppSettings()
    configure_logging(json_mode=settings.log_json, level=settings.log_level)


def build_container() -> dict:
    """Buduje kontener zależności — adaptery wstrzyknięte do use case'ów."""
    from application.use_cases.build_tourist_region_geometry import BuildTouristRegionGeometryUseCase
    from application.use_cases.calculate_object_regions import CalculateObjectRegionsUseCase
    from application.use_cases.fetch_osm_data import FetchOsmDataUseCase, RunOsmNightWatchmanUseCase
    from application.use_cases.scan_proximity_candidates import ScanProximityCandidatesUseCase
    from application.use_cases.verify_badge import VerifyBadgeUseCase
    from infrastructure.adapters.clock import SystemClock
    from infrastructure.adapters.osm_repository import OsmRepository
    from infrastructure.adapters.persistence.django_badge_repo import DjangoBadgeRepository
    from infrastructure.adapters.persistence.region_cache_repo import RegionCacheRepository

    clock = SystemClock()
    badge_repository = DjangoBadgeRepository()
    region_cache_repository = RegionCacheRepository()
    osm_repository = OsmRepository()

    return {
        "verify_badge": VerifyBadgeUseCase(
            repository=badge_repository,
        ),
        "fetch_osm_data": FetchOsmDataUseCase(
            osm_repository=osm_repository,
            clock=clock,
        ),
        "calculate_object_regions": CalculateObjectRegionsUseCase(
            region_cache_repository=region_cache_repository,
            clock=clock,
        ),
        "build_tourist_region_geometry": BuildTouristRegionGeometryUseCase(
            region_cache_repository=region_cache_repository,
        ),
        "scan_proximity_candidates": ScanProximityCandidatesUseCase(
            region_cache_repository=region_cache_repository,
        ),
        "run_osm_night_watchman": RunOsmNightWatchmanUseCase(
            osm_repository=osm_repository,
            clock=clock,
        ),
    }


def get_container() -> dict:
    """Lazy singleton — zwraca kontener, buduje go przy pierwszym wywołaniu."""
    global _container
    if _container is None:
        _container = build_container()
    return _container


def reset_container() -> None:
    """Resetuje kontener — używane wyłącznie w testach."""
    global _container
    _container = None
