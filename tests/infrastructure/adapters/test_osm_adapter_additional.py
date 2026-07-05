"""Dodatkowe testy dla OSM Adapter pokrywające brakujące ścieżki."""

from unittest.mock import MagicMock, patch

import pytest

from infrastructure.adapters.osm_adapter import OsmAdapterError, OsmNodeDTO, OverpassClient


class TestOsmNodeDTO:
    def test_latitude_from_lat(self):
        """Zwraca lat gdy jest dostępny."""
        dto = OsmNodeDTO(id=1, type="node", lat=50.0, lon=20.0)
        assert dto.latitude == 50.0

    def test_latitude_from_center(self):
        """Zwraca lat z center gdy lat nie jest dostępny."""
        dto = OsmNodeDTO(id=1, type="way", center={"lat": 50.0, "lon": 20.0})
        assert dto.latitude == 50.0

    def test_latitude_raises_error_when_missing(self):
        """Rzuca błąd gdy brak współrzędnych."""
        dto = OsmNodeDTO(id=1, type="way")
        with pytest.raises(ValueError, match="Brak współrzędnych"):
            _ = dto.latitude

    def test_longitude_from_lon(self):
        """Zwraca lon gdy jest dostępny."""
        dto = OsmNodeDTO(id=1, type="node", lat=50.0, lon=20.0)
        assert dto.longitude == 20.0

    def test_longitude_from_center(self):
        """Zwraca lon z center gdy lon nie jest dostępny."""
        dto = OsmNodeDTO(id=1, type="way", center={"lat": 50.0, "lon": 20.0})
        assert dto.longitude == 20.0

    def test_longitude_raises_error_when_missing(self):
        """Rzuca błąd gdy brak współrzędnych."""
        dto = OsmNodeDTO(id=1, type="way")
        with pytest.raises(ValueError, match="Brak współrzędnych"):
            _ = dto.longitude


class TestOverpassClient:
    def test_raises_error_for_invalid_osm_id_format(self):
        """Rzuca błąd dla nieprawidłowego formatu osm_id."""
        client = OverpassClient()
        with pytest.raises(OsmAdapterError, match="Nieprawidłowy format"):
            client.fetch_object("invalid-id")

    def test_raises_error_for_unsupported_osm_type(self):
        """Rzuca błąd dla nieobsługiwanego typu OSM."""
        client = OverpassClient()
        with pytest.raises(OsmAdapterError, match="Nieobsługiwany typ"):
            client.fetch_object("invalid/123")

    @patch("infrastructure.adapters.osm_adapter.urllib.request.urlopen")
    def test_raises_error_for_404_response(self, mock_urlopen):
        """Rzuca błąd dla odpowiedzi 404."""
        from urllib.error import HTTPError

        mock_response = MagicMock()
        mock_response.code = 404
        mock_response.read.return_value = b"Not found"
        mock_urlopen.side_effect = HTTPError("url", 404, "Not Found", {}, None)

        client = OverpassClient()
        with pytest.raises(OsmAdapterError, match="404"):
            client.fetch_object("node/123")

    @patch("infrastructure.adapters.osm_adapter.urllib.request.urlopen")
    def test_raises_error_for_empty_response(self, mock_urlopen):
        """Rzuca błąd gdy odpowiedź jest pusta."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"elements": []}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = OverpassClient()
        with pytest.raises(OsmAdapterError, match="nie został znaleziony"):
            client.fetch_object("node/123")

    @patch("infrastructure.adapters.osm_adapter.urllib.request.urlopen")
    def test_raises_error_for_no_elements_in_response(self, mock_urlopen):
        """Rzuca błąd gdy brak elements w odpowiedzi."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"{}"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = OverpassClient()
        with pytest.raises(OsmAdapterError, match="Brak danych"):
            client.fetch_object("node/123")

    @patch("infrastructure.adapters.osm_adapter.urllib.request.urlopen")
    def test_raises_error_after_max_retries(self, mock_urlopen):
        """Rzuca błąd po wyczerpaniu prób."""
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("Connection failed")

        client = OverpassClient()
        with pytest.raises(OsmAdapterError, match="Nie udało się połączyć"):
            client.fetch_object("node/123", max_retries=2)

    def test_fetch_multiple_objects_returns_empty_for_empty_list(self):
        """Zwraca pusty słownik dla pustej listy."""
        client = OverpassClient()
        result = client.fetch_multiple_objects([])
        assert result == {}

    @patch("infrastructure.adapters.osm_adapter.urllib.request.urlopen")
    def test_fetch_multiple_objects_handles_429_rate_limit(self, mock_urlopen):
        """Czeka przy limicie szybkości (429)."""
        from urllib.error import HTTPError

        mock_response = MagicMock()
        mock_response.code = 429
        mock_urlopen.side_effect = HTTPError("url", 429, "Too Many Requests", {}, None)

        client = OverpassClient()
        # Should retry on 429
        with pytest.raises(OsmAdapterError):
            client.fetch_multiple_objects(["node/123"], max_retries=2)

    @patch("infrastructure.adapters.osm_adapter.urllib.request.urlopen")
    def test_fetch_multiple_objects_raises_for_400_404(self, mock_urlopen):
        """Rzuca błąd dla 400/404 przy masowym pobieraniu."""
        from urllib.error import HTTPError

        mock_response = MagicMock()
        mock_response.code = 404
        mock_response.read.return_value = b"Not found"
        mock_urlopen.side_effect = HTTPError("url", 404, "Not Found", {}, None)

        client = OverpassClient()
        with pytest.raises(OsmAdapterError, match="404"):
            client.fetch_multiple_objects(["node/123"])

    @patch("infrastructure.adapters.osm_adapter.urllib.request.urlopen")
    def test_fetch_multiple_objects_returns_empty_for_no_queries(self, mock_urlopen):
        """Zwraca pusty słownik gdy wszystkie ID są nieprawidłowe."""
        client = OverpassClient()
        result = client.fetch_multiple_objects(["invalid", "also-invalid"])
        assert result == {}

    @patch("infrastructure.adapters.osm_adapter.urllib.request.urlopen")
    def test_successful_fetch_object(self, mock_urlopen):
        """Pomyślnie pobiera obiekt."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"elements": [{"id": 123, "type": "node", "lat": 50.0, "lon": 20.0}]}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = OverpassClient()
        result = client.fetch_object("node/123")

        assert result.id == 123
        assert result.type == "node"
        assert result.lat == 50.0

    @patch("infrastructure.adapters.osm_adapter.urllib.request.urlopen")
    def test_successful_fetch_way_with_center(self, mock_urlopen):
        """Pomyślnie pobiera way z center."""
        mock_response = MagicMock()
        mock_response.read.return_value = (
            b'{"elements": [{"id": 456, "type": "way", "center": {"lat": 50.0, "lon": 20.0}}]}'
        )
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = OverpassClient()
        result = client.fetch_object("way/456")

        assert result.id == 456
        assert result.type == "way"
        assert result.center == {"lat": 50.0, "lon": 20.0}

    @patch("infrastructure.adapters.osm_adapter.urllib.request.urlopen")
    def test_successful_fetch_multiple_objects(self, mock_urlopen):
        """Pomyślnie pobiera wiele obiektów."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"elements": [{"id": 123, "type": "node", "lat": 50.0, "lon": 20.0}, {"id": 124, "type": "node", "lat": 51.0, "lon": 21.0}]}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = OverpassClient()
        result = client.fetch_multiple_objects(["node/123", "node/124"])

        assert len(result) == 2
        assert "node/123" in result
        assert "node/124" in result
