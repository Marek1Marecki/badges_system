"""Testy dla zadań Celery."""

from unittest.mock import Mock, patch

from django.contrib.gis.geos import Point, Polygon

from apps.badges.models import RegionLevelType, TouristObject, TouristRegionModel
from apps.badges.tasks import build_tourist_region_geometry_task, calculate_object_regions_task


class TestCalculateObjectRegionsTask:
    """Testy zadania calculate_object_regions_task."""

    @patch("apps.badges.tasks.TouristObject.objects.get")
    def test_object_not_exists(self, mock_get):
        mock_get.side_effect = TouristObject.DoesNotExist
        result = calculate_object_regions_task(999)
        assert result == "Błąd: Obiekt o ID 999 nie istnieje."

    @patch("apps.badges.tasks.TouristObject.objects.get")
    def test_object_without_geometry(self, mock_get):
        obj = Mock()
        obj.name = "Test Object"
        obj.geom = None
        mock_get.return_value = obj
        result = calculate_object_regions_task(1)
        assert result == "Pominięto: Obiekt Test Object (ID: 1) nie ma geometrii."

    @patch("apps.badges.tasks.transaction.atomic")
    @patch("apps.badges.tasks.ObjectRegionCache.objects.bulk_create")
    @patch("apps.badges.tasks.ObjectRegionCache.objects.filter")
    @patch("django.contrib.gis.measure.D")
    @patch("apps.badges.tasks.MesoregionModel.objects.filter")
    @patch("apps.badges.tasks.MacroregionModel.objects.filter")
    @patch("apps.badges.tasks.SubprovinceModel.objects.filter")
    @patch("apps.badges.tasks.ProvinceModel.objects.filter")
    @patch("apps.badges.tasks.VoivodeshipModel.objects.filter")
    @patch("apps.badges.tasks.CountryModel.objects.filter")
    @patch("apps.badges.tasks.TouristRegionModel.objects.filter")
    @patch("apps.badges.tasks.TouristObject.objects.get")
    def test_successful_calculation_with_regions(
        self,
        mock_get,
        mock_tourist_filter,
        mock_country_filter,
        mock_voivodeship_filter,
        mock_province_filter,
        mock_subprovince_filter,
        mock_macro_filter,
        mock_meso_filter,
        mock_d_class,
        mock_cache_filter,
        mock_bulk_create,
        mock_atomic,
    ):
        obj = TouristObject(name="Test Peak", geom=Point(20.0, 50.0, srid=4326))
        obj.local_names = {}
        obj.osm_raw_tags = {}
        obj.save = Mock()
        mock_get.return_value = obj

        region = Mock()
        region.id = 1
        region.name = "Test Region"
        region.shape.intersects.return_value = True
        for region_filter in [
            mock_tourist_filter,
            mock_country_filter,
            mock_voivodeship_filter,
            mock_province_filter,
            mock_subprovince_filter,
            mock_macro_filter,
            mock_meso_filter,
        ]:
            region_filter.return_value = [region]

        cache_qs = Mock()
        cache_qs.delete.return_value = None
        mock_cache_filter.return_value = cache_qs
        mock_d_class.return_value = Mock()
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)

        result = calculate_object_regions_task(1)
        assert "Sukces: Przeliczono obiekt 'Test Peak'" in result
        assert "Znaleziono 7 regionów" in result
        mock_bulk_create.assert_called_once()

    @patch("apps.badges.tasks.transaction.atomic")
    @patch("apps.badges.tasks.ObjectRegionCache.objects.bulk_create")
    @patch("apps.badges.tasks.ObjectRegionCache.objects.filter")
    @patch("django.contrib.gis.measure.D")
    @patch("apps.badges.tasks.MesoregionModel.objects.filter")
    @patch("apps.badges.tasks.MacroregionModel.objects.filter")
    @patch("apps.badges.tasks.SubprovinceModel.objects.filter")
    @patch("apps.badges.tasks.ProvinceModel.objects.filter")
    @patch("apps.badges.tasks.VoivodeshipModel.objects.filter")
    @patch("apps.badges.tasks.CountryModel.objects.filter")
    @patch("apps.badges.tasks.TouristRegionModel.objects.filter")
    @patch("apps.badges.tasks.TouristObject.objects.get")
    def test_local_names_extraction(
        self,
        mock_get,
        mock_tourist_filter,
        mock_country_filter,
        mock_voivodeship_filter,
        mock_province_filter,
        mock_subprovince_filter,
        mock_macro_filter,
        mock_meso_filter,
        mock_d_class,
        mock_cache_filter,
        mock_bulk_create,
        mock_atomic,
    ):
        obj = TouristObject(name="Rysy", geom=Point(20.0, 50.0, srid=4326))
        obj.local_names = {"de": "Rysberg"}
        obj.osm_raw_tags = {
            "name:pl": "Rysy",
            "name:cs": "Rysí hora",
            "name:sk": "Rysy vrch",
            "name:de": "Rysberg",
            "name:fr": "Rysy",
        }
        obj.save = Mock()
        mock_get.return_value = obj

        for region_filter in [
            mock_tourist_filter,
            mock_country_filter,
            mock_voivodeship_filter,
            mock_province_filter,
            mock_subprovince_filter,
            mock_macro_filter,
            mock_meso_filter,
        ]:
            region_filter.return_value = []

        cache_qs = Mock()
        cache_qs.delete.return_value = None
        mock_cache_filter.return_value = cache_qs
        mock_d_class.return_value = Mock()
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)

        calculate_object_regions_task(1)

        obj.save.assert_called_once_with(update_fields=["local_names"])
        assert obj.local_names == {"de": "Rysberg", "cs": "Rysí hora", "sk": "Rysy vrch"}
        mock_bulk_create.assert_not_called()


