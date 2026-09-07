"""Testy jednostkowe dla DjangoExploreQueriesRepository."""

from unittest.mock import MagicMock, patch

import pytest

from infrastructure.adapters.persistence.django_explore_queries_repo import (
    DjangoExploreQueriesRepository,
)


class TestDjangoExploreQueriesRepository:
    """Testy repozytorium zapytań eksploracyjnych."""

    @pytest.fixture
    def repo(self):
        return DjangoExploreQueriesRepository()

    def test_get_regions_by_level_voivodeship(self, repo):
        """Zwraca regiony dla poziomu VOIVODESHIP z regions_flat (ADR-028)."""
        mock_qs = MagicMock()
        with patch("apps.badges.models.RegionFlatModel.objects.filter", return_value=mock_qs):
            result = repo.get_regions_by_level("VOIVODESHIP")
            assert result == mock_qs

    def test_get_regions_by_level_macroregion(self, repo):
        """Zwraca regiony dla poziomu MACROREGION z regions_flat (ADR-028)."""
        mock_qs = MagicMock()
        with patch("apps.badges.models.RegionFlatModel.objects.filter", return_value=mock_qs):
            result = repo.get_regions_by_level("MACROREGION")
            assert result == mock_qs

    def test_get_regions_by_level_mesoregion(self, repo):
        """Zwraca regiony dla poziomu MESOREGION z regions_flat (ADR-028)."""
        mock_qs = MagicMock()
        with patch("apps.badges.models.RegionFlatModel.objects.filter", return_value=mock_qs):
            result = repo.get_regions_by_level("MESOREGION")
            assert result == mock_qs

    def test_get_regions_by_level_unknown_returns_empty(self, repo):
        """Dla nieznanego poziomu zwraca pusty QuerySet (filter level=X)."""
        mock_qs = MagicMock()
        with patch("apps.badges.models.RegionFlatModel.objects.filter", return_value=mock_qs):
            result = repo.get_regions_by_level("UNKNOWN")
            assert result == mock_qs

    def test_get_object_region_cache_for_level(self, repo):
        """Filtruje cache regionów według poziomu."""
        mock_qs = MagicMock()
        with patch("apps.badges.models.ObjectRegionCache.objects.filter", return_value=mock_qs) as mock_filter:
            result = repo.get_object_region_cache_for_level("VOIVODESHIP")
            mock_filter.assert_called_once_with(region_level="VOIVODESHIP")
            assert result == mock_qs

    def test_get_points_of_interest_with_relations(self, repo):
        """Zwraca QuerySet z prefetch relacji."""
        mock_qs = MagicMock()
        with patch("apps.badges.models.TouristObject.objects.filter") as mock_filter:
            mock_filter.return_value.select_related.return_value.prefetch_related.return_value = mock_qs
            result = repo.get_points_of_interest_with_relations()
            assert result == mock_qs
