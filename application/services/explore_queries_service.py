"""Usługa odczytu (Query Service) odpowiedzialna za budowanie rankingów."""

from collections import defaultdict
from collections.abc import Sequence

from application.dto.explore_queries_dto import (
    PoiRankingResponseDTO,
    RankingItemDTO,
    RegionRankingItemDTO,
    RegionRankingResponseDTO,
)
from application.dto.tourist_views_dto import (
    BadgeCatalogEntryResponseDTO,
    BadgeDetailResponseDTO,
    BadgeObjectDTO,
    BadgeTierInfoDTO,
    ObjectDetailResponseDTO,
    ObjectRegionDTO,
    OrganizerDetailResponseDTO,
    RegionContextResponseDTO,
    RegionRankingEntryDTO,
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
        """Buduje sklastrowany ranking pojedynczych obiektów turystycznych (Szczytów).

        Args:
          profile_id: ID profilu turysty.

        Returns:
          Ranking obiektów POI z klasterami i wynikami.
        """
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
        """Buduje skumulowany ranking dla całych regionów (np.

        wszystkich szczytów w Tatrach).

        Args:
          profile_id: ID profilu turysty.
          level: Poziom geograficzny regionów.

        Returns:
          Ranking regionów z wynikami.
        """
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

    def get_catalog_badges(self, profile_id: int) -> Sequence[BadgeCatalogEntryResponseDTO]:
        """Pobiera katalog odznak z danymi subskrypcji i statusu dla profilu.

        Delegowanie do adaptera — serwis nie importuje modeli Django (AUDYT-016).

        Args:
          profile_id: int:

        Returns:
          Sequence[BadgeCatalogEntryResponseDTO]: Lista wpisów katalogu odznak.
        """
        return self._query_repo.get_catalog_badges(profile_id)

    def get_badge_details(
        self, badge_code: str, profile_id: int, evaluation: dict[str, object] | None = None
    ) -> BadgeDetailResponseDTO:
        """Buduje szczegóły odznaki dla widoku badge_detail.

        Args:
          badge_code: str:
          profile_id: int:
          evaluation: dict[str, object] | None:

        Returns:
          BadgeDetailDTO: Szczegóły odznaki z danymi dla HTML.
        """
        raw = self._query_repo.get_badge_detail_data(badge_code, profile_id)

        # Map state for scores/colors
        map_state = self._cache.get(f"map_state:{profile_id}") or {}
        scores = map_state.get("scores", {})
        colors = map_state.get("colors", {})

        objects_list = []
        for obj in raw["objects"]:
            obj_score = int(scores.get(obj.id, scores.get(str(obj.id), 0)))
            obj_color = colors.get(obj.id, colors.get(str(obj.id), "GRAY"))
            objects_list.append(
                BadgeObjectDTO(
                    id=obj.id,
                    name=obj.name,
                    altitude=obj.altitude,
                    score=obj_score,
                    color=obj_color,
                )
            )

        tiers_info = []
        for tier in raw["tiers"]:
            tiers_info.append(
                BadgeTierInfoDTO(
                    name=tier.name,
                    required_count=tier.required_peaks_count if tier.required_peaks_count else 0,
                    status="",
                    image_url=tier.badge_image.url if tier.badge_image else None,
                )
            )

        return BadgeDetailResponseDTO(
            badge=raw["badge"],
            progress=raw["progress"],
            evaluation=evaluation,
            objects_list=objects_list,
            target_version=raw["target_version"],
            tiers_info=tiers_info,
            has_consent=raw["badge"].organizer.has_publication_consent,
        )

    def get_object_details(self, object_id: int, profile_id: int) -> ObjectDetailResponseDTO:
        """Buduje szczegóły obiektu turystycznego dla widoku object_detail.

        Args:
          object_id: int:
          profile_id: int:

        Returns:
          ObjectDetailDTO: Szczegóły obiektu z danymi dla HTML.
        """
        raw = self._query_repo.get_object_detail_data(object_id, profile_id)
        obj = raw["obj"]

        # Map state for score/color
        map_state = self._cache.get(f"map_state:{profile_id}") or {}
        scores = map_state.get("scores", {})
        colors = map_state.get("colors", {})

        obj_score = int(scores.get(obj.id, scores.get(str(obj.id), 0)))
        obj_color = colors.get(obj.id, colors.get(str(obj.id), "GRAY"))

        regions = [ObjectRegionDTO(level=level, name=name) for level, name in raw["regions"]]

        badges_list = [{"code": b.badge.code, "name": b.badge.name} for b in raw["badges"]]

        return ObjectDetailResponseDTO(
            obj=obj,
            regions=regions,
            badges_list=badges_list,
            score=obj_score,
            color=obj_color,
            ascents=raw["ascents"],
            parent=raw["parent"],
            children=raw["children"],
            subscribed_badge_codes=raw["subscribed_badge_codes"],
        )

    def get_region_context(self, region_level: str, region_id: int, profile_id: int) -> RegionContextResponseDTO:
        """Buduje kontekst geograficzny regionu dla widoku region_detail.

        Args:
          region_level: str:
          region_id: int:
          profile_id: int:

        Returns:
          RegionContextDTO: Kontekst regionu z rankingiem obiektów.
        """
        raw = self._query_repo.get_region_context_data(region_level, region_id, profile_id)

        if raw is None:
            raise ValueError(f"Nieobsługiwany poziom regionu: {region_level}")

        map_state = self._cache.get(f"map_state:{profile_id}") or {}
        scores = map_state.get("scores", {})
        colors = map_state.get("colors", {})

        objects = raw["objects"]
        ranking_data: list[RegionRankingEntryDTO] = []
        for obj in objects:
            obj_score = int(scores.get(obj.id, scores.get(str(obj.id), 0)))
            obj_color = colors.get(obj.id, colors.get(str(obj.id), "GRAY"))
            ranking_data.append(
                RegionRankingEntryDTO(
                    id=obj.id,
                    name=obj.name,
                    type=obj.type,
                    score=obj_score,
                    color=obj_color,
                )
            )
        ranking_data.sort(key=lambda x: x.score, reverse=True)

        # Extent from region geometry
        extent = None
        region = raw["region"]
        if hasattr(region, "shape") and region.shape:
            extent = (
                float(region.shape.extent[0]),
                float(region.shape.extent[1]),
                float(region.shape.extent[2]),
                float(region.shape.extent[3]),
            )

        return RegionContextResponseDTO(
            region=region,
            region_level=region_level,
            region_id=region_id,
            extent=extent,
            ranking_data=ranking_data,
            total_objects=len(ranking_data),
            parent_region=raw["parent_region"],
            parent_level=raw["parent_level"],
            children_regions=raw["children_regions"],
            children_level=raw["children_level"],
            neighbors=raw["neighbors"],
        )

    def get_organizer_detail(self, organizer_id: int) -> OrganizerDetailResponseDTO:
        """Pobiera organizatora z odznakami dla widoku organizer_detail.

        Args:
          organizer_id: int:

        Returns:
          OrganizerDetailDTO: DTO otaczające model organizatora.
        """
        organizer = self._query_repo.get_organizer_detail(organizer_id)
        return OrganizerDetailResponseDTO(organizer=organizer)

    def get_subscribed_badge_ids(self, profile_id: int) -> list[int]:
        """Pobiera ID odznak subskrybowanych przez profil.

        Args:
          profile_id: int:

        Returns:
          list[int]: Lista ID subskrybowanych odznak.
        """
        return self._query_repo.get_subscribed_badge_ids(profile_id)
