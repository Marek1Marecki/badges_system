"""Przypadek użycia: Złączanie geometrii (ST_Union) w regionach turystycznych."""

from application.ports.region_cache_port import TouristRegionGeometryRepositoryPort


class BuildTouristRegionGeometryUseCase:
    """Złącza (ST_Union) składowe w 1 ogromny wielokąt (Poligon)."""

    def __init__(self, geometry_repository: TouristRegionGeometryRepositoryPort) -> None:
        """Inicjalizuje przypadek użycia.

        Args:
            geometry_repository: Port do zapisu/odczytu geometrii w PostGIS.
        """
        self._repo = geometry_repository

    def execute(self, region_id: int) -> str:
        """Kompiluje obrys składników do jednego Poligonu i go zapisuje.

        Args:
          region_id: int:
          region_id: int:

        Returns:
        """
        # Oddelegowanie całkowitej brudnej roboty GIS i złączeń do Adaptera (infrastruktury)
        success = self._repo.update_region_geometry(region_id)

        if not success:
            return f"Brak geometrii do scalenia dla Regionu {region_id}."

        return f"Sukces. Scalono geometrię Regionu {region_id}."
