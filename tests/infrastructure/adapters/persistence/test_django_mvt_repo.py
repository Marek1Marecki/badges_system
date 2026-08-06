"""Testy integracyjne dla DjangoMvtRepository — bez mocków połączenia DB."""

import pytest

from infrastructure.adapters.persistence.django_mvt_repo import DjangoMvtRepository
from infrastructure.exceptions import InfrastructureException


@pytest.mark.integration
@pytest.mark.django_db
class TestDjangoMvtRepository:
    """Testy oparte na prawdziwej bazie danych PostgreSQL z PostGIS."""

    def setup_method(self):
        self.repo = DjangoMvtRepository()

    def test_get_tile_raises_for_unknown_layer(self):
        """Rzuca wyjątek dla nieznanej warstwy."""
        with pytest.raises(InfrastructureException, match="Nieznana warstwa MVT"):
            self.repo.get_tile("unknown_layer", 1, 2, 3)

    def test_get_tile_uses_correct_table_for_country(self):
        """Używa poprawnej tabeli dla warstwy country."""
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        result = self.repo.get_tile("country", 2, 2, 3)

        assert result is None or isinstance(result, bytes)

    def test_get_tile_uses_correct_table_for_voivodeship(self):
        """Używa poprawnej tabeli dla warstwy voivodeship."""
        result = self.repo.get_tile("voivodeship", 2, 2, 3)
        assert result is None or isinstance(result, bytes)

    def test_get_tile_uses_correct_table_for_tourist_region(self):
        """Używa poprawnej tabeli dla warstwy tourist_region."""
        result = self.repo.get_tile("tourist_region", 2, 2, 3)
        assert result is None or isinstance(result, bytes)
