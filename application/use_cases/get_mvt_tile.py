"""Przypadek użycia: Generowanie kafelków wektorowych (MVT).

Zgodnie z zasadami Czystej Architektury:
Orkiestruje pobieranie kafelka z bazy, kompresję GZIP oraz buforowanie w Redis.
Widok HTTP otrzymuje gotowe, skompresowane bajty.
"""

import gzip

from application.exceptions import UseCaseError
from application.ports.cache_port import CachePort
from application.ports.mvt_port import MvtRepositoryPort

# Lista dozwolonych warstw (Czysto biznesowe pojęcia, bez nazw tabel bazy danych)
SUPPORTED_LAYERS = {"country", "voivodeship", "province", "subprovince", "macroregion", "mesoregion", "tourist_region"}


class GetMvtTileUseCase:
    """Odpytuje repozytorium o kafelek PBF, buforując skompresowany wynik."""

    def __init__(self, mvt_repository: MvtRepositoryPort, cache: CachePort) -> None:
        """Inicjalizuje przypadek użycia z repozytorium MVT i cache'em."""
        self._mvt_repo = mvt_repository
        self._cache = cache

    def execute(self, layer: str, z: int, x: int, y: int) -> bytes | None:
        """Pobiera kafelek dla określonej warstwy i współrzędnych XYZ."""
        if layer not in SUPPORTED_LAYERS:
            raise UseCaseError(f"Nieznana warstwa kafelków: {layer}")

        cache_key = f"mvt_{layer}_{z}_{x}_{y}"
        cached_tile = self._cache.get(cache_key)

        # Cache Hit - Zwracamy gotowe skompresowane bajty
        if cached_tile is not None:
            return cached_tile  # type: ignore[no-any-return]

        # Cache Miss - Uderzamy do PostGIS
        tile_data = self._mvt_repo.get_tile(layer, z, x, y)
        if not tile_data:
            return None

        # Kompresja z użyciem stdlib i zapis do wstrzykniętego CachePort
        compressed_data = gzip.compress(tile_data)
        self._cache.set(cache_key, compressed_data, timeout_seconds=86400)

        return compressed_data
