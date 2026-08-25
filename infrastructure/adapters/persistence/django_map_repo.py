"""Adapter przestrzenny dostarczający dane dla warstwy mapowej."""

from typing import Any

from django.contrib.gis.geos import GEOSGeometry, Polygon
from django.contrib.gis.measure import D

from application.dto.map_dto import TouristObjectGeoDTO
from application.ports.map_port import MapRepositoryPort


class DjangoMapRepository(MapRepositoryPort):
    """Implementacja MapRepositoryPort korzystająca z indeksów GiST w GeoDjango."""

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
        """

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
        from apps.badges.models import BadgeVersionModel, ObjectRegionCache, TouristObject

        # 1. Główny filtr przestrzenny z użyciem Bounding Boxa (Indeks GiST)
        geom_filter = Polygon.from_bbox((min_lon, min_lat, max_lon, max_lat))
        qs = TouristObject.objects.filter(geom__within=geom_filter, is_active=True, status="READY")

        # 2. Filtr CQRS (Leniwe wartościowanie terytorialne z ADR-011)
        if region_level and region_id:
            obj_ids = ObjectRegionCache.objects.filter(region_level=region_level, region_id=region_id).values_list(
                "tourist_object_id", flat=True
            )
            qs = qs.filter(id__in=obj_ids)

        # 3. Opcjonalny filtr do mapy "Tylko jedna odznaka" (US-C11)
        if badge_code:
            badge_peaks = BadgeVersionModel.objects.filter(badge__code=badge_code).values_list(
                "pool_peaks__id", flat=True
            )
            qs = qs.filter(id__in=badge_peaks)

        # Twardy limit zapobiegający "Map Spammingowi" i dławieniu przeglądarki
        qs = qs[:500]

        return [
            TouristObjectGeoDTO(
                id=obj.id,
                name=obj.name,
                type=obj.type,
                lon=obj.geom.x,
                lat=obj.geom.y,
            )
            for obj in qs
        ]

    def get_objects_along_line(self, line_wkt: str, buffer_meters: float) -> list[dict[str, Any]]:
        """Szuka obiektów wokół podanej linii WKT za pomocą indeksów GiST.

        Args:
          line_wkt: str:
          buffer_meters: float:
          line_wkt: str:
          buffer_meters: float:

        Returns:
        """
        from apps.badges.models import TouristObject

        try:
            line_geom = GEOSGeometry(line_wkt, srid=4326)
        except Exception:
            return []

        # Szybki filtr PostGIS z użyciem D() - chroni CPU przed ST_DistanceSpheroid
        qs = TouristObject.objects.filter(
            geom__distance_lte=(line_geom, D(m=buffer_meters)), is_active=True, status="READY"
        )

        results = []
        for obj in qs:
            results.append(
                {
                    "id": obj.id,
                    "name": obj.name,
                    "type": obj.type,
                    "altitude": obj.altitude,
                    "lon": obj.geom.x,
                    "lat": obj.geom.y,
                }
            )

        return results
