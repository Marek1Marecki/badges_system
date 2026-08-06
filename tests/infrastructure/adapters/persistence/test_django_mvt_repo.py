"""Testy jednostkowe dla DjangoMvtRepository."""

from unittest.mock import MagicMock, patch

import pytest

from infrastructure.adapters.persistence.django_mvt_repo import DjangoMvtRepository
from infrastructure.exceptions import InfrastructureException


class TestDjangoMvtRepository:
    """Testy repozytorium kafelków wektorowych."""

    @pytest.fixture
    def repo(self):
        return DjangoMvtRepository()

    def test_get_tile_raises_on_unknown_layer(self, repo):
        """Rzuca InfrastructureException dla nieznanej warstwy."""
        with pytest.raises(InfrastructureException, match="Nieznana warstwa MVT"):
            repo.get_tile("unknown_layer", 1, 0, 0)

    def test_get_tile_returns_bytes_when_tile_exists(self, repo):
        """Zwraca bajty kafelka gdy istnieje."""
        mock_row = (b"mvt_data",)
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = mock_row

        with patch("infrastructure.adapters.persistence.django_mvt_repo.connection.cursor") as mock_cursor_ctx:
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor
            result = repo.get_tile("voivodeship", 5, 10, 15)
            assert result == b"mvt_data"

    def test_get_tile_returns_none_when_no_data(self, repo):
        """Zwraca None gdy kafelek nie istnieje."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None

        with patch("infrastructure.adapters.persistence.django_mvt_repo.connection.cursor") as mock_cursor_ctx:
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor
            result = repo.get_tile("voivodeship", 5, 10, 15)
            assert result is None

    def test_get_tile_returns_none_when_row_has_no_bytes(self, repo):
        """Zwraca None gdy wiersz istnieje ale brak danych MVT."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (None,)

        with patch("infrastructure.adapters.persistence.django_mvt_repo.connection.cursor") as mock_cursor_ctx:
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor
            result = repo.get_tile("voivodeship", 5, 10, 15)
            assert result is None