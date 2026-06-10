"""Testy jednostkowe dla CalculateObjectRegionsUseCase."""

from unittest.mock import MagicMock

import pytest

from application.exceptions import UseCaseError
from application.use_cases.calculate_object_regions import CalculateObjectRegionsUseCase
from tests.fakes.clock import FakeClock


class TestCalculateObjectRegionsUseCase:
    """Testy klasy CalculateObjectRegionsUseCase."""

    def test_init(self):
        """Test inicjalizacji use case."""
        repo = MagicMock()
        clock = FakeClock()
        uc = CalculateObjectRegionsUseCase(repo, clock)
        assert uc._repo == repo
        assert uc._clock == clock

    def test_execute_raises_when_object_not_found(self):
        """Test błędu gdy obiekt nie istnieje."""
        repo = MagicMock()
        repo.get_tourist_object.return_value = None
        clock = FakeClock()
        uc = CalculateObjectRegionsUseCase(repo, clock)

        with pytest.raises(UseCaseError, match="nie istnieje"):
            uc.execute(999)

    def test_execute_skips_when_no_geometry(self):
        """Test pomijania gdy obiekt nie ma geometrii."""
        repo = MagicMock()
        obj = MagicMock()
        obj.has_geom = False
        obj.name = "Test Object"
        repo.get_tourist_object.return_value = obj
        clock = FakeClock()
        uc = CalculateObjectRegionsUseCase(repo, clock)

        result = uc.execute(1)
        assert "Pominięto" in result
        assert "nie ma geometrii" in result

    def test_execute_success(self):
        """Test pomyślnego obliczenia regionów."""
        repo = MagicMock()
        obj = MagicMock()
        obj.has_geom = True
        obj.name = "Test Object"
        obj.geom = "POINT(0 0)"
        obj.osm_raw_tags = {"name:pl": "Test"}
        obj.local_names = {}
        repo.get_tourist_object.return_value = obj
        repo.find_regions_for_point.return_value = [1, 2]
        clock = FakeClock()
        uc = CalculateObjectRegionsUseCase(repo, clock)

        result = uc.execute(1)
        assert "Sukces" in result
        assert "2 regionów" in result
        repo.replace_cache_for_object.assert_called_once_with(1, [1, 2])

    def test_extract_and_save_local_names_with_empty_tags(self):
        """Test ekstrakcji nazw lokalnych z pustymi tagami."""
        repo = MagicMock()
        obj = MagicMock()
        obj.has_geom = True
        obj.name = "Test Object"
        obj.osm_raw_tags = None
        obj.local_names = {}
        repo.get_tourist_object.return_value = obj
        repo.find_regions_for_point.return_value = []
        clock = FakeClock()
        uc = CalculateObjectRegionsUseCase(repo, clock)

        uc.execute(1)
        repo.save_local_names.assert_not_called()

    def test_extract_and_save_local_names_with_tags(self):
        """Test ekstrakcji nazw lokalnych z tagami."""
        repo = MagicMock()
        obj = MagicMock()
        obj.has_geom = True
        obj.name = "Test Object"
        obj.osm_raw_tags = {"name:pl": "Test", "name:de": "Test_DE"}
        obj.local_names = {}
        repo.get_tourist_object.return_value = obj
        repo.find_regions_for_point.return_value = []
        clock = FakeClock()
        uc = CalculateObjectRegionsUseCase(repo, clock)

        uc.execute(1)
        repo.save_local_names.assert_called_once()
