"""Usługa odczytu (Query Service) odpowiedzialna za budowanie rankingów."""

from collections import defaultdict

from application.dto.explore_queries_dto import (
    PoiRankingResponseDTO,
    RankingItemDTO,
    RegionRankingItemDTO,
    RegionRankingResponseDTO,
)
from application.ports.cache_port import CachePort
from application.ports.explore_queries_port import ExploreQueriesRepositoryPort
from application.ports.user_progress_port import UserProgressRepositoryPort


class ExploreQueriesService:
    """Buduje gotowe struktury danych do wyświetlenia przez widoki eksploracji."""

    def __init__(
        self,
        query_repository: ExploreQueriesRepositoryPort,
        progress_repository: UserProgressRepositoryPort,
        cache: CachePort,
    ) -> None:
        """Inicjalizuje usługę zapytań eksploracyjnych."""
        self._query_repo = query_repository
        self._progress_repo = progress_repository
        self._cache = cache

    def get_poi_ranking(self, profile_id: int) -> PoiRankingResponseDTO:
        """Buduje sklastrowany ranking pojedynczych obiektów turystycznych (Szczytów)."""
        active_progresses = self._progress_repo.get_active_progresses(profile_id)
        subscribed_badge_codes = [p.badge_code for p in active_progresses]

        map_state = self._cache.get(f"map_state:{profile_id}") or {}
        scores = map_state.get("scores", {})
        colors = map_state.get("colors", {})

        qs_peaks = self._query_repo.get_points_of_interest_with_relations()
        grouped_families = defaultdict(list)

        # 1. Zbieramy dzieci do koszyków według "anchor_id"
        for peak in qs_peaks:
            peak_score = int(scores.get(peak.id, scores.get(str(peak.id), 0)))
            anchor_id = peak.parent_object_id if peak.parent_object_id else peak.id
            grouped_families[anchor_id].append(
                {
                    "obj": peak,
                    "score": peak_score,
                    "color": colors.get(peak.id, colors.get(str(peak.id), "GRAY")),
                    "is_parent": peak.parent_object_id is None,
                }
            )

        ranking_data = []

        # 2. Budujemy i sumujemy rodziny
        for anchor_id, children in grouped_families.items():
            cluster_score = sum(c["score"] for c in children)
            is_family = len(children) > 1

            parent_item = next((c for c in children if c["is_parent"]), None)
            cluster_name = parent_item["obj"].name if parent_item else "Nieznany Klaster"

            items = []
            for c in sorted(children, key=lambda x: not x["is_parent"]):
                badges_list = [
                    {"code": b.badge.code, "name": b.badge.name} for b in c["obj"].badgeversionmodel_set.all()
                ]
                items.append(
                    {
                        "id": c["obj"].id,
                        "name": c["obj"].name,
                        "type": c["obj"].type,
                        "altitude": c["obj"].altitude,
                        "score": c["score"],
                        "color": c["color"],
                        "is_parent": c["is_parent"],
                        "badges": badges_list,
                    }
                )

            ranking_data.append(
                RankingItemDTO(
                    is_family=is_family,
                    cluster_score=cluster_score,
                    cluster_id=anchor_id if is_family else None,
                    cluster_name=cluster_name if is_family else None,
                    items=items,
                )
            )

        # 3. Sortujemy i zwracamy spakowany DTO
        ranking_data.sort(key=lambda x: x.cluster_score, reverse=True)

        # Zamiana aktywnych postępów na listę słowników dla szablonu
        active_progresses_dict = [{"badge_code": p.badge_code} for p in active_progresses]

        return PoiRankingResponseDTO(
            active_progresses=active_progresses_dict,
            subscribed_badge_codes=subscribed_badge_codes,
            ranking=ranking_data,
        )

    def get_region_ranking(self, profile_id: int, level: str) -> RegionRankingResponseDTO:
        """Buduje skumulowany ranking dla całych regionów (np. wszystkich szczytów w Tatrach)."""
        map_state = self._cache.get(f"map_state:{profile_id}") or {}
        scores = map_state.get("scores", {})

        regions = self._query_repo.get_regions_by_level(level)
        region_dict = {r.id: {"name": r.name, "score": 0} for r in regions}

        cache_records = self._query_repo.get_object_region_cache_for_level(level)

        for record in cache_records:
            region_id = record.region_id
            obj_id = record.tourist_object_id
            obj_score = int(scores.get(obj_id, scores.get(str(obj_id), 0)))

            if region_id in region_dict:
                region_dict[region_id]["score"] += obj_score

        ranking_data = []
        for r_id, r_data in region_dict.items():
            ranking_data.append(RegionRankingItemDTO(id=r_id, name=r_data["name"], score=r_data["score"], level=level))

        ranking_data.sort(key=lambda x: x.score, reverse=True)

        return RegionRankingResponseDTO(
            level=level,
            ranking=ranking_data,
        )
