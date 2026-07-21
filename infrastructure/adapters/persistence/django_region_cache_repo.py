"""Adapter dla buforowania relacji regionalnych (CQRS) oraz lokalnych nazw."""

from typing import Any

from application.dto.region_cache_dto import ObjectRegionDTO

from application.ports.region_cache_port import RegionCacheRepositoryPort
from apps.badges.models import ObjectRegionCache, TouristObject, TouristRegionModel


class DjangoRegionCacheRepository(RegionCacheRepositoryPort):
    """Adapter zarządzający tabelą ObjectRegionCache i ekstrakcją nazw."""

    def clear_cache_for_object(self, object_id: int) -> None:
        ObjectRegionCache.objects.filter(tourist_object_id=object_id).delete()

    def clear_cache_for_region(self, region_id: int, region_level: str) -> None:
        ObjectRegionCache.objects.filter(region_id=region_id, region_level=region_level).delete()

    def save_object_region(self, dto: ObjectRegionDTO) -> None:
        ObjectRegionCache.objects.create(
            tourist_object_id=dto.object_id,
            region_id=dto.region_id,
            region_level=dto.region_level,
            distance_meters=dto.distance_meters,
        )

    def extract_and_save_local_names(self, object_id: int, osm_raw_tags: dict[str, Any]) -> None:
        """Pobiera lokalne nazwy i aktualizuje obiekt (np. nazwy czeskie)."""
        whitelist = ["pl", "cs", "sk", "de"]
        local_names = {}

        if osm_raw_tags:
            for lang in whitelist:
                tag_key = f"name:{lang}"
                if tag_key in osm_raw_tags:
                    local_names[lang] = osm_raw_tags[tag_key]

        if local_names:
            TouristObject.objects.filter(id=object_id).update(local_names=local_names)

    def get_related_regions(self, tourist_region_id: int) -> list[tuple[int, str]]:
        """Zwraca jednostki składowe zdefiniowane przez administratora PTTK w Regionie Turystycznym."""
        try:
            region = TouristRegionModel.objects.get(id=tourist_region_id)
        except TouristRegionModel.DoesNotExist:
            return []

        related = []
        for v in region.voivodeships.all():
            related.append((v.id, "VOIVODESHIP"))
        for m in region.macroregions.all():
            related.append((m.id, "MACROREGION"))
        for me in region.mesoregions.all():
            related.append((me.id, "MESOREGION"))
        return related

    def check_object_geometry_and_tags(self, object_id: int) -> tuple[bool, dict[str, Any]]:
        from apps.badges.models import TouristObject

        try:
            obj = TouristObject.objects.get(id=object_id)
            return (bool(obj.geom), obj.osm_raw_tags or {})
        except TouristObject.DoesNotExist:
            return (False, {})

    def mark_object_as_ready(self, object_id: int) -> None:
        from apps.badges.models import TouristObject

        TouristObject.objects.filter(id=object_id).update(status="READY")

    def recalculate_all_region_levels(self, object_id: int) -> None:
        from django.apps import apps
        from django.contrib.gis.measure import D

        from apps.badges.models import ObjectRegionCache, TouristObject

        obj = TouristObject.objects.get(id=object_id)
        if not obj.geom:
            return

        levels = [
            ("CountryModel", "COUNTRY"),
            ("VoivodeshipModel", "VOIVODESHIP"),
            ("ProvinceModel", "PROVINCE"),
            ("SubprovinceModel", "SUBPROVINCE"),
            ("MacroregionModel", "MACROREGION"),
            ("MesoregionModel", "MESOREGION"),
        ]

        for model_name, level_name in levels:
            model = apps.get_model("badges", model_name)
            regions = model.objects.filter(shape__distance_lte=(obj.geom, D(m=50)))
            for r in regions:
                ObjectRegionCache.objects.create(
                    tourist_object_id=object_id, region_id=r.id, region_level=level_name, distance_meters=0.0
                )

    def recalculate_tourist_regions(self, object_id: int) -> None:
        from apps.badges.models import ObjectRegionCache, TouristRegionModel

        current_cache = list(ObjectRegionCache.objects.filter(tourist_object_id=object_id))

        for tr in TouristRegionModel.objects.all():
            related_components = self.get_related_regions(tr.id)
            is_inside = any(
                cc.region_id == r_id and cc.region_level == r_level
                for cc in current_cache
                for r_id, r_level in related_components
            )

            if is_inside:
                ObjectRegionCache.objects.create(
                    tourist_object_id=object_id, region_id=tr.id, region_level="TOURIST_REGION", distance_meters=0.0
                )
