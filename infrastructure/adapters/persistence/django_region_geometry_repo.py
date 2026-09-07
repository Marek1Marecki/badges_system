"""Adapter dla wyliczania fizycznych kształtów Regionów Turystycznych (ADR-028)."""

from django.contrib.gis.geos import MultiPolygon, Polygon

from application.ports.region_cache_port import TouristRegionGeometryRepositoryPort
from apps.badges.models import RegionFlatModel


class DjangoTouristRegionGeometryRepository(TouristRegionGeometryRepositoryPort):
    """Repozytorium geometrii regionów turystycznych."""

    def get_regions_without_geometry(self) -> list[int]:
        """Zwraca regiony turystyczne bez geometrii."""
        return list(
            RegionFlatModel.objects.filter(level="TOURIST_REGION", shape__isnull=True).values_list("id", flat=True)
        )

    def update_region_geometry(self, region_id: int) -> bool:
        """

        Args:
          region_id: int:
          region_id: int:

        Returns:

        """
        try:
            region = RegionFlatModel.objects.get(id=region_id, level="TOURIST_REGION")
        except RegionFlatModel.DoesNotExist:
            return False

        geometries = []
        for child in region.children.all():
            if child.shape:
                geometries.append(child.shape)

        if not geometries:
            return False

        merged_geom = geometries[0]
        for geom in geometries[1:]:
            merged_geom = merged_geom.union(geom)

        if isinstance(merged_geom, Polygon):
            merged_geom = MultiPolygon(merged_geom)

        RegionFlatModel.objects.filter(id=region_id).update(shape=merged_geom)
        return True
