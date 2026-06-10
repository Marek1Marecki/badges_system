"""Testy jednostkowe dla BuildTouristRegionGeometryUseCase."""

from unittest.mock import MagicMock

import pytest

from application.exceptions import UseCaseError
from application.use_cases.build_tourist_region_geometry import BuildTouristRegionGeometryUseCase


class TestBuildTouristRegionGeometryUseCase:
    """Testy klasy BuildTouristRegionGeometryUseCase."""

    def test_init(self):
        """Test inicjalizacji use case."""
        repo = MagicMock()
        uc = BuildTouristRegionGeometryUseCase(repo)
        assert uc._repo == repo

    def test_execute_raises_when_region_not_found(self):
        """Test błędu gdy region nie istnieje."""
        repo = MagicMock()
        repo.get_tourist_region.return_value = None
        uc = BuildTouristRegionGeometryUseCase(repo)

        with pytest.raises(UseCaseError, match="nie istnieje"):
            uc.execute(999)

    def test_execute_success(self):
        """Test pomyślnego zbudowania geometrii regionu."""
        repo = MagicMock()
        region = MagicMock()
        region.name = "Tatry"
        repo.get_tourist_region.return_value = region
        repo.build_union_geometry.return_value = "GEOMETRY"
        repo.find_object_ids_in_sub_regions.return_value = [1, 2, 3]
        uc = BuildTouristRegionGeometryUseCase(repo)

        result = uc.execute(1)
        assert "Sukces" in result
        assert "3 obiektów" in result
        assert "Tatry" in result
        repo.save_region_geometry.assert_called_once_with(1, "GEOMETRY")
        repo.replace_tourist_region_entries.assert_called_once()

    def test_execute_with_no_geometry(self):
        """Test gdy build_union_geometry zwraca None."""
        repo = MagicMock()
        region = MagicMock()
        region.name = "Test Region"
        repo.get_tourist_region.return_value = region
        repo.build_union_geometry.return_value = None
        repo.find_object_ids_in_sub_regions.return_value = [1, 2]
        uc = BuildTouristRegionGeometryUseCase(repo)

        result = uc.execute(1)
        assert "Sukces" in result
        repo.save_region_geometry.assert_not_called()
        repo.replace_tourist_region_entries.assert_called_once()

    def test_execute_with_empty_object_list(self):
        """Test gdy nie ma obiektów w regionie."""
        repo = MagicMock()
        region = MagicMock()
        region.name = "Empty Region"
        repo.get_tourist_region.return_value = region
        repo.build_union_geometry.return_value = "GEOMETRY"
        repo.find_object_ids_in_sub_regions.return_value = []
        uc = BuildTouristRegionGeometryUseCase(repo)

        result = uc.execute(1)
        assert "Sukces" in result
        assert "0 obiektów" in result
