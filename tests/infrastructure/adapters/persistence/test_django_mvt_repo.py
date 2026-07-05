"""Testy dla DjangoMvtRepository."""

from unittest.mock import MagicMock, patch

import pytest

from infrastructure.adapters.persistence.django_mvt_repo import DjangoMvtRepository
from infrastructure.exceptions import InfrastructureException


class TestDjangoMvtRepository:
    @patch("infrastructure.adapters.persistence.django_mvt_repo.connection")
    def test_get_tile_returns_bytes(self, mock_connection):
        """Zwraca bajty kafelka gdy dane istnieją."""
        repo = DjangoMvtRepository()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (b"tile_data",)
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        result = repo.get_tile("country", 1, 2, 3)

        assert result == b"tile_data"

    @patch("infrastructure.adapters.persistence.django_mvt_repo.connection")
    def test_get_tile_returns_none_when_no_data(self, mock_connection):
        """Zwraca None gdy brak danych."""
        repo = DjangoMvtRepository()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        result = repo.get_tile("country", 1, 2, 3)

        assert result is None

    @patch("infrastructure.adapters.persistence.django_mvt_repo.connection")
    def test_get_tile_returns_none_when_empty_row(self, mock_connection):
        """Zwraca None gdy wiersz jest pusty."""
        repo = DjangoMvtRepository()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (None,)
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        result = repo.get_tile("country", 1, 2, 3)

        assert result is None

    def test_get_tile_raises_for_unknown_layer(self):
        """Rzuca wyjątek dla nieznanej warstwy."""
        repo = DjangoMvtRepository()

        with pytest.raises(InfrastructureException, match="Nieznana warstwa MVT"):
            repo.get_tile("unknown_layer", 1, 2, 3)

    @patch("infrastructure.adapters.persistence.django_mvt_repo.connection")
    def test_get_tile_executes_sql_with_params(self, mock_connection):
        """Wykonuje SQL z poprawnymi parametrami."""
        repo = DjangoMvtRepository()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        repo.get_tile("macroregion", 5, 10, 15)

        mock_cursor.execute.assert_called_once()
        args = mock_cursor.execute.call_args[0]
        assert args[1] == [5, 10, 15, "macroregion"]

    @patch("infrastructure.adapters.persistence.django_mvt_repo.connection")
    def test_get_tile_uses_correct_table_for_layer(self, mock_connection):
        """Używa poprawnej tabeli dla danej warstwy."""
        repo = DjangoMvtRepository()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        repo.get_tile("mesoregion", 1, 2, 3)

        query = mock_cursor.execute.call_args[0][0]
        assert "odznaki_mesoregion" in query

    @patch("infrastructure.adapters.persistence.django_mvt_repo.connection")
    def test_get_tile_for_tourist_region(self, mock_connection):
        """Pobiera kafelek dla warstwy tourist_region."""
        repo = DjangoMvtRepository()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (b"tile_data",)
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        result = repo.get_tile("tourist_region", 1, 2, 3)

        assert result == b"tile_data"
        query = mock_cursor.execute.call_args[0][0]
        assert "tourist_region" in query
