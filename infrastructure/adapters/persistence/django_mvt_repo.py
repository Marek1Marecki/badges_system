"""Adapter przestrzenny dla kafelków wektorowych (MVT) z użyciem surowego SQL (ADR-028)."""

from django.db import connection

from application.ports.mvt_port import MvtRepositoryPort
from apps.badges.models import RegionFlatModel

# POPRAWNY IMPORT WYJĄTKU (Z infrastruktury, a nie z aplikacji)
from infrastructure.exceptions import InfrastructureException

# Jedna płaska tabela regions_flat = wszystkie warstwy MVT
LAYER_TO_MODEL = {
    "regions_flat": RegionFlatModel,
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
        model = LAYER_TO_MODEL.get(layer_name)
        if not model:
            raise InfrastructureException(f"Nieznana warstwa MVT: {layer_name}")

        table_name = model._meta.db_table
        query = f"""
                WITH bounds AS (
                    SELECT ST_TileEnvelope(%s, %s, %s) AS geom
                ),
                mvtgeom AS (
                    SELECT ST_AsMVTGeom(ST_Transform(t.shape, 3857), bounds.geom) AS geom,
                           t.id, t.id::text AS db_id_str, t.name
                    FROM {table_name} t, bounds
                    WHERE ST_Intersects(ST_Transform(t.shape, 3857), bounds.geom)
                )
                SELECT ST_AsMVT(mvtgeom, %s) FROM mvtgeom;
                """  # noqa: S608

        with connection.cursor() as cursor:
            cursor.execute(query, [z, x, y, layer_name])
            row = cursor.fetchone()

            if row and row[0]:
                return bytes(row[0])

        return None
