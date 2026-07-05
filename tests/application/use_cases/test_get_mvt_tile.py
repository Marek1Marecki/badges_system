"""Testy jednostkowe dla GetMvtTileUseCase."""

from unittest.mock import MagicMock

import pytest

from application.exceptions import UseCaseError
from application.use_cases.get_mvt_tile import GetMvtTileUseCase


class TestGetMvtTileUseCase:
    """Testuje logikę pobierania i buforowania kafelków MVT."""

    def test_returns_cached_tile_when_available(self) -> None:
        """Zwraca skompresowane dane z cache, jeśli są dostępne."""
        cache = MagicMock()
        cache.get.return_value = b"compressed_tile_data"
        mvt_repo = MagicMock()

        uc = GetMvtTileUseCase(mvt_repository=mvt_repo, cache=cache)
        result = uc.execute(layer="country", z=5, x=10, y=15)

        assert result == b"compressed_tile_data"
        cache.get.assert_called_once_with("mvt_v7_country_5_10_15")
        mvt_repo.get_tile.assert_not_called()

    def test_fetches_from_db_when_cache_miss(self) -> None:
        """Pobiera kafelek z bazy danych, gdy nie ma w cache."""
        cache = MagicMock()
        cache.get.return_value = None
        mvt_repo = MagicMock()
        mvt_repo.get_tile.return_value = b"raw_tile_data"

        uc = GetMvtTileUseCase(mvt_repository=mvt_repo, cache=cache)
        result = uc.execute(layer="voivodeship", z=6, x=20, y=30)

        assert result is not None
        mvt_repo.get_tile.assert_called_once_with("voivodeship", 6, 20, 30)
        cache.set.assert_called_once()

    def test_compresses_and_caches_tile_from_db(self) -> None:
        """Kompresuje dane z bazy i zapisuje w cache."""
        cache = MagicMock()
        cache.get.return_value = None
        mvt_repo = MagicMock()
        mvt_repo.get_tile.return_value = b"raw_tile_data"

        uc = GetMvtTileUseCase(mvt_repository=mvt_repo, cache=cache)
        result = uc.execute(layer="province", z=7, x=25, y=35)

        assert result is not None
        # Sprawdzamy, że cache.set został wywołany z skompresowanymi danymi
        cache_set_call = cache.set.call_args
        assert cache_set_call is not None
        assert cache_set_call[0][0] == "mvt_v7_province_7_25_35"
        assert cache_set_call[1]["timeout_seconds"] == 86400

    def test_returns_none_when_db_has_no_tile(self) -> None:
        """Zwraca None, gdy baza nie ma kafelka dla danej lokalizacji."""
        cache = MagicMock()
        cache.get.return_value = None
        mvt_repo = MagicMock()
        mvt_repo.get_tile.return_value = None

        uc = GetMvtTileUseCase(mvt_repository=mvt_repo, cache=cache)
        result = uc.execute(layer="subprovince", z=8, x=30, y=40)

        assert result is None
        cache.set.assert_not_called()

    def test_raises_error_for_unknown_layer(self) -> None:
        """Rzuca UseCaseError dla nieznanej warstwy."""
        cache = MagicMock()
        mvt_repo = MagicMock()

        uc = GetMvtTileUseCase(mvt_repository=mvt_repo, cache=cache)

        with pytest.raises(UseCaseError, match="Nieznana warstwa kafelków: invalid_layer"):
            uc.execute(layer="invalid_layer", z=5, x=10, y=15)

    def test_supports_all_valid_layers(self) -> None:
        """Wszystkie dozwolone warstwy są akceptowane."""
        cache = MagicMock()
        cache.get.return_value = b"data"
        mvt_repo = MagicMock()

        uc = GetMvtTileUseCase(mvt_repository=mvt_repo, cache=cache)

        valid_layers = [
            "country",
            "voivodeship",
            "province",
            "subprovince",
            "macroregion",
            "mesoregion",
            "tourist_region",
        ]

        for layer in valid_layers:
            result = uc.execute(layer=layer, z=5, x=10, y=15)
            assert result == b"data"

    def test_cache_key_format(self) -> None:
        """Klucz cache ma poprawny format."""
        cache = MagicMock()
        cache.get.return_value = None
        mvt_repo = MagicMock()
        mvt_repo.get_tile.return_value = b"data"

        uc = GetMvtTileUseCase(mvt_repository=mvt_repo, cache=cache)
        uc.execute(layer="mesoregion", z=10, x=100, y=200)

        cache.get.assert_called_once_with("mvt_v7_mesoregion_10_100_200")
