"""Definicja AppContainer — centralnego rejestru Use Case'ów i Serwisów.

Oddzielenie dataclass od logiki budowy (AUDYT-065) umożliwia
`adapters_factory.py` i `usecase_factory.py` importowanie tej klasy
bez tworzenia cyklu importowego z `container.py`.
"""

from dataclasses import dataclass

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


@dataclass(frozen=True)
class AppContainer:
    """Centralny rejestr zainstancjonowanych Use Case'ów i Serwisów.

    Płaska struktura (każdy Use Case dostępny jako atrybut) zapewnia
    bezpieczeństwo typów Mypy w widokach i taskach oraz kompatybilność
    ze wzorcem kompozycji używanym w testach (`UseCaseContainer`).
    """

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
    evaluate_badge_progress: EvaluateBadgeProgressQuery
    update_badge_progress: UpdateBadgeProgressCommand
    poi_scoring_service: PoiScoringService
    explore_queries_service: ExploreQueriesService
    bitemporal_validation_service: BitemporalValidationService
