"""Adapter przestrzenny dla kafelków wektorowych (MVT) z użyciem surowego SQL (ADR-028)."""

from django.db import connection

from application.ports.mvt_port import MvtRepositoryPort
from apps.badges.models import RegionFlatModel

# POPRAWNY IMPORT WYJĄTKU (Z infrastruktury, a nie z aplikacji)
from infrastructure.exceptions import InfrastructureException

# Jedna płaska tabela regions_flat = wszystkie level'e (COUNTRY/.../MESOREGION).
# Frontend prosi warstwy po nazwach leveli (mesoregion, macroregion, voivodeship).
# Mapujemy na RegionLevel w bazie.
LAYER_TO_LEVEL = {
    "regions_flat": None,  # wszystkie poziomy
    "country": "COUNTRY",
    "province": "PROVINCE",
    "subprovince": "SUBPROVINCE",
    "voivodeship": "VOIVODESHIP",
    "macroregion": "MACROREGION",
    "mesoregion": "MESOREGION",
}


class DjangoMvtRepository(MvtRepositoryPort):
    """Implementuje MvtRepositoryPort korzystając z potęgi funkcji PostGIS."""

    def get_tile(self, layer_name: str, z: int, x: int, y: int) -> bytes | None:
        """

        Args:
          layer_name: str:
          z: int:
          x: int:
          y: int:
          layer_name: str:
          z: int:
          x: int:
          y: int:

        Returns:

        """
        region_level = LAYER_TO_LEVEL.get(layer_name)
        if region_level is None and layer_name not in LAYER_TO_LEVEL:
            raise InfrastructureException(f"Nieznana warstwa MVT: {layer_name}")

        table_name = RegionFlatModel._meta.db_table

        # Tolerance dla ST_Simplify zależy od zoomu — niższe zoomy = większa tolerancja.
        # Wartość w metrach (SRID 3857): 40074m (zoom 0-3), 20037m (zoom 4-6), 10019m (zoom 7-9), 501m (zoom 10+).
        if z <= 3:
            simplify_tolerance = 40074
        elif z <= 6:
            simplify_tolerance = 20037
        elif z <= 9:
            simplify_tolerance = 10019
        else:
            simplify_tolerance = 501

        query = f"""
                WITH bounds AS (
                    SELECT ST_TileEnvelope(%s, %s, %s) AS geom
                ),
                mvtgeom AS (
                    SELECT ST_AsMVTGeom(
                        ST_Simplify(ST_Transform(t.shape, 3857), %s::float),
                        bounds.geom
                    ) AS geom,
                           t.id, t.id::text AS db_id_str, t.name
                    FROM {table_name} t, bounds
                    WHERE ST_Intersects(ST_Transform(t.shape, 3857), bounds.geom)
                    {("AND t.level = %s" if region_level else "")}
                )
                SELECT ST_AsMVT(mvtgeom, %s) FROM mvtgeom;
                """  # noqa: S608

        params: list = [z, x, y, simplify_tolerance]
        if region_level:
            params.append(region_level)
        params.append(layer_name)

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()

            if row and row[0]:
                return bytes(row[0])

        return None
