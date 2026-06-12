"""Przypadek użycia: Generowanie kafelków wektorowych (MVT).

Zgodnie z zasadami Czystej Architektury:
Orkiestruje pobieranie kafelka z bazy, kompresję GZIP oraz buforowanie w Redis.
Widok HTTP otrzymuje gotowe, skompresowane bajty.
"""

import gzip

from application.exceptions import UseCaseError
from application.ports.cache_port import CachePort
from application.ports.mvt_port import MvtRepositoryPort

LAYER_TO_TABLE_MAP = {
    "country": "odznaki_countrymodel",
    "voivodeship": "odznaki_voivodeshipmodel",
    "province": "odznaki_provincemodel",
    "subprovince": "odznaki_subprovincemodel",
    "macroregion": "odznaki_macroregionmodel",
    "mesoregion": "odznaki_mesoregionmodel",
    "tourist_region": "odznaki_touristregionmodel",
}


class GetMvtTileUseCase:
    """Odpytuje repozytorium o kafelek PBF, buforując skompresowany wynik."""

    def __init__(self, mvt_repository: MvtRepositoryPort, cache: CachePort) -> None:
        """Inicjalizuje use case z repozytorium MVT."""
        self._mvt_repo = mvt_repository
        self._cache = cache

    def execute(self, layer: str, z: int, x: int, y: int) -> bytes | None:
        """Pobiera kafelek dla określonej warstwy i współrzędnych XYZ."""
        table_name = LAYER_TO_TABLE_MAP.get(layer)
        if not table_name:
            raise UseCaseError(f"Nieznana warstwa kafelków: {layer}")

        cache_key = f"mvt_{layer}_{z}_{x}_{y}"
        cached_tile = self._cache.get(cache_key)

        # Cache Hit - Zwracamy gotowe skompresowane bajty (weryfikacja typu dla Mypy i ochrony przed zatruciem cache'u)
        if isinstance(cached_tile, bytes):
            return cached_tile

        # Cache Miss - Uderzamy do PostGIS
        tile_data = self._mvt_repo.get_tile(layer, table_name, z, x, y)
        if not tile_data:
            return None

        # Kompresja z użyciem stdlib i zapis do wstrzykniętego CachePort
        compressed_data = gzip.compress(tile_data)
        self._cache.set(cache_key, compressed_data, timeout_seconds=86400)

        return compressed_data
