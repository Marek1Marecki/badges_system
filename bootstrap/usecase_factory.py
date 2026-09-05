"""Fabryka Use Case'ów i serwisów aplikacji dla kontenera DI.

Rozdziela budowę serwisów i use-case'ów od inicjalizacji adapterów infrastruktury,
redukując rozmiar monolithu `build_container()` w `bootstrap/container.py`
(AUDYT-065).

Wzorzec: `create_usecases()` przyjmuje `Adapters` i zwraca gotowy
`AppContainer` z wszystkimi zarejestrowanymi Use Case'ami i Serwisami.
"""

from application.services.bitemporal_validation_service import BitemporalValidationService
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
from application.use_cases.verify_badge import EvaluateBadgeProgressQuery, UpdateBadgeProgressCommand
from bootstrap.adapters_factory import Adapters
from bootstrap.app_container import AppContainer
from domain.services.badge_awarding_domain_service import BadgeAwardingDomainService


def create_usecases(adapters: Adapters) -> AppContainer:
    """Buduje wszystkie Use Case'y i serwisy aplikacji z podanymi adapterami.

    Args:
      adapters: Adapters: Gotowe adaptery infrastruktury (z `create_adapters()`).

    Returns:
      AppContainer: W pełni skonfigurowany kontener DI.
    """
    # Serwisy aplikacyjne
    poi_scoring_service = PoiScoringService(
        badge_repository=adapters.badge_repo,
        progress_repository=adapters.progress_repo,
        ascent_repository=adapters.ascent_repo,
        profile_repository=adapters.profile_repo,
        cache=adapters.cache,
        clock=adapters.clock,
    )
    explore_queries_service = ExploreQueriesService(
        query_repository=adapters.explore_query_repo,
        progress_repository=adapters.progress_repo,
        cache=adapters.cache,
    )
    bitemporal_validation_service = BitemporalValidationService(
        ascent_repo=adapters.ascent_repo,
        clock=adapters.clock,
    )
    awarding_service = BadgeAwardingDomainService()

    return AppContainer(
        analyze_gpx_track=AnalyzeGpxTrackUseCase(map_repository=adapters.map_repo, gpx_parser=adapters.gpx_parser),
        advance_logistic_status=AdvanceLogisticStatusUseCase(
            progress_repository=adapters.progress_repo,
            event_publisher=adapters.event_publisher,
        ),
        bitemporal_validation_service=bitemporal_validation_service,
        bulk_log_ascents=BulkLogAscentsUseCase(
            ascent_repository=adapters.ascent_repo,
            bitemporal_service=bitemporal_validation_service,
            uow=adapters.uow,
            event_publisher=adapters.event_publisher,
        ),
        calculate_object_regions=CalculateObjectRegionsUseCase(
            region_cache_repository=adapters.region_cache_repo, clock=adapters.clock
        ),
        build_tourist_region_geometry=BuildTouristRegionGeometryUseCase(geometry_repository=adapters.region_geom_repo),
        explore_map=ExploreMapUseCase(map_repository=adapters.map_repo, cache=adapters.cache),
        fetch_badge_news=FetchBadgeNewsUseCase(scraper=adapters.news_scraper, repository=adapters.news_repo),
        fetch_osm_data=FetchOsmDataUseCase(osm_repository=adapters.osm_repo, clock=adapters.clock),
        run_osm_night_watchman=RunOsmNightWatchmanUseCase(osm_repository=adapters.osm_repo, clock=adapters.clock),
        get_mvt_tile=GetMvtTileUseCase(mvt_repository=adapters.mvt_repo, cache=adapters.cache),
        log_ascent=LogAscentUseCase(
            ascent_repository=adapters.ascent_repo,
            profile_repository=adapters.profile_repo,
            poi_service=poi_scoring_service,
            bitemporal_service=bitemporal_validation_service,
            clock=adapters.clock,
            uow=adapters.uow,
            event_publisher=adapters.event_publisher,
        ),
        scan_proximity_candidates=ScanProximityCandidatesUseCase(proximity_repository=adapters.proximity_repo),
        start_badge_progress=StartBadgeProgressUseCase(
            progress_repository=adapters.progress_repo,
            ascent_repository=adapters.ascent_repo,
            badge_repository=adapters.badge_repo,
            profile_repository=adapters.profile_repo,
            clock=adapters.clock,
            uow=adapters.uow,
            event_publisher=adapters.event_publisher,
            awarding_service=awarding_service,
        ),
        unsubscribe_badge=UnsubscribeBadgeUseCase(
            progress_repository=adapters.progress_repo,
            uow=adapters.uow,
            event_publisher=adapters.event_publisher,
        ),
        evaluate_badge_progress=EvaluateBadgeProgressQuery(
            progress_repository=adapters.progress_repo,
            ascent_repository=adapters.ascent_repo,
            profile_repository=adapters.profile_repo,
            badge_repository=adapters.badge_repo,
            clock=adapters.clock,
            awarding_service=awarding_service,
        ),
        update_badge_progress=UpdateBadgeProgressCommand(
            query_service=EvaluateBadgeProgressQuery(
                progress_repository=adapters.progress_repo,
                ascent_repository=adapters.ascent_repo,
                profile_repository=adapters.profile_repo,
                badge_repository=adapters.badge_repo,
                clock=adapters.clock,
                awarding_service=awarding_service,
            ),
            progress_repository=adapters.progress_repo,
        ),
        poi_scoring_service=poi_scoring_service,
        explore_queries_service=explore_queries_service,
    )