class TestBuildTouristRegionGeometryTask:
    """Testy zadania build_tourist_region_geometry_task."""

    @patch("apps.badges.tasks.TouristRegionModel.objects.get")
    def test_region_not_exists(self, mock_get):
        mock_get.side_effect = TouristRegionModel.DoesNotExist
        result = build_tourist_region_geometry_task(999)
        assert result == "Błąd: Region turystyczny o ID 999 nie istnieje."

    @patch("apps.badges.tasks.transaction.atomic")
    @patch("apps.badges.tasks.ObjectRegionCache.objects.bulk_create")
    @patch("apps.badges.tasks.ObjectRegionCache.objects.filter")
    @patch("apps.badges.tasks.TouristRegionModel.objects.get")
    def test_successful_geometry_building(self, mock_get, mock_cache_filter, mock_bulk_create, mock_atomic):
        region = Mock()
        region.id = 1
        region.name = "Sudety"
        region.provinces.all.return_value = []
        region.subprovinces.all.return_value = []
        region.macroregions.all.return_value = []
        region.mesoregions.all.return_value = []
        region.provinces.values_list.return_value = []
        region.subprovinces.values_list.return_value = []
        region.macroregions.values_list.return_value = []
        region.mesoregions.values_list.return_value = []
        region.save = Mock()
        mock_get.return_value = region

        cache_qs = Mock()
        cache_qs.delete.return_value = None
        cache_qs.values_list.return_value.distinct.return_value = [1, 2, 3]
        mock_cache_filter.return_value = cache_qs
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)

        result = build_tourist_region_geometry_task(1)
        assert result == "Sukces: Przypisano 3 obiektów do Sudety."
        mock_bulk_create.assert_called_once()

    @patch("apps.badges.tasks.transaction.atomic")
    @patch("apps.badges.tasks.ObjectRegionCache.objects.bulk_create")
    @patch("apps.badges.tasks.ObjectRegionCache.objects.filter")
    @patch("apps.badges.tasks.TouristRegionModel.objects.get")
    def test_geometry_building_with_polygon(self, mock_get, mock_cache_filter, mock_bulk_create, mock_atomic):
        region = Mock()
        region.id = 1
        region.name = "Test Region"
        polygon = Polygon(((0, 0), (1, 0), (1, 1), (0, 1), (0, 0)))
        item = Mock()
        item.shape = polygon

        region.provinces.all.return_value = [item]
        region.subprovinces.all.return_value = []
        region.macroregions.all.return_value = []
        region.mesoregions.all.return_value = []
        region.provinces.values_list.return_value = []
        region.subprovinces.values_list.return_value = []
        region.macroregions.values_list.return_value = []
        region.mesoregions.values_list.return_value = []
        region.save = Mock()
        mock_get.return_value = region

        cache_qs = Mock()
        cache_qs.delete.return_value = None
        cache_qs.values_list.return_value.distinct.return_value = []
        mock_cache_filter.return_value = cache_qs
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)

        with patch("apps.badges.tasks.GeometryCollection") as mock_gc:
            mock_gc.return_value.unary_union = polygon
            build_tourist_region_geometry_task(1)
            region.save.assert_called_once_with(update_fields=["shape"])
            mock_bulk_create.assert_not_called()

    @patch("apps.badges.tasks.transaction.atomic")
    @patch("apps.badges.tasks.ObjectRegionCache.objects.bulk_create")
    @patch("apps.badges.tasks.ObjectRegionCache.objects.filter")
    @patch("apps.badges.tasks.TouristRegionModel.objects.get")
    def test_cache_entries_creation(self, mock_get, mock_cache_filter, mock_bulk_create, mock_atomic):
        region = Mock()
        region.id = 1
        region.name = "Test Region"
        region.provinces.all.return_value = []
        region.subprovinces.all.return_value = []
        region.macroregions.all.return_value = []
        region.mesoregions.all.return_value = []
        region.provinces.values_list.return_value = [1]
        region.subprovinces.values_list.return_value = [2]
        region.macroregions.values_list.return_value = [3]
        region.mesoregions.values_list.return_value = [4]
        region.save = Mock()
        mock_get.return_value = region

        cache_qs = Mock()
        cache_qs.delete.return_value = None
        cache_qs.values_list.return_value.distinct.return_value = [1, 2, 3]
        mock_cache_filter.return_value = cache_qs
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)

        build_tourist_region_geometry_task(1)

        entries = mock_bulk_create.call_args[0][0]
        assert len(entries) == 3
        for entry in entries:
            assert entry.region_level == RegionLevelType.TOURIST_REGION
            assert entry.region_id == 1
            assert entry.region_name == "Test Region"
            assert entry.distance_meters == 0.0
            assert entry.tourist_object_id in [1, 2, 3]
        assert mock_bulk_create.call_args[1]["ignore_conflicts"] is True
