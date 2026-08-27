"""Adapter dla wyliczania fizycznych kształtów Regionów Turystycznych."""

from django.contrib.gis.geos import MultiPolygon, Polygon

from application.ports.region_cache_port import TouristRegionGeometryRepositoryPort
from apps.badges.models import TouristRegionModel


class DjangoTouristRegionGeometryRepository(TouristRegionGeometryRepositoryPort):
    """Repozytorium geometrii regionów turystycznych."""

    def get_regions_without_geometry(self) -> list[int]:
        """Zwraca regiony turystyczne bez geometrii."""
        return list(TouristRegionModel.objects.filter(shape__isnull=True).values_list("id", flat=True))

    def update_region_geometry(self, region_id: int) -> bool:
        """

        Args:
          region_id: int:
          region_id: int:

        Returns:

        """
        try:
            region = TouristRegionModel.objects.get(id=region_id)
        except TouristRegionModel.DoesNotExist:
            return False

        geometries = []
        for v in region.voivodeships.filter(shape__isnull=False):
            geometries.append(v.shape)
        for m in region.macroregions.filter(shape__isnull=False):
            geometries.append(m.shape)
        for me in region.mesoregions.filter(shape__isnull=False):
            geometries.append(me.shape)

        if not geometries:
            return False

        merged_geom = geometries[0]
        for geom in geometries[1:]:
            merged_geom = merged_geom.union(geom)

        if isinstance(merged_geom, Polygon):
            merged_geom = MultiPolygon(merged_geom)

        TouristRegionModel.objects.filter(id=region_id).update(shape=merged_geom)
        return True
