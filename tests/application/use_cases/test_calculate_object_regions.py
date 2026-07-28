"""Testy jednostkowe dla CalculateObjectRegionsUseCase."""

from unittest.mock import MagicMock

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

    def test_execute_skips_when_object_not_found(self):
        """Test pomijania gdy obiekt nie istnieje (brak geometrii)."""
        repo = MagicMock()
        repo.check_object_geometry_and_tags.return_value = (False, {})
        clock = FakeClock()
        uc = CalculateObjectRegionsUseCase(repo, clock)

        uc.execute(999)
        repo.check_object_geometry_and_tags.assert_called_once_with(999)
        repo.clear_cache_for_object.assert_not_called()

    def test_execute_skips_when_no_geometry(self):
        """Test pomijania gdy obiekt nie ma geometrii."""
        repo = MagicMock()
        repo.check_object_geometry_and_tags.return_value = (False, {})
        clock = FakeClock()
        uc = CalculateObjectRegionsUseCase(repo, clock)

        uc.execute(1)
        repo.check_object_geometry_and_tags.assert_called_once_with(1)
        repo.clear_cache_for_object.assert_not_called()

    def test_execute_success(self):
        """Test pomyślnego obliczenia regionów."""
        repo = MagicMock()
        repo.check_object_geometry_and_tags.return_value = (True, {"name:pl": "Test"})
        clock = FakeClock()
        uc = CalculateObjectRegionsUseCase(repo, clock)

        uc.execute(1)
        repo.check_object_geometry_and_tags.assert_called_once_with(1)
        repo.clear_cache_for_object.assert_called_once_with(object_id=1)
        repo.recalculate_all_region_levels.assert_called_once_with(1)
        repo.recalculate_tourist_regions.assert_called_once_with(1)
        repo.extract_and_save_local_names.assert_called_once_with(1, {"name:pl": "Test"})
        repo.mark_object_as_ready.assert_called_once_with(1)

    def test_extract_and_save_local_names_with_empty_tags(self):
        """Test ekstrakcji nazw lokalnych z pustymi tagami."""
        repo = MagicMock()
        repo.check_object_geometry_and_tags.return_value = (True, None)
        clock = FakeClock()
        uc = CalculateObjectRegionsUseCase(repo, clock)

        uc.execute(1)
        repo.extract_and_save_local_names.assert_not_called()

    def test_extract_and_save_local_names_with_tags(self):
        """Test ekstrakcji nazw lokalnych z tagami."""
        repo = MagicMock()
        repo.check_object_geometry_and_tags.return_value = (True, {"name:pl": "Test", "name:de": "Test_DE"})
        clock = FakeClock()
        uc = CalculateObjectRegionsUseCase(repo, clock)

        uc.execute(1)
        repo.extract_and_save_local_names.assert_called_once_with(1, {"name:pl": "Test", "name:de": "Test_DE"})
