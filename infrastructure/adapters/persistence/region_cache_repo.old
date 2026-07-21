"""Adapter repozytorium dla operacji przestrzennych (PostGIS).

Zawiera WSZYSTKIE operacje na modelach Django wyodrębnione z use case'ów.
Use case'y nie wiedzą o istnieniu Django ORM — operują tylko na prostych typach.

Zgodnie z 22-ports-adapters-dto-contract.md:
- Adapter zna Django ORM i PostGIS — use case'y nie
- Metody przyjmują i zwracają proste typy Pythona lub dataclasses
- Logika biznesowa (co obliczyć, kiedy) pozostaje w use case'ach
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.contrib.gis.geos import MultiPolygon, Polygon
from django.contrib.gis.measure import D
from django.db import transaction


@dataclass
class RegionMatch:
    """Wynik dopasowania przestrzennego — region znaleziony dla obiektu."""

    region_level: str
    region_id: int
    region_name: str
    distance_meters: float


@dataclass
class TouristObjectData:
    """Dane obiektu turystycznego — DTO między adapterem a use case'em."""

    id: int
    name: str
    has_geom: bool
    geom: Any  # Point — unikamy importu GEOS w use case'ach
    osm_id: str | None
    osm_raw_tags: dict[str, str] | None
    local_names: dict[str, str] | None
    alt_name: str | None
    altitude: float | None
    wikipedia_link: str | None


@dataclass
class TouristRegionData:
    """Dane regionu turystycznego — DTO między adapterem a use case'em."""

    id: int
    name: str


