"""Wstrzykiwanie zależności i konfiguracja kontenera (Dependency Injection).

Punkt spinający adaptery infrastruktury z przypadkami użycia z warstwy aplikacji.
Zwraca teraz formalny, typowany obiekt AppContainer zamiast generycznego słownika,
dzięki czemu Mypy gwarantuje bezpieczeństwo typów we wszystkich widokach i taskach (Eliminacja String-Keys).
"""

from dataclasses import dataclass

from application.services.explore_queries_service import ExploreQueriesService
from application.services.poi_scoring_service import PoiScoringService
from application.use_cases.advance_logistic_status import AdvanceLogisticStatusUseCase
from application.use_cases.analyze_gpx_track import AnalyzeGpxTrackUseCase
from application.use_cases.build_tourist_region_geometry import BuildTouristRegionGeometryUseCase
from application.use_cases.bulk_log_ascents import BulkLogAscentsUseCase
from application.use_cases.calculate_object_regions import CalculateObjectRegionsUseCase
from application.use_cases.explore_map import ExploreMapUseCase
from application.use_cases.fetch_badge_news import FetchBadgeNewsUseCase
from application.use_cases.fetch_osm_data import FetchOsmDataUseCase, RunOsmNightWatchmanUseCase
from application.use_cases.get_mvt_tile import GetMvtTileUseCase
from application.use_cases.log_ascent import LogAscentUseCase
from application.use_cases.scan_proximity_candidates import ScanProximityCandidatesUseCase
from application.use_cases.start_badge_progress import StartBadgeProgressUseCase
from application.use_cases.unsubscribe_badge import UnsubscribeBadgeUseCase
from application.use_cases.verify_badge import VerifyBadgeUseCase
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
from infrastructure.adapters.persistence.django_tourist_repo import DjangoTouristRepository


@dataclass(frozen=True)
class AppContainer:
    """Centralny rejestr zainstancjonowanych Use Case'ów i Serwisów."""

    analyze_gpx_track: AnalyzeGpxTrackUseCase
    advance_logistic_status: AdvanceLogisticStatusUseCase
    bulk_log_ascents: BulkLogAscentsUseCase
    calculate_object_regions: CalculateObjectRegionsUseCase
    build_tourist_region_geometry: BuildTouristRegionGeometryUseCase
    explore_map: ExploreMapUseCase
    fetch_badge_news: FetchBadgeNewsUseCase
    fetch_osm_data: FetchOsmDataUseCase
    run_osm_night_watchman: RunOsmNightWatchmanUseCase
    get_mvt_tile: GetMvtTileUseCase
    log_ascent: LogAscentUseCase
    scan_proximity_candidates: ScanProximityCandidatesUseCase
    start_badge_progress: StartBadgeProgressUseCase
    unsubscribe_badge: UnsubscribeBadgeUseCase
    verify_badge: VerifyBadgeUseCase
    poi_scoring_service: PoiScoringService
    explore_queries_service: ExploreQueriesService


_container_instance: AppContainer | None = None


def build_container() -> AppContainer:
    """Inicjalizuje wszystkie adaptery i wstrzykuje je do Use Case'ów."""
    global _container_instance
    if _container_instance is not None:
        return _container_instance

    clock = SystemClock()
    cache_adapter = DjangoCacheAdapter()

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
    tourist_repo = DjangoTouristRepository()

    # gpx_parser = ElementTreeGpxParser()
    news_scraper = BeautifulSoupNewsScraper()

    # NOWE: UoW i Event Publisher
    uow = DjangoUnitOfWork()
    event_publisher = CeleryEventPublisher()

    # PoiScoringService (Naprawa argumentów z błędu Mypy)
    poi_scoring_service = PoiScoringService(
        badge_repository=badge_repo,
        progress_repository=tourist_repo,
        ascent_repository=tourist_repo,
        profile_repository=tourist_repo,
        cache=cache_adapter,
        clock=clock,
    )
    explore_queries_service = ExploreQueriesService(
        query_repository=explore_query_repo,
        progress_repository=tourist_repo,
        cache=cache_adapter,
    )

    _container_instance = AppContainer(
        analyze_gpx_track=AnalyzeGpxTrackUseCase(map_repository=map_repo, gpx_parser=gpx_parser),
        advance_logistic_status=AdvanceLogisticStatusUseCase(
            progress_repository=tourist_repo,
        ),
        bulk_log_ascents=BulkLogAscentsUseCase(
            ascent_repository=tourist_repo,
            clock=clock,
            uow=uow,
            event_publisher=event_publisher,
        ),
        calculate_object_regions=CalculateObjectRegionsUseCase(region_cache_repository=region_cache_repo, clock=clock),
        build_tourist_region_geometry=BuildTouristRegionGeometryUseCase(geometry_repository=region_geom_repo),
        explore_map=ExploreMapUseCase(map_repository=map_repo, cache=cache_adapter),
        fetch_badge_news=FetchBadgeNewsUseCase(scraper=news_scraper, repository=news_repo),
        fetch_osm_data=FetchOsmDataUseCase(osm_repository=osm_repo, clock=clock),
        run_osm_night_watchman=RunOsmNightWatchmanUseCase(osm_repository=osm_repo, clock=clock),
        get_mvt_tile=GetMvtTileUseCase(mvt_repository=mvt_repo, cache=cache_adapter),
        log_ascent=LogAscentUseCase(
            ascent_repository=tourist_repo,
            profile_repository=tourist_repo,
            poi_service=poi_scoring_service,
            clock=clock,
            uow=uow,
            event_publisher=event_publisher,
        ),
        scan_proximity_candidates=ScanProximityCandidatesUseCase(proximity_repository=proximity_repo),
        start_badge_progress=StartBadgeProgressUseCase(
            progress_repository=tourist_repo,
            ascent_repository=tourist_repo,
            badge_repository=badge_repo,
            profile_repository=tourist_repo,
            clock=clock,
            uow=uow,
            event_publisher=event_publisher,
        ),
        unsubscribe_badge=UnsubscribeBadgeUseCase(
            progress_repository=tourist_repo,
            uow=uow,
            event_publisher=event_publisher,
        ),
        verify_badge=VerifyBadgeUseCase(
            progress_repository=tourist_repo,
            ascent_repository=tourist_repo,
            profile_repository=tourist_repo,
            badge_repository=badge_repo,
            clock=clock,
        ),
        poi_scoring_service=poi_scoring_service,
        explore_queries_service=explore_queries_service,
    )

    return _container_instance


def get_container() -> AppContainer:
    return build_container()


def reset_container() -> None:
    global _container_instance
    _container_instance = None


configure_app = build_container
