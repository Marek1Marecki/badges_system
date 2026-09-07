"""Adapter odczytu dla zapytań eksploracji i rankingów."""

from typing import Any

from application.dto.tourist_views_dto import BadgeCatalogEntryResponseDTO
from application.ports.explore_queries_port import ExploreQueriesRepositoryPort
from apps.badges.models import (
    BadgeModel,
    BadgeVersionModel,
    ObjectRegionCache,
    OrganizerModel,
    RegionFlatModel,
    TouristObject,
)


class DjangoExploreQueriesRepository(ExploreQueriesRepositoryPort):
    """Implementuje zoptymalizowane pod odczyt zapytania do bazy PTTK."""

    def get_points_of_interest_with_relations(self) -> Any:
        """Pobiera szczyty z relacjami prefetch (Ochrona N+1)."""
        return (
            TouristObject.objects.filter(status="READY", is_active=True)
            .select_related("parent_object")
            .prefetch_related("badgeversionmodel_set__badge")
        )

    def get_regions_by_level(self, level: str) -> Any:
        """Zwraca wszystkie regiony z danego poziomu (ADR-028 — Ltree).

        Read layer używa jednej tabeli `regions_flat` z kolumną `level`
        zamiast 3 osobnych if/elif na różne modele. O(1) lookup na `level`
        zamiast 3 modeli + JOIN w `get_region_context_data`.

        Args:
          level: str: RegionLevel value (np. "VOIVODESHIP", "MACROREGION").

        Returns:
          QuerySet[RegionFlatModel] — pusty, jeśli `level` nieznany.
        """
        return RegionFlatModel.objects.filter(level=level)

    def get_object_region_cache_for_level(self, level: str) -> Any:
        """Pobiera płaską relację CQRS dla obiektów na zadanym poziomie.

        Args:
          level: str:

        Returns:
        """
        return ObjectRegionCache.objects.filter(region_level=level)

    def get_catalog_badges(self, profile_id: int) -> list[BadgeCatalogEntryResponseDTO]:
        """Pobiera katalog odznak z danymi subskrypcji i statusu dla profilu.

        Zabezpieczenie N+1: select_related na organizer, prefetch_related na wersję.
        """
        # Late import: UserBadgeProgress is in apps.tourists.models (bounded by BINDING-016-ext)
        from apps.tourists.models import UserBadgeProgress

        badges = BadgeModel.objects.select_related("organizer").prefetch_related("versions").all()

        progresses = UserBadgeProgress.objects.filter(profile_id=profile_id).select_related("badge__organizer")
        progress_by_badge: dict[int, Any] = {p.badge_id: p for p in progresses}

        entries: list[BadgeCatalogEntryResponseDTO] = []
        for badge in badges:
            progress = progress_by_badge.get(badge.id)
            domain_status = progress.domain_status if progress else "NOT_STARTED"
            current_version = badge.versions.order_by("-valid_from").first()

            entries.append(
                BadgeCatalogEntryResponseDTO(
                    id=badge.id,
                    code=badge.code,
                    name=badge.name,
                    organizer_name=badge.organizer.name,
                    current_version_id=current_version.id if current_version else None,
                    is_subscribed=progress is not None,
                    domain_status=domain_status,
                    badge=badge,
                )
            )
        return entries

    def get_badge_detail_data(self, badge_code: str, profile_id: int) -> Any:
        """Pobiera surowe dane odznaki dla widoku badge_detail (z prefetchami N+1).

        Returns a dict with keys: badge, progress, target_version, tiers, objects.
        """
        from apps.tourists.models import UserBadgeProgress

        badge = (
            BadgeModel.objects.select_related("organizer")
            .prefetch_related(
                "versions__tiers",
                "versions__pool_peaks",
            )
            .get(code=badge_code)
        )

        versions = badge.versions.all()
        target_version = versions.order_by("-valid_from").first()

        progress = None
        try:
            progress = UserBadgeProgress.objects.get(profile_id=profile_id, badge=badge)
        except UserBadgeProgress.DoesNotExist:
            pass

        tiers = target_version.tiers.all() if target_version else []
        pool_peaks = target_version.pool_peaks.all() if target_version else []

        return {
            "badge": badge,
            "progress": progress,
            "target_version": target_version,
            "tiers": tiers,
            "objects": pool_peaks,
        }

    def get_object_detail_data(self, object_id: int, profile_id: int) -> Any:
        """Pobiera surowe dane obiektu turystycznego dla widoku object_detail."""
        from apps.tourists.models import AscentLog, UserBadgeProgress

        obj = (
            TouristObject.objects.filter(status="READY", is_active=True)
            .select_related("parent_object")
            .prefetch_related("ascents_logged")
            .get(id=object_id)
        )

        # Regions via CQRS cache
        region_cache = ObjectRegionCache.objects.filter(tourist_object=obj)
        regions_data: list[tuple[str, str]] = []
        for cache in region_cache:
            regions_data.append((cache.region_level, cache.region_name))

        # Badges that include this object in their pool
        badges = BadgeVersionModel.objects.filter(pool_peaks=obj).select_related("badge")

        # Ascents by this profile on this object
        ascents = AscentLog.objects.filter(profile_id=profile_id, peak=obj).order_by("-ascent_date")

        # Subscribed badge codes for this profile
        subscribed_codes = list(
            UserBadgeProgress.objects.filter(profile_id=profile_id).values_list("badge__code", flat=True)
        )

        return {
            "obj": obj,
            "regions": regions_data,
            "badges": badges,
            "ascents": ascents,
            "parent": obj.parent_object,
            "children": TouristObject.objects.filter(parent_object=obj),
            "subscribed_badge_codes": subscribed_codes,
        }

    def get_region_context_data(self, region_level: str, region_id: int, profile_id: int) -> Any:
        """Pobiera surowe dane kontekstu regionu dla widoku region_detail.

        ADR-028 — używa płaskiej tabeli `regions_flat`:
          - `region.parent` (FK) zastępuje twarde getattr w if/elif,
          - `region.children.all()` (reverse FK) zastępuje
            `MesoregionModel.filter(macroregion=region)` i
            `MacroregionModel.filter(subprovince__country=region)` —
            eliminuje dwa chainy JOIN (VOIVODESHIP -> ... -> MACROREGION).

        Returns:
          dict z region, parent_region, parent_level, children_regions,
          children_level, neighbors, objects. None, gdy `region_level`
          nie istnieje w RegionLevel.
        """
        try:
            region = RegionFlatModel.objects.select_related("parent").get(id=region_id, level=region_level)
        except RegionFlatModel.DoesNotExist:
            return None

        parent_region = region.parent
        parent_level = parent_region.level if parent_region else None

        # Descendants = regiony w tej samej tabeli z `parent=region`
        # (działa dla każdego poziomu — nie tylko MESOREGION/MACROREGION)
        children_regions: list[RegionFlatModel] = list(region.children.all())
        children_level = region.level if children_regions else None

        cache_records = ObjectRegionCache.objects.filter(region_level=region_level, region_id=region_id)
        object_ids = [r.tourist_object_id for r in cache_records]
        objects = TouristObject.objects.filter(id__in=object_ids)

        return {
            "region": region,
            "parent_region": parent_region,
            "parent_level": parent_level,
            "children_regions": children_regions,
            "children_level": children_level,
            "neighbors": list(region.neighbors.all()),
            "objects": objects,
        }

    def get_organizer_detail(self, organizer_id: int) -> Any:
        """Pobiera organizatora z odznakami dla widoku organizer_detail."""
        organizer = OrganizerModel.objects.prefetch_related("badges").get(id=organizer_id)
        return organizer

    def get_subscribed_badge_ids(self, profile_id: int) -> list[int]:
        """Pobiera ID odznak subskrybowanych przez profil (dla organizer_detail)."""
        from apps.tourists.models import UserBadgeProgress

        return list(UserBadgeProgress.objects.filter(profile_id=profile_id).values_list("badge_id", flat=True))
