"""Testy dla OsmRepository."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from infrastructure.adapters.osm_adapter import OsmAdapterError
from infrastructure.adapters.osm_repository import OsmRepository


class TestOsmRepository:
    @patch("apps.badges.models.TouristObject")
    def test_get_object_for_osm_fetch_returns_data(self, mock_model):
        """Zwraca dane obiektu gdy istnieje."""
        repo = OsmRepository()
        obj = MagicMock()
        obj.id = 1
        obj.osm_id = "node/123"
        obj.name = "Test Peak"
        obj.alt_name = "Alt Name"
        obj.altitude = 1000
        obj.wikipedia_link = "https://wiki"
        obj.geom = "POINT(10 20)"
        obj.type = "peak"
        mock_model.objects.get.return_value = obj

        result = repo.get_object_for_osm_fetch(1)

        assert result is not None
        assert result["id"] == 1
        assert result["osm_id"] == "node/123"
        assert result["name"] == "Test Peak"

    @patch("apps.badges.models.TouristObject")
    def test_get_object_for_osm_fetch_returns_none_when_not_found(self, mock_model):
        """Zwraca None gdy obiekt nie istnieje."""
        repo = OsmRepository()
        
        class DoesNotExist(Exception):
            pass
        
        mock_model.DoesNotExist = DoesNotExist
        mock_model.objects.get.side_effect = DoesNotExist()

        result = repo.get_object_for_osm_fetch(999)

        assert result is None

    @patch("infrastructure.adapters.osm_repository.OverpassClient")
    def test_fetch_from_osm_delegates_to_client(self, mock_client):
        """Deleguje pobieranie do OverpassClient."""
        repo = OsmRepository()
        mock_node = MagicMock()
        mock_client.return_value.fetch_object.return_value = mock_node

        result = repo.fetch_from_osm("node/123")

        assert result == mock_node

    @patch("infrastructure.adapters.osm_repository.OverpassClient")
    def test_fetch_multiple_from_osm_returns_results(self, mock_client):
        """Zwraca wyniki gdy pobieranie się powiedzie."""
        repo = OsmRepository()
        mock_results = {"node/123": MagicMock()}
        mock_client.return_value.fetch_multiple_objects.return_value = mock_results

        result = repo.fetch_multiple_from_osm(["node/123"])

        assert result == mock_results

    @patch("infrastructure.adapters.osm_repository.OverpassClient")
    def test_fetch_multiple_from_osm_returns_none_on_error(self, mock_client):
        """Zwraca None przy błędzie OSM."""
        repo = OsmRepository()
        mock_client.return_value.fetch_multiple_objects.side_effect = OsmAdapterError("Error")

        result = repo.fetch_multiple_from_osm(["node/123"])

        assert result is None

    @patch("apps.badges.models.TouristObject")
    @patch("django.contrib.gis.geos.Point")
    @patch("infrastructure.adapters.osm_repository.OsmDataExtractor")
    def test_update_object_from_osm_updates_fields(self, mock_extractor, mock_point, mock_model):
        """Aktualizuje pola obiektu danymi z OSM."""
        repo = OsmRepository()
        obj = MagicMock()
        obj.id = 1
        obj.name = ""
        obj.alt_name = ""
        obj.altitude = None
        obj.wikipedia_link = ""
        obj.geom = None
        obj.type = ""
        mock_model.objects.get.return_value = obj

        osm_node = MagicMock()
        osm_node.tags = {"name": "OSM Name"}
        osm_node.version = 1
        osm_node.timestamp = datetime.now()
        osm_node.latitude = 50.0
        osm_node.longitude = 20.0

        mock_extractor.extract_name.return_value = "OSM Name"
        mock_extractor.extract_alt_name.return_value = None
        mock_extractor.extract_altitude.return_value = None
        mock_extractor.extract_wikipedia_link.return_value = None
        mock_extractor.determine_type.return_value = ("peak", None)

        current_data = {"name": "", "altitude": None, "wikipedia_link": "", "has_geom": False, "type": ""}

        repo.update_object_from_osm(1, osm_node, current_data)

        assert obj.name == "OSM Name"
        assert obj.status == "READY"
        obj.save.assert_called_once()

    @patch("apps.badges.models.TouristObject")
    def test_get_objects_for_sync_returns_batch(self, mock_model):
        """Zwraca partię obiektów do synchronizacji."""
        repo = OsmRepository()
        obj1 = MagicMock()
        obj1.id = 1
        obj1.osm_id = "node/123"
        obj1.altitude = 1000
        obj1.wikipedia_link = "https://wiki"
        obj1.is_active = True

        mock_qs = MagicMock()
        mock_qs.__getitem__.return_value = [obj1]
        mock_model.objects.exclude.return_value.exclude.return_value.order_by.return_value = mock_qs

        result = repo.get_objects_for_sync(10)

        assert len(result) == 1
        assert result[0]["id"] == 1

    @patch("apps.badges.models.TouristObject")
    def test_update_object_after_sync(self, mock_model):
        """Aktualizuje obiekt po synchronizacji."""
        repo = OsmRepository()
        mock_model.objects.filter.return_value.update.return_value = None

        repo.update_object_after_sync(1, {"tags": {}}, 1, datetime.now(), datetime.now())

        mock_model.objects.filter.assert_called_once_with(id=1)

    @patch("apps.badges.models.TouristObject")
    def test_mark_sync_checked(self, mock_model):
        """Aktualizuje last_sync_check."""
        repo = OsmRepository()
        mock_model.objects.filter.return_value.update.return_value = None

        repo.mark_sync_checked(1, datetime.now())

        mock_model.objects.filter.assert_called_once_with(id=1)

    @patch("apps.badges.models.OsmSyncConflict")
    @patch("apps.badges.models.TouristObject")
    def test_create_osm_sync_conflict_creates_new(self, mock_model, mock_conflict):
        """Tworzy nowy konflikt synchronizacji."""
        repo = OsmRepository()
        obj = MagicMock()
        mock_model.objects.get.return_value = obj
        mock_conflict.objects.get_or_create.return_value = (MagicMock(), True)

        repo.create_osm_sync_conflict(1, "altitude", "1000", "1100")

        mock_conflict.objects.get_or_create.assert_called_once()

    @patch("infrastructure.adapters.osm_repository.OsmDataExtractor")
    @patch("infrastructure.adapters.osm_repository.OsmRepository.create_osm_sync_conflict")
    def test_detect_and_save_conflicts_detects_differences(self, mock_create_conflict, mock_extractor):
        """Wykrywa różnice w danych i zapisuje konflikty."""
        repo = OsmRepository()
        osm_node = MagicMock()
        osm_node.tags = {"ele": "1100", "wikipedia": "https://wiki"}

        mock_extractor.extract_altitude.return_value = 1100
        mock_extractor.extract_wikipedia_link.return_value = "https://wiki"

        current_data = {"altitude": 1000, "wikipedia_link": "https://old"}

        conflicts = repo.detect_and_save_conflicts(1, current_data, osm_node)

        assert conflicts == 2
        assert mock_create_conflict.call_count == 2

    @patch("infrastructure.adapters.osm_repository.OsmDataExtractor")
    @patch("infrastructure.adapters.osm_repository.OsmRepository.create_osm_sync_conflict")
    def test_detect_and_save_conflicts_no_differences(self, mock_create_conflict, mock_extractor):
        """Nie tworzy konfliktów gdy dane są zgodne."""
        repo = OsmRepository()
        osm_node = MagicMock()
        osm_node.tags = {"ele": "1000"}

        mock_extractor.extract_altitude.return_value = 1000
        mock_extractor.extract_wikipedia_link.return_value = None

        current_data = {"altitude": 1000, "wikipedia_link": None}

        conflicts = repo.detect_and_save_conflicts(1, current_data, osm_node)

        assert conflicts == 0
        mock_create_conflict.assert_not_called()
