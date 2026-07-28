"""Testy jednostkowe dla BuildTouristRegionGeometryUseCase."""

from unittest.mock import MagicMock

from application.use_cases.build_tourist_region_geometry import BuildTouristRegionGeometryUseCase


class TestBuildTouristRegionGeometryUseCase:
    """Testy klasy BuildTouristRegionGeometryUseCase."""

    def test_init(self):
        """Test inicjalizacji use case."""
        repo = MagicMock()
        uc = BuildTouristRegionGeometryUseCase(repo)
        assert uc._repo == repo

    def test_execute_returns_false_when_region_not_found(self):
        """Test zwracania False gdy region nie istnieje."""
        repo = MagicMock()
        repo.update_region_geometry.return_value = False
        uc = BuildTouristRegionGeometryUseCase(repo)

        result = uc.execute(999)
        assert "Brak geometrii" in result

    def test_execute_success(self):
        """Test pomyślnego zbudowania geometrii regionu."""
        repo = MagicMock()
        repo.update_region_geometry.return_value = True
        uc = BuildTouristRegionGeometryUseCase(repo)

        result = uc.execute(1)
        assert "Sukces" in result
        assert "1" in result
        repo.update_region_geometry.assert_called_once_with(1)

    def test_execute_with_no_geometry(self):
        """Test gdy adapter zwraca False (brak geometrii do scalenia)."""
        repo = MagicMock()
        repo.update_region_geometry.return_value = False
        uc = BuildTouristRegionGeometryUseCase(repo)

        result = uc.execute(1)
        assert "Brak geometrii" in result
        repo.update_region_geometry.assert_called_once_with(1)

    def test_execute_with_empty_object_list(self):
        """Test pomyślnego scalenia geometrii (nie sprawdza już listy obiektów)."""
        repo = MagicMock()
        repo.update_region_geometry.return_value = True
        uc = BuildTouristRegionGeometryUseCase(repo)

        result = uc.execute(1)
        assert "Sukces" in result
        repo.update_region_geometry.assert_called_once_with(1)
