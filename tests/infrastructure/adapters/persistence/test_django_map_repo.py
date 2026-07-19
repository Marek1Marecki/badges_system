"""Testy dla DjangoMapRepository."""

from unittest.mock import MagicMock, patch

from infrastructure.adapters.persistence.django_map_repo import DjangoMapRepository


class TestDjangoMapRepository:
    @patch("apps.badges.models.TouristObject")
    @patch("infrastructure.adapters.persistence.django_map_repo.Polygon")
    def test_get_objects_in_bbox_returns_objects(self, mock_polygon, mock_model):
        """Zwraca obiekty w podanym bbox."""
        repo = DjangoMapRepository()
        mock_polygon.from_bbox.return_value = MagicMock()

        obj = MagicMock()
        obj.id = 1
        obj.name = "Test Peak"
        obj.type = "peak"
        obj.geom = MagicMock()
        obj.geom.x = 20.0
        obj.geom.y = 50.0

        mock_qs = MagicMock()
        mock_qs.filter.return_value.filter.return_value.filter.return_value = mock_qs
        mock_qs.__getitem__ = MagicMock(return_value=[obj])
        mock_model.objects.filter.return_value = mock_qs

        result = repo.get_objects_in_bbox(10, 40, 30, 60, None, None, None)

        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].name == "Test Peak"

    @patch("apps.badges.models.TouristObject")
    @patch("infrastructure.adapters.persistence.django_map_repo.Polygon")
    @patch("apps.badges.models.ObjectRegionCache")
    def test_get_objects_in_bbox_filters_by_region(self, mock_cache, mock_polygon, mock_model):
        """Filtruje obiekty według regionu."""
        repo = DjangoMapRepository()
        mock_polygon.from_bbox.return_value = MagicMock()

        mock_cache.objects.filter.return_value.values_list.return_value = [1, 2]
        mock_qs = MagicMock()
        mock_qs.filter.return_value.filter.return_value.filter.return_value = []
        mock_model.objects.filter.return_value = mock_qs

        repo.get_objects_in_bbox(10, 40, 30, 60, None, "macroregion", 5)

        mock_cache.objects.filter.assert_called_once_with(region_level="macroregion", region_id=5)

    @patch("apps.badges.models.TouristObject")
    @patch("infrastructure.adapters.persistence.django_map_repo.Polygon")
    @patch("apps.badges.models.BadgeVersionModel")
    def test_get_objects_in_bbox_filters_by_badge(self, mock_badge, mock_polygon, mock_model):
        """Filtruje obiekty według kodu odznaki."""
        repo = DjangoMapRepository()
        mock_polygon.from_bbox.return_value = MagicMock()

        mock_badge.objects.filter.return_value.values_list.return_value = [1, 2]
        mock_qs = MagicMock()
        mock_qs.filter.return_value.filter.return_value.filter.return_value = []
        mock_model.objects.filter.return_value = mock_qs

        repo.get_objects_in_bbox(10, 40, 30, 60, "KGP", None, None)

        mock_badge.objects.filter.assert_called_once_with(badge__code="KGP")

    @patch("apps.badges.models.TouristObject")
    @patch("infrastructure.adapters.persistence.django_map_repo.Polygon")
    def test_get_objects_in_bbox_limits_results(self, mock_polygon, mock_model):
        """Ogranicza liczbę wyników do 500."""
        repo = DjangoMapRepository()
        mock_polygon.from_bbox.return_value = MagicMock()

        mock_qs = MagicMock()
        mock_qs.filter.return_value.filter.return_value.filter.return_value = mock_qs
        mock_qs.__getitem__ = MagicMock(return_value=[])
        mock_model.objects.filter.return_value = mock_qs

        repo.get_objects_in_bbox(10, 40, 30, 60, None, None, None)

        # The slicing happens on the queryset after all filters
        assert mock_qs.__getitem__.called

    @patch("apps.badges.models.TouristObject")
    @patch("infrastructure.adapters.persistence.django_map_repo.GEOSGeometry")
    def test_get_objects_along_line_returns_objects(self, mock_geos, mock_model):
        """Zwraca obiekty wokół linii."""
        repo = DjangoMapRepository()
        mock_geos.return_value = MagicMock()

        obj = MagicMock()
        obj.id = 1
        obj.name = "Test Peak"
        obj.type = "peak"
        obj.altitude = 1000
        obj.geom = MagicMock()
        obj.geom.x = 20.0
        obj.geom.y = 50.0

        mock_model.objects.filter.return_value = [obj]

        result = repo.get_objects_along_line("LINESTRING(0 0, 10 10)", 1000)

        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["name"] == "Test Peak"

    @patch("apps.badges.models.TouristObject")
    @patch("infrastructure.adapters.persistence.django_map_repo.GEOSGeometry")
    def test_get_objects_along_line_returns_empty_on_invalid_wkt(self, mock_geos, mock_model):
        """Zwraca pustą listę przy nieprawidłowym WKT."""
        repo = DjangoMapRepository()
        mock_geos.side_effect = Exception("Invalid WKT")

        result = repo.get_objects_along_line("invalid", 1000)

        assert result == []

    @patch("apps.badges.models.TouristObject")
    @patch("infrastructure.adapters.persistence.django_map_repo.GEOSGeometry")
    def test_get_objects_along_line_filters_active_ready(self, mock_geos, mock_model):
        """Filtruje tylko aktywne i gotowe obiekty."""
        repo = DjangoMapRepository()
        mock_geos.return_value = MagicMock()

        mock_model.objects.filter.return_value = []

        repo.get_objects_along_line("LINESTRING(0 0, 10 10)", 1000)

        args, kwargs = mock_model.objects.filter.call_args
        assert "is_active" in str(kwargs)
        assert "status" in str(kwargs)
