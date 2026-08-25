"""Port dla repozytorium mapowego.

Zwraca obiekty w oparciu o filtry przestrzenne.
"""

from typing import Any, Protocol

from application.dto.map_dto import TouristObjectGeoDTO


class MapRepositoryPort(Protocol):
    """Interfejs odpytywania bazy danych o punkty na mapie (BBox + CQRS)."""

    def get_objects_in_bbox(
        self,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        badge_code: str | None,
        region_level: str | None,
        region_id: int | None,
    ) -> list[TouristObjectGeoDTO]:
        """Pobiera zwalidowane, aktywne obiekty z zadanego prostokąta.

        Maksymalnie do 500 sztuk, aby zapobiec przeciążeniu frontendu.

        Args:
          min_lon: float:
          min_lat: float:
          max_lon: float:
          max_lat: float:
          badge_code: str | None:
          region_level: str | None:
          region_id: int | None:
          min_lon: float:
          min_lat: float:
          max_lon: float:
          max_lat: float:
          badge_code: str | None:
          region_level: str | None:
          region_id: int | None:

        Returns:
        """
        ...

    def get_objects_along_line(self, line_wkt: str, buffer_meters: float) -> list[dict[str, Any]]:
        """Zwraca obiekty (w formacie słownika) leżące w zadanym buforze wokół linii WKT.

        Args:
          line_wkt: str:
          buffer_meters: float:
          line_wkt: str:
          buffer_meters: float:

        Returns:
        """
        ...
