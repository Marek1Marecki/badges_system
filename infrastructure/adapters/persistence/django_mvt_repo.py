"""Adapter przestrzenny dla kafelków wektorowych (MVT) z użyciem surowego SQL."""

from django.db import connection

from application.ports.mvt_port import MvtRepositoryPort
from apps.badges.models import (
    CountryModel,
    MacroregionModel,
    MesoregionModel,
    ProvinceModel,
    SubprovinceModel,
    TouristRegionModel,
    VoivodeshipModel,
)

# POPRAWNY IMPORT WYJĄTKU (Z infrastruktury, a nie z aplikacji)
from infrastructure.exceptions import InfrastructureException

# Baza sama dostarczy poprawne nazwy tabel z modeli!
LAYER_TO_TABLE_MAP = {
    "country": CountryModel._meta.db_table,
    "voivodeship": VoivodeshipModel._meta.db_table,
    "province": ProvinceModel._meta.db_table,
    "subprovince": SubprovinceModel._meta.db_table,
    "macroregion": MacroregionModel._meta.db_table,
    "mesoregion": MesoregionModel._meta.db_table,
    "tourist_region": TouristRegionModel._meta.db_table,
}


class DjangoMvtRepository(MvtRepositoryPort):
    """Implementuje MvtRepositoryPort korzystając z potęgi funkcji PostGIS."""

    def get_tile(self, layer_name: str, z: int, x: int, y: int) -> bytes | None:
        table_name = LAYER_TO_TABLE_MAP.get(layer_name)
        if not table_name:
            raise InfrastructureException(f"Nieznana warstwa MVT: {layer_name}")

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

            if row and row[0]:
                return bytes(row[0])

        return None