class RegionCacheRepository:
    """Zarządza tabelą ObjectRegionCache i wykonuje zapytania przestrzenne."""

    SEARCH_RADIUS_METERS = 50

    # ------------------------------------------------------------------
    # Pobieranie obiektów
    # ------------------------------------------------------------------

    def get_tourist_object(self, object_id: int) -> TouristObjectData | None:
        """Zwraca dane obiektu turystycznego lub None jeśli nie istnieje."""
        from apps.badges.models import TouristObject

        try:
            obj = TouristObject.objects.get(id=object_id)
        except TouristObject.DoesNotExist:
            return None

        return TouristObjectData(
            id=obj.id,
            name=obj.name,
            has_geom=bool(obj.geom),
            geom=obj.geom,
            osm_id=obj.osm_id,
            osm_raw_tags=obj.osm_raw_tags,
            local_names=obj.local_names,
            alt_name=obj.alt_name,
            altitude=obj.altitude,
            wikipedia_link=obj.wikipedia_link,
        )

    def get_tourist_region(self, region_id: int) -> TouristRegionData | None:
        """Zwraca dane regionu turystycznego lub None jeśli nie istnieje."""
        from apps.badges.models import TouristRegionModel

        try:
            region = TouristRegionModel.objects.get(id=region_id)
        except TouristRegionModel.DoesNotExist:
            return None

        return TouristRegionData(id=region.id, name=region.name)

    # ------------------------------------------------------------------
    # Operacje przestrzenne
    # ------------------------------------------------------------------

    def find_regions_for_point(self, point: Any) -> list[RegionMatch]:
        """Wykonuje zapytania ST_DWithin dla wszystkich poziomów hierarchii."""
        from apps.badges.models import (
            CountryModel,
            MacroregionModel,
            MesoregionModel,
            ProvinceModel,
            RegionLevelType,
            SubprovinceModel,
            TouristRegionModel,
            VoivodeshipModel,
        )

        region_models_map: list[tuple[type[Any], str]] = [
            (CountryModel, str(RegionLevelType.COUNTRY)),
            (VoivodeshipModel, str(RegionLevelType.VOIVODESHIP)),
            (ProvinceModel, str(RegionLevelType.PROVINCE)),
            (SubprovinceModel, str(RegionLevelType.SUBPROVINCE)),
            (MacroregionModel, str(RegionLevelType.MACROREGION)),
            (MesoregionModel, str(RegionLevelType.MESOREGION)),
            (TouristRegionModel, str(RegionLevelType.TOURIST_REGION)),
        ]

        matches: list[RegionMatch] = []

        for ModelClass, level_type in region_models_map:
            found_regions = ModelClass.objects.filter(shape__distance_lte=(point, D(m=self.SEARCH_RADIUS_METERS)))
            for region in found_regions:
                is_inside = region.shape.intersects(point)
                distance = 0.0 if is_inside else float(self.SEARCH_RADIUS_METERS)
                matches.append(
                    RegionMatch(
                        region_level=level_type,
                        region_id=region.id,
                        region_name=region.name,
                        distance_meters=distance,
                    )
                )

        return matches

    def replace_cache_for_object(self, tourist_object_id: int, matches: list[RegionMatch]) -> None:
        """Atomowo zastępuje wpisy cache dla danego obiektu (idempotentne)."""
        from apps.badges.models import ObjectRegionCache, TouristObject

        tourist_obj = TouristObject.objects.get(id=tourist_object_id)

        new_entries = [
            ObjectRegionCache(
                tourist_object=tourist_obj,
                region_level=match.region_level,
                region_id=match.region_id,
                region_name=match.region_name,
                distance_meters=match.distance_meters,
            )
            for match in matches
        ]

        with transaction.atomic():
            ObjectRegionCache.objects.filter(tourist_object=tourist_obj).delete()
            if new_entries:
                ObjectRegionCache.objects.bulk_create(new_entries)

    def replace_tourist_region_entries(self, region_id: int, region_name: str, object_ids: list[int]) -> None:
        """Atomowo zastępuje wpisy cache dla całego regionu turystycznego."""
        from apps.badges.models import ObjectRegionCache, RegionLevelType

        new_entries = [
            ObjectRegionCache(
                tourist_object_id=obj_id,
                region_level=RegionLevelType.TOURIST_REGION,
                region_id=region_id,
                region_name=region_name,
                distance_meters=0.0,
            )
            for obj_id in object_ids
        ]

        with transaction.atomic():
            ObjectRegionCache.objects.filter(
                region_level=RegionLevelType.TOURIST_REGION,
                region_id=region_id,
            ).delete()
            if new_entries:
                ObjectRegionCache.objects.bulk_create(new_entries, ignore_conflicts=True)

    def find_object_ids_in_sub_regions(self, region_id: int) -> list[int]:
        """Zwraca ID obiektów turystycznych należących do składowych regionu."""
        from django.db.models import Q

        from apps.badges.models import ObjectRegionCache, RegionLevelType, TouristRegionModel

        t_region = TouristRegionModel.objects.get(id=region_id)

        prov_ids = list(t_region.provinces.values_list("id", flat=True))
        subprov_ids = list(t_region.subprovinces.values_list("id", flat=True))
        macro_ids = list(t_region.macroregions.values_list("id", flat=True))
        meso_ids = list(t_region.mesoregions.values_list("id", flat=True))

        query = (
            Q(region_level=RegionLevelType.PROVINCE, region_id__in=prov_ids)
            | Q(region_level=RegionLevelType.SUBPROVINCE, region_id__in=subprov_ids)
            | Q(region_level=RegionLevelType.MACROREGION, region_id__in=macro_ids)
            | Q(region_level=RegionLevelType.MESOREGION, region_id__in=meso_ids)
        )

        return list(ObjectRegionCache.objects.filter(query).values_list("tourist_object_id", flat=True).distinct())

    def build_union_geometry(self, region_id: int) -> MultiPolygon | None:
        """Scala geometrie składowych regionu turystycznego (ST_UnaryUnion)."""
        from django.contrib.gis.geos import GeometryCollection

        from apps.badges.models import TouristRegionModel

        t_region = TouristRegionModel.objects.get(id=region_id)

        geoms = []
        for qs in [
            t_region.provinces.all(),
            t_region.subprovinces.all(),
            t_region.macroregions.all(),
            t_region.mesoregions.all(),
        ]:
            for item in qs:
                if item.shape:
                    geoms.append(item.shape)

        if not geoms:
            return None

        combined = GeometryCollection(geoms).unary_union

        if isinstance(combined, Polygon):
            return MultiPolygon(combined)
        elif isinstance(combined, MultiPolygon):
            return combined

        return None

    def save_local_names(self, object_id: int, local_names: dict[str, str]) -> None:
        """Zapisuje lokalne nazwy do obiektu turystycznego."""
        from apps.badges.models import TouristObject

        TouristObject.objects.filter(id=object_id).update(local_names=local_names)

    # ------------------------------------------------------------------
    # Operacje dla ScanProximityCandidatesUseCase
    # ------------------------------------------------------------------

    def find_proximity_candidates(self, radius_meters: float) -> list[tuple[int, int, float]]:
        """Szuka par obiektów bliższych niż radius_meters.

        Returns:
            Lista krotek (id_a, id_b, distance_meters) gdzie id_a < id_b.
        """
        from apps.badges.models import TouristObject

        base_qs = TouristObject.objects.filter(
            geom__isnull=False,
            is_active=True,
            parent_object__isnull=True,
        )

        pairs: list[tuple[int, int, float]] = []

        for obj in base_qs:
            neighbors = base_qs.exclude(id=obj.id).filter(geom__distance_lte=(obj.geom, D(m=radius_meters)))
            for neighbor in neighbors:
                if obj.id >= neighbor.id:
                    continue
                try:
                    distance: float = obj.geom.transform(3857, clone=True).distance(
                        neighbor.geom.transform(3857, clone=True)
                    )
                except Exception:
                    distance = 0.0
                pairs.append((obj.id, neighbor.id, distance))

        return pairs

    def create_proximity_candidate(self, obj_a_id: int, obj_b_id: int, distance_meters: float) -> bool:
        """Tworzy wpis ProximityCandidate jeśli nie istnieje.

        Returns:
            True jeśli nowy wpis został utworzony, False jeśli już istniał.
        """
        from apps.badges.models import ProximityCandidate, ProximityStatus, TouristObject

        obj_a = TouristObject.objects.get(id=obj_a_id)
        obj_b = TouristObject.objects.get(id=obj_b_id)

        _, created = ProximityCandidate.objects.get_or_create(
            obj_a=obj_a,
            obj_b=obj_b,
            defaults={
                "distance_meters": distance_meters,
                "status": ProximityStatus.PENDING,
            },
        )
        return bool(created)

    # ------------------------------------------------------------------
    # Operacje dla OsmNightWatchmanUseCase
    # ------------------------------------------------------------------

    def get_objects_for_sync(self, batch_size: int) -> list[dict[str, Any]]:
        """Zwraca partię obiektów do synchronizacji z OSM (najdawniej sprawdzane)."""
        from django.db.models import F

        from apps.badges.models import TouristObject

        qs = (
            TouristObject.objects.exclude(osm_id__isnull=True)
            .exclude(osm_id="")
            .order_by(F("last_sync_check").asc(nulls_first=True))[:batch_size]
        )

        return [
            {
                "id": obj.id,
                "osm_id": obj.osm_id,
                "altitude": obj.altitude,
                "wikipedia_link": obj.wikipedia_link,
                "is_active": obj.is_active,
            }
            for obj in qs
        ]

    def update_object_after_sync(
        self,
        object_id: int,
        osm_raw_tags: dict[str, Any],
        osm_version: int | None,
        osm_timestamp: datetime | None,
        last_sync_check: datetime,
    ) -> None:
        """Zapisuje wynik synchronizacji OSM do obiektu."""
        from apps.badges.models import TouristObject

        TouristObject.objects.filter(id=object_id).update(
            osm_raw_tags=osm_raw_tags,
            osm_version=osm_version,
            osm_timestamp=osm_timestamp,
            last_sync_check=last_sync_check,
        )

    def create_osm_sync_conflict(self, object_id: int, field_name: str, old_value: str, new_value: str) -> None:
        """Tworzy wpis konfliktu synchronizacji OSM jeśli nie istnieje."""
        from apps.badges.models import OsmSyncConflict, TouristObject

        obj = TouristObject.objects.get(id=object_id)
        OsmSyncConflict.objects.get_or_create(
            tourist_object=obj,
            field_name=field_name,
            defaults={"old_value": old_value, "new_value": new_value},
        )

    def save_region_geometry(self, region_id: int, geometry: Any) -> None:
        """Zapisuje scaloną geometrię do modelu TouristRegionModel."""
        from apps.badges.models import TouristRegionModel

        TouristRegionModel.objects.filter(id=region_id).update(shape=geometry)
