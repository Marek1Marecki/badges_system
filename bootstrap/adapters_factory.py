"""Fabryka adapterów infrastruktury dla kontenera DI.

Rozdziela budowę obiektów infrastruktury (adaptery ORM, parsery, itp.) od
logiki inicjalizacji Use Case'ów, redukując rozmiar monolithu
`build_container()` w `bootstrap/container.py` (AUDYT-065).

Wzorzec: `create_adapters()` zwraca nazwany tuple `Adapters` zawierający
wszystkie gotowe do użycz do adaptery.
"""

from dataclasses import dataclass

from infrastructure.adapters.celery_event_publisher import CeleryEventPublisher
from infrastructure.adapters.clock import SystemClock
from infrastructure.adapters.django_cache import DjangoCacheAdapter
from infrastructure.adapters.django_uow import DjangoUnitOfWork
from infrastructure.adapters.gpx_parser import DjangoGpxParser
from infrastructure.adapters.news_scraper import BeautifulSoupNewsScraper
from infrastructure.adapters.osm_repository import OsmRepository
from infrastructure.adapters.persistence.django_badge_repo import DjangoBadgeRepository
from infrastructure.adapters.persistence.django_explore_queries_repo import DjangoExploreQueriesRepository
from infrastructure.adapters.persistence.django_map_repo import DjangoMapRepository
from infrastructure.adapters.persistence.django_mvt_repo import DjangoMvtRepository
from infrastructure.adapters.persistence.django_news_repo import DjangoNewsRepository
from infrastructure.adapters.persistence.django_proximity_repo import DjangoProximityRepository
from infrastructure.adapters.persistence.django_region_cache_repo import DjangoRegionCacheRepository
from infrastructure.adapters.persistence.django_region_geometry_repo import DjangoTouristRegionGeometryRepository
from infrastructure.adapters.persistence.django_tourist_repo import (
    DjangoAscentLogRepository,
    DjangoTouristProfileRepository,
    DjangoUserProgressRepository,
)


@dataclass(frozen=True)
class Adapters:
    """Wszystkie adaptery infrastruktury, gotowe do wstrzyknięcia do Use Case'ów."""

    clock: SystemClock
    cache: DjangoCacheAdapter
    badge_repo: DjangoBadgeRepository
    explore_query_repo: DjangoExploreQueriesRepository
    gpx_parser: DjangoGpxParser
    map_repo: DjangoMapRepository
    mvt_repo: DjangoMvtRepository
    news_repo: DjangoNewsRepository
    news_scraper: BeautifulSoupNewsScraper
    osm_repo: OsmRepository
    region_cache_repo: DjangoRegionCacheRepository
    region_geom_repo: DjangoTouristRegionGeometryRepository
    proximity_repo: DjangoProximityRepository
    profile_repo: DjangoTouristProfileRepository
    ascent_repo: DjangoAscentLogRepository
    progress_repo: DjangoUserProgressRepository
    uow: DjangoUnitOfWork
    event_publisher: CeleryEventPublisher


def create_adapters() -> Adapters:
    """Tworzy i inicjalizuje wszystkie adaptery infrastruktury.

    Centralizuje budowę obiektów warstwy infrastruktury, dzięki czemu
    `build_container()` w `container.py` skupia się wyłącznie na
    kompozycji Use Case'ów (Composition Root).
    """
    clock = SystemClock()
    cache = DjangoCacheAdapter()
    badge_repo = DjangoBadgeRepository()
    explore_query_repo = DjangoExploreQueriesRepository()
    gpx_parser = DjangoGpxParser()
    map_repo = DjangoMapRepository()
    mvt_repo = DjangoMvtRepository()
    news_repo = DjangoNewsRepository()
    osm_repo = OsmRepository()
    region_cache_repo = DjangoRegionCacheRepository()
    region_geom_repo = DjangoTouristRegionGeometryRepository()
    proximity_repo = DjangoProximityRepository()
    profile_repo = DjangoTouristProfileRepository()
    ascent_repo = DjangoAscentLogRepository()
    progress_repo = DjangoUserProgressRepository()
    uow = DjangoUnitOfWork()
    event_publisher = CeleryEventPublisher()
    news_scraper = BeautifulSoupNewsScraper()

    return Adapters(
        clock=clock,
        cache=cache,
        badge_repo=badge_repo,
        explore_query_repo=explore_query_repo,
        gpx_parser=gpx_parser,
        map_repo=map_repo,
        mvt_repo=mvt_repo,
        news_repo=news_repo,
        news_scraper=news_scraper,
        osm_repo=osm_repo,
        region_cache_repo=region_cache_repo,
        region_geom_repo=region_geom_repo,
        proximity_repo=proximity_repo,
        profile_repo=profile_repo,
        ascent_repo=ascent_repo,
        progress_repo=progress_repo,
        uow=uow,
        event_publisher=event_publisher,
    )
