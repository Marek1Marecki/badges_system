"""Testy dla ExploreQueriesService."""

from types import SimpleNamespace
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
        service._progress_repo.get_all_unarchived_progresses.return_value = []
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
        service._progress_repo.get_all_unarchived_progresses.return_value = []
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
        service._progress_repo.get_all_unarchived_progresses.return_value = []
        service._query_repo.get_points_of_interest_with_relations.return_value = [
            self._make_peak(1, "P1", "Szczyt", 1000, None),
        ]

        result = service.get_poi_ranking(42)

        assert result.ranking[0].cluster_score == 10

    def test_get_poi_ranking_handles_missing_cache(self, service):
        """Gdy cache zwraca None, serwis nie przerywa działania w get_poi_ranking."""
        service._cache.get.return_value = None
        service._progress_repo.get_all_unarchived_progresses.return_value = []
        service._query_repo.get_points_of_interest_with_relations.return_value = [
            self._make_peak(1, "P1", "Szczyt", 1000, None),
        ]

        result = service.get_poi_ranking(1)

        assert len(result.ranking) == 1
        assert result.ranking[0].cluster_score == 0

    def test_get_poi_ranking_calls_cache_get(self, service):
        """Serwis wywołuje cache.get z poprawnym kluczem w get_poi_ranking."""
        service._cache.get.return_value = {}
        service._progress_repo.get_all_unarchived_progresses.return_value = []
        service._query_repo.get_points_of_interest_with_relations.return_value = [
            self._make_peak(1, "P1", "Szczyt", 1000, None),
        ]

        service.get_poi_ranking(42)

        service._cache.get.assert_called_once_with("map_state:42")

    def test_get_poi_ranking_reads_colors_from_map_state(self, service):
        """Serwis odczytuje kolory z klucza 'colors' w map_state."""
        service._cache.get.return_value = {
            "scores": {},
            "colors": {1: "RED"},
        }
        service._progress_repo.get_all_unarchived_progresses.return_value = []
        service._query_repo.get_points_of_interest_with_relations.return_value = [
            self._make_peak(1, "P1", "Szczyt", 1000, None),
        ]

        result = service.get_poi_ranking(1)

        assert result.ranking[0].items[0]["color"] == "RED"

    def test_get_catalog_badges_delegates_to_repository(self, service):
        entries = [object()]
        service._query_repo.get_catalog_badges.return_value = entries

        result = service.get_catalog_badges(42)

        assert result is entries
        service._query_repo.get_catalog_badges.assert_called_once_with(42)

    def test_get_badge_details_builds_dto(self, service):
        badge = SimpleNamespace(organizer=SimpleNamespace(has_publication_consent=True))
        target_version = object()
        tier_with_image = SimpleNamespace(
            name="Standard",
            required_peaks_count=3,
            badge_image=SimpleNamespace(url="/badges/standard.png"),
        )
        tier_without_image = SimpleNamespace(name="Mini", required_peaks_count=0, badge_image=None)
        obj = SimpleNamespace(id=10, name="Giewont", altitude=1894.0)
        service._query_repo.get_badge_detail_data.return_value = {
            "badge": badge,
            "progress": None,
            "target_version": target_version,
            "tiers": [tier_with_image, tier_without_image],
            "objects": [obj],
        }
        service._cache.get.return_value = {"scores": {10: 7}, "colors": {10: "GREEN"}}

        result = service.get_badge_details("KGP", 42)

        assert result.badge is badge
        assert result.progress is None
        assert result.evaluation is None
        assert result.target_version is target_version
        assert result.has_consent is True
        assert result.objects_list[0].id == 10
        assert result.objects_list[0].score == 7
        assert result.objects_list[0].color == "GREEN"
        assert result.tiers_info[0].required_count == 3
        assert result.tiers_info[0].image_url == "/badges/standard.png"
        assert result.tiers_info[1].required_count == 0
        assert result.tiers_info[1].image_url is None
        service._query_repo.get_badge_detail_data.assert_called_once_with("KGP", 42)
        service._cache.get.assert_called_once_with("map_state:42")

    def test_get_object_details_builds_dto(self, service):
        obj = SimpleNamespace(id=10)
        parent = SimpleNamespace(id=1)
        child = SimpleNamespace(id=11)
        badge = SimpleNamespace(badge=SimpleNamespace(code="KGP", name="KGP"))
        service._query_repo.get_object_detail_data.return_value = {
            "obj": obj,
            "regions": [("VOIVODESHIP", "Małopolskie")],
            "badges": [badge],
            "ascents": [object()],
            "parent": parent,
            "children": [child],
            "subscribed_badge_codes": ["KGP"],
        }
        service._cache.get.return_value = {"scores": {10: 2}, "colors": {10: "BLUE"}}

        result = service.get_object_details(10, 42)

        assert result.obj is obj
        assert result.regions[0].level == "VOIVODESHIP"
        assert result.regions[0].name == "Małopolskie"
        assert result.badges_list == [{"code": "KGP", "name": "KGP"}]
        assert result.score == 2
        assert result.color == "BLUE"
        assert result.parent is parent
        assert result.children == [child]
        assert result.subscribed_badge_codes == ["KGP"]
        service._query_repo.get_object_detail_data.assert_called_once_with(10, 42)
        service._cache.get.assert_called_once_with("map_state:42")

    def test_get_region_context_builds_dto_and_extent(self, service):
        region = SimpleNamespace(shape=SimpleNamespace(extent=(1.0, 2.0, 3.0, 4.0)))
        first = SimpleNamespace(id=10, name="Pierwszy", type="Szczyt")
        second = SimpleNamespace(id=11, name="Drugi", type="Schronisko")
        service._query_repo.get_region_context_data.return_value = {
            "region": region,
            "objects": [first, second],
            "parent_region": SimpleNamespace(id=1),
            "parent_level": "MACROREGION",
            "children_regions": [SimpleNamespace(id=12)],
            "children_level": "MESOREGION",
            "neighbors": [SimpleNamespace(id=13)],
        }
        service._cache.get.return_value = {"scores": {10: 5, 11: 9}, "colors": {10: "GREEN", 11: "RED"}}

        result = service.get_region_context("VOIVODESHIP", 2, 42)

        assert result.region is region
        assert result.extent == (1.0, 2.0, 3.0, 4.0)
        assert [entry.id for entry in result.ranking_data] == [11, 10]
        assert result.ranking_data[0].score == 9
        assert result.ranking_data[0].color == "RED"
        assert result.total_objects == 2
        assert result.parent_level == "MACROREGION"
        assert result.children_level == "MESOREGION"
        service._query_repo.get_region_context_data.assert_called_once_with("VOIVODESHIP", 2, 42)
        service._cache.get.assert_called_once_with("map_state:42")

    def test_get_region_context_rejects_unknown_level(self, service):
        service._query_repo.get_region_context_data.return_value = None

        with pytest.raises(ValueError, match="Nieobsługiwany poziom regionu: UNKNOWN"):
            service.get_region_context("UNKNOWN", 2, 42)

    def test_get_organizer_detail_builds_dto(self, service):
        organizer = object()
        service._query_repo.get_organizer_detail.return_value = organizer

        result = service.get_organizer_detail(7)

        assert result.organizer is organizer
        service._query_repo.get_organizer_detail.assert_called_once_with(7)

    def test_get_subscribed_badge_ids_delegates_to_repository(self, service):
        service._query_repo.get_subscribed_badge_ids.return_value = [1, 2]

        assert service.get_subscribed_badge_ids(42) == [1, 2]
        service._query_repo.get_subscribed_badge_ids.assert_called_once_with(42)
