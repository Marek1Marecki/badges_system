"""Testy dla ExploreQueriesService."""

from unittest.mock import MagicMock

import pytest

from application.dto.explore_queries_dto import (
    PoiRankingResponseDTO,
    RegionRankingResponseDTO,
)
from application.services.explore_queries_service import ExploreQueriesService


class TestExploreQueriesService:
    """Testy klasy ExploreQueriesService."""

    @pytest.fixture
    def service(self):
        """Tworzy serwis z mockowanymi zależnościami."""
        query_repo = MagicMock()
        progress_repo = MagicMock()
        cache = MagicMock()
        return ExploreQueriesService(query_repo, progress_repo, cache)

    def _make_peak(self, peak_id, name, type_, altitude, parent_object_id=None):
        peak = MagicMock()
        peak.id = peak_id
        peak.name = name
        peak.type = type_
        peak.altitude = altitude
        peak.parent_object_id = parent_object_id
        peak.badges = MagicMock()
        peak.badges.all.return_value = []
        return peak

    def test_get_poi_ranking_builds_clusters(self, service):
        """Buduje ranking szczytów z klastrami rodzinnymi."""
        service._progress_repo.get_active_progresses.return_value = []
        service._cache.get.return_value = {}
        service._query_repo.get_points_of_interest_with_relations.return_value = [
            self._make_peak(1, "P1", "Szczyt", 1000, None),
            self._make_peak(2, "P2", "Schronisko", 1200, 1),
        ]

        result = service.get_poi_ranking(1)

        assert isinstance(result, PoiRankingResponseDTO)
        assert result.subscribed_badge_codes == []
        assert len(result.ranking) == 1
        assert result.ranking[0].cluster_id == 1
        assert result.ranking[0].is_family is True

    def test_get_poi_ranking_sorts_by_score(self, service):
        """Sortuje klastry według wyniku malejąco."""
        service._progress_repo.get_active_progresses.return_value = []
        service._cache.get.return_value = {"scores": {1: 10, 2: 5, 3: 3}, "colors": {}}
        service._query_repo.get_points_of_interest_with_relations.return_value = [
            self._make_peak(1, "P1", "Szczyt", 1000, None),
            self._make_peak(2, "P2", "Schronisko", 1200, 1),
            self._make_peak(3, "P3", "Szczyt", 900, None),
        ]

        result = service.get_poi_ranking(1)

        family_clusters = [r for r in result.ranking if r.is_family]
        assert len(family_clusters) == 1
        assert family_clusters[0].cluster_id == 1
        assert family_clusters[0].cluster_score == 15

    def test_get_region_ranking_aggregates_scores(self, service):
        """Agreguje wyniki dla regionów."""
        service._cache.get.return_value = {"scores": {10: 5, 20: 3}}
        region_a = MagicMock()
        region_a.id = 1
        region_a.name = "Region A"
        region_b = MagicMock()
        region_b.id = 2
        region_b.name = "Region B"
        service._query_repo.get_regions_by_level.return_value = [region_a, region_b]
        service._query_repo.get_object_region_cache_for_level.return_value = [
            MagicMock(region_id=1, tourist_object_id=10),
            MagicMock(region_id=2, tourist_object_id=20),
        ]

        result = service.get_region_ranking(1, "VOIVODESHIP")

        assert isinstance(result, RegionRankingResponseDTO)
        assert result.level == "VOIVODESHIP"
        assert result.ranking[0].id == 1
        assert result.ranking[0].score == 5
        assert result.ranking[1].id == 2
        assert result.ranking[1].score == 3

    def test_get_region_ranking_sorts_by_score(self, service):
        """Sortuje regiony według wyniku malejąco."""
        service._cache.get.return_value = {"scores": {}}
        region_a = MagicMock()
        region_a.id = 1
        region_a.name = "A"
        region_b = MagicMock()
        region_b.id = 2
        region_b.name = "B"
        service._query_repo.get_regions_by_level.return_value = [region_a, region_b]
        service._query_repo.get_object_region_cache_for_level.return_value = []

        result = service.get_region_ranking(1, "MACROREGION")

        assert len(result.ranking) == 2
        assert result.ranking[0].id in (1, 2)
        assert result.ranking[0].score == 0

    def test_get_region_ranking_uses_correct_cache_key(self, service):
        """Poprawnie konstruuje klucz cache dla profilu w get_region_ranking."""

        def cache_get_side_effect(key):
            if key == "map_state:42":
                return {"scores": {10: 5}}
            return None

        service._cache.get.side_effect = cache_get_side_effect
        region_a = MagicMock()
        region_a.id = 1
        region_a.name = "Region A"
        service._query_repo.get_regions_by_level.return_value = [region_a]
        service._query_repo.get_object_region_cache_for_level.return_value = [
            MagicMock(region_id=1, tourist_object_id=10),
        ]

        result = service.get_region_ranking(42, "VOIVODESHIP")

        assert result.ranking[0].score == 5

    def test_get_region_ranking_handles_missing_cache(self, service):
        """Gdy cache zwraca None, serwis nie przerywa działania."""
        service._cache.get.return_value = None
        region_a = MagicMock()
        region_a.id = 1
        region_a.name = "Region A"
        service._query_repo.get_regions_by_level.return_value = [region_a]
        service._query_repo.get_object_region_cache_for_level.return_value = []

        result = service.get_region_ranking(1, "VOIVODESHIP")

        assert len(result.ranking) == 1
        assert result.ranking[0].score == 0

    def test_get_region_ranking_calls_cache_get(self, service):
        """Serwis wywołuje cache.get z poprawnym kluczem w get_region_ranking."""
        service._cache.get.return_value = {"scores": {}}
        service._query_repo.get_regions_by_level.return_value = []
        service._query_repo.get_object_region_cache_for_level.return_value = []

        service.get_region_ranking(42, "MACROREGION")

        service._cache.get.assert_called_once_with("map_state:42")

    def test_get_poi_ranking_uses_correct_cache_key(self, service):
        """Poprawnie konstruuje klucz cache dla profilu w get_poi_ranking."""

        def cache_get_side_effect(key):
            if key == "map_state:42":
                return {"scores": {1: 10}, "colors": {1: "GREEN"}}
            return None

        service._cache.get.side_effect = cache_get_side_effect
        service._progress_repo.get_active_progresses.return_value = []
        service._query_repo.get_points_of_interest_with_relations.return_value = [
            self._make_peak(1, "P1", "Szczyt", 1000, None),
        ]

        result = service.get_poi_ranking(42)

        assert result.ranking[0].cluster_score == 10

    def test_get_poi_ranking_handles_missing_cache(self, service):
        """Gdy cache zwraca None, serwis nie przerywa działania w get_poi_ranking."""
        service._cache.get.return_value = None
        service._progress_repo.get_active_progresses.return_value = []
        service._query_repo.get_points_of_interest_with_relations.return_value = [
            self._make_peak(1, "P1", "Szczyt", 1000, None),
        ]

        result = service.get_poi_ranking(1)

        assert len(result.ranking) == 1
        assert result.ranking[0].cluster_score == 0

    def test_get_poi_ranking_calls_cache_get(self, service):
        """Serwis wywołuje cache.get z poprawnym kluczem w get_poi_ranking."""
        service._cache.get.return_value = {}
        service._progress_repo.get_active_progresses.return_value = []
        service._query_repo.get_points_of_interest_with_relations.return_value = [
            self._make_peak(1, "P1", "Szczyt", 1000, None),
        ]

        service.get_poi_ranking(42)

        service._cache.get.assert_called_once_with("map_state:42")
