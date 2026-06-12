"""Adapter przestrzenny dla kafelków wektorowych (MVT) z użyciem surowego SQL."""

from django.db import connection

from application.ports.mvt_port import MvtRepositoryPort


class DjangoMvtRepository(MvtRepositoryPort):
    """Implementuje MvtRepositoryPort korzystając z potęgi funkcji PostGIS."""

    def get_tile(self, layer_name: str, table_name: str, z: int, x: int, y: int) -> bytes | None:
        # ADR-013: Świadome złamanie abstrakcji ORM dla ekstremalnej wydajności.
        # Tabela wstrzykiwana z bezpiecznej białej listy w Use Case (Ochrona przed SQL Injection).
        # Transformacja 3857 wymagana przez ST_TileEnvelope.
        query = f""" 
        WITH bounds AS (
            SELECT ST_TileEnvelope(%s, %s, %s) AS geom
        ),
        mvtgeom AS (
            SELECT ST_AsMVTGeom(ST_Transform(t.shape, 3857), bounds.geom) AS geom,
                   t.id, t.name
            FROM {table_name} t, bounds
            WHERE ST_Intersects(ST_Transform(t.shape, 3857), bounds.geom)
        )
        SELECT ST_AsMVT(mvtgeom, %s) FROM mvtgeom;
        """  # noqa: S608

        with connection.cursor() as cursor:
            cursor.execute(query, [z, x, y, layer_name])
            row = cursor.fetchone()

            # PostGIS ST_AsMVT zwraca bajty. Zabezpieczamy przypadek pustych kafelków (np. na oceanie).
            if row and row[0]:
                return bytes(row[0])

        return None
