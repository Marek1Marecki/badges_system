"""Testy dla adaptera OSM."""

import json
import urllib.error
import urllib.request
from unittest.mock import Mock, patch

import pytest

from infrastructure.adapters.osm_adapter import (
    OsmAdapterError,
    OsmDataExtractor,
    OsmNodeDTO,
    OverpassClient,
)


class TestOsmNodeDTO:
    """Testy klasy OsmNodeDTO."""

    def test_node_dto_with_lat_lon(self):
        """Test DTO z współrzędnymi lat/lon."""
        dto = OsmNodeDTO(id=123, type="node", lat=50.0, lon=20.0, tags={"name": "Test Peak"})

        assert dto.latitude == 50.0
        assert dto.longitude == 20.0

    def test_node_dto_with_center_coordinates(self):
        """Test DTO ze współrzędnymi w center."""
        dto = OsmNodeDTO(id=456, type="way", center={"lat": 51.0, "lon": 21.0}, tags={"name": "Test Area"})

        assert dto.latitude == 51.0
        assert dto.longitude == 21.0

    def test_node_dto_without_coordinates_raises_error(self):
        """Test DTO bez współrzędnych rzuca błąd."""
        dto = OsmNodeDTO(id=789, type="relation", tags={"name": "Test Relation"})

        with pytest.raises(ValueError, match="Brak współrzędnych dla obiektu relation/789"):
            _ = dto.latitude

        with pytest.raises(ValueError, match="Brak współrzędnych dla obiektu relation/789"):
            _ = dto.longitude

    def test_node_dto_prefer_lat_lon_over_center(self):
        """Test DTO preferuje lat/lon nad center."""
        dto = OsmNodeDTO(
            id=123, type="node", lat=50.0, lon=20.0, center={"lat": 51.0, "lon": 21.0}, tags={"name": "Test"}
        )

        assert dto.latitude == 50.0
        assert dto.longitude == 20.0


class TestOverpassClient:
    """Testy klasy OverpassClient."""

    def test_invalid_osm_id_format(self):
        """Test nieprawidłowego formatu OSM ID."""
        client = OverpassClient()

        with pytest.raises(OsmAdapterError, match="Nieprawidłowy format osm_id"):
            client.fetch_object("invalid_format")

    def test_unsupported_osm_type(self):
        """Test nieobsługiwanego typu OSM."""
        client = OverpassClient()

        with pytest.raises(OsmAdapterError, match="Nieobsługiwany typ OSM"):
            client.fetch_object("invalid/123")

    @patch("urllib.request.urlopen")
    def test_successful_fetch(self, mock_urlopen):
        """Test udanego pobierania danych."""
        mock_response = Mock()
        mock_response.read.return_value.decode.return_value = json.dumps(
            {"elements": [{"id": 123, "type": "node", "lat": 50.0, "lon": 20.0, "tags": {"name": "Test Peak"}}]}
        )
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = OverpassClient()
        result = client.fetch_object("node/123")

        assert isinstance(result, OsmNodeDTO)
        assert result.id == 123
        assert result.type == "node"
        assert result.latitude == 50.0
        assert result.longitude == 20.0

    @patch("urllib.request.urlopen")
    @patch("infrastructure.adapters.osm_adapter.time.sleep")
    def test_retry_mechanism(self, mock_sleep, mock_urlopen):
        """Test mechanizmu ponawiania."""
        # Przygotowujemy mock responses
        mock_response_success = Mock()
        mock_response_success.read.return_value.decode.return_value = json.dumps(
            {"elements": [{"id": 123, "type": "node", "lat": 50.0, "lon": 20.0, "tags": {"name": "Test Peak"}}]}
        )
        mock_response_success.__enter__ = Mock(return_value=mock_response_success)
        mock_response_success.__exit__ = Mock(return_value=None)

        # Pierwsze dwie próby kończą się błędem, trzecia się udaje
        mock_urlopen.side_effect = [
            urllib.error.URLError("Network error"),
            urllib.error.URLError("Network error"),
            mock_response_success,
        ]

        client = OverpassClient()
        result = client.fetch_object("node/123")

        assert isinstance(result, OsmNodeDTO)
        assert mock_sleep.call_count == 2

    @patch("urllib.request.urlopen")
    @patch("infrastructure.adapters.osm_adapter.time.sleep")
    def test_max_retries_exceeded(self, mock_sleep, mock_urlopen):
        """Test przekroczenia maksymalnej liczby prób."""
        mock_urlopen.side_effect = urllib.error.URLError("Network error")

        client = OverpassClient()

        with pytest.raises(OsmAdapterError, match="Nie udało się połączyć z Overpass API po 3 próbach"):
            client.fetch_object("node/123")

    @patch("urllib.request.urlopen")
    def test_http_4xx_error(self, mock_urlopen):
        """Test błędu HTTP 4xx."""
        mock_urlopen.side_effect = urllib.error.HTTPError(url="test_url", code=404, msg="Not Found", hdrs=None, fp=None)

        client = OverpassClient()

        with pytest.raises(OsmAdapterError, match="Odrzucono zapytanie \\(404\\)"):
            client.fetch_object("node/123")

    @patch("urllib.request.urlopen")
    @patch("infrastructure.adapters.osm_adapter.time.sleep")
    def test_http_429_error_retries(self, mock_sleep, mock_urlopen):
        """Test błędu 429 Too Many Requests z ponowieniem."""
        mock_response_429 = urllib.error.HTTPError(
            url="test_url", code=429, msg="Too Many Requests", hdrs=None, fp=None
        )

        mock_response_success = Mock()
        mock_response_success.read.return_value.decode.return_value = json.dumps(
            {"elements": [{"id": 123, "type": "node", "lat": 50.0, "lon": 20.0, "tags": {"name": "Test Peak"}}]}
        )
        mock_response_success.__enter__ = Mock(return_value=mock_response_success)
        mock_response_success.__exit__ = Mock(return_value=None)

        mock_urlopen.side_effect = [mock_response_429, mock_response_success]

        client = OverpassClient()
        result = client.fetch_object("node/123")

        assert isinstance(result, OsmNodeDTO)

    @patch("urllib.request.urlopen")
    def test_empty_response_elements(self, mock_urlopen):
        """Test pustej odpowiedzi z OSM."""
        mock_response = Mock()
        mock_response.read.return_value.decode.return_value = json.dumps({"elements": []})
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = OverpassClient()

        with pytest.raises(OsmAdapterError, match="Obiekt node/123 nie został znaleziony w OSM"):
            client.fetch_object("node/123")

    @patch("urllib.request.urlopen")
    def test_json_decode_error(self, mock_urlopen):
        """Test błędu dekodowania JSON."""
        mock_response = Mock()
        mock_response.read.return_value.decode.return_value = "invalid json"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = OverpassClient()

        with pytest.raises(OsmAdapterError, match="Nie udało się połączyć z Overpass API po 3 próbach"):
            client.fetch_object("node/123")

    @patch("urllib.request.urlopen")
    def test_dto_validation_error(self, mock_urlopen):
        """Test błędu walidacji DTO."""
        mock_response = Mock()
        mock_response.read.return_value.decode.return_value = json.dumps(
            {
                "elements": [
                    {
                        # Brak wymaganego pola 'id'
                        "type": "node",
                        "lat": 50.0,
                        "lon": 20.0,
                        "tags": {"name": "Test Peak"},
                    }
                ]
            }
        )
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = OverpassClient()

        with pytest.raises(OsmAdapterError, match="Błąd parsowania danych z OSM"):
            client.fetch_object("node/123")

    def test_urls_rotation(self):
        """Test rotacji URL-i Overpass."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("Network error")

            client = OverpassClient()

            try:
                client.fetch_object("node/123", max_retries=4)
            except OsmAdapterError:
                pass

            # Sprawdzamy, że zostały użyte różne URL-e
            calls = mock_urlopen.call_args_list
            urls = [call[0][0].full_url for call in calls]

            # Powinny być użyte wszystkie 3 URL-e, a potem ponownie pierwszy
            assert len(urls) == 4
            assert urls[0] != urls[1] != urls[2]


class TestOsmDataExtractor:
    """Testy klasy OsmDataExtractor."""

    def test_extract_name_prefer_polish(self):
        """Test ekstrakcji nazwy z preferencją języka polskiego."""
        tags = {"name": "Test Peak", "name:pl": "Testowy Szczyt", "alt_name": "Alternative Name"}

        result = OsmDataExtractor.extract_name(tags)
        assert result == "Testowy Szczyt"

    def test_extract_name_fallback_to_english(self):
        """Test ekstrakcji nazwy z fallbackiem do angielskiego."""
        tags = {"name": "Test Peak", "alt_name": "Alternative Name"}

        result = OsmDataExtractor.extract_name(tags)
        assert result == "Test Peak"

    def test_extract_name_fallback_to_alt_name(self):
        """Test ekstrakcji nazwy z fallbackiem do alt_name."""
        tags = {"alt_name": "Alternative Name"}

        result = OsmDataExtractor.extract_name(tags)
        assert result == "Alternative Name"

    def test_extract_name_no_name_available(self):
        """Test ekstrakcji nazwy gdy brak dostępnych nazw."""
        tags = {"ele": "1234"}

        result = OsmDataExtractor.extract_name(tags)
        assert result is None

    def test_extract_alt_name_polish(self):
        """Test ekstrakcji alternatywnej nazwy polskiej."""
        tags = {"alt_name:pl": "Alternatywna Nazwa PL", "alt_name": "Alternative Name"}
        primary_name = "Główna Nazwa"

        result = OsmDataExtractor.extract_alt_name(tags, primary_name)
        assert result == "Alternatywna Nazwa PL"

    def test_extract_alt_name_english(self):
        """Test ekstrakcji alternatywnej nazwy angielskiej."""
        tags = {"alt_name": "Alternative Name"}
        primary_name = "Główna Nazwa"

        result = OsmDataExtractor.extract_alt_name(tags, primary_name)
        assert result == "Alternative Name"

    def test_extract_alt_name_same_as_primary(self):
        """Test ekstrakcji alternatywnej nazwy identycznej z główną."""
        tags = {"alt_name": "Same Name"}
        primary_name = "Same Name"

        result = OsmDataExtractor.extract_alt_name(tags, primary_name)
        assert result is None

    def test_extract_alt_name_no_alternative(self):
        """Test ekstrakcji alternatywnej nazwy gdy brak."""
        tags = {}
        primary_name = "Main Name"

        result = OsmDataExtractor.extract_alt_name(tags, primary_name)
        assert result is None

    def test_extract_altitude_valid_integer(self):
        """Test ekstrakcji wysokości z poprawną liczbą."""
        tags = {"ele": "1234"}

        result = OsmDataExtractor.extract_altitude(tags)
        assert result == 1234

    def test_extract_altitude_with_units(self):
        """Test ekstrakcji wysokości z jednostkami."""
        tags = {"ele": "1234 m"}

        result = OsmDataExtractor.extract_altitude(tags)
        assert result == 1234

    def test_extract_altitude_negative_value(self):
        """Test ekstrakcji ujemnej wysokości."""
        tags = {"ele": "-15"}

        result = OsmDataExtractor.extract_altitude(tags)
        assert result == -15

    def test_extract_altitude_positive_sign(self):
        """Test ekstrakcji wysokości ze znakiem plus."""
        tags = {"ele": "+1234"}

        result = OsmDataExtractor.extract_altitude(tags)
        assert result == 1234

    def test_extract_altitude_no_value(self):
        """Test ekstrakcji wysokości gdy brak wartości."""
        tags = {}

        result = OsmDataExtractor.extract_altitude(tags)
        assert result is None

    def test_extract_altitude_invalid_value(self):
        """Test ekstrakcji wysokości z niepoprawną wartością."""
        tags = {"ele": "invalid"}

        result = OsmDataExtractor.extract_altitude(tags)
        assert result is None

    @patch("infrastructure.adapters.osm_adapter.OsmTypeMapping.objects")
    def test_determine_type_with_existing_mapping(self, mock_objects):
        """Test określania typu z istniejącym mapowaniem."""
        mock_mapping = Mock()
        mock_mapping.is_ignored = False
        mock_mapping.target_type = "Szczyt"

        mock_objects.get_or_create.return_value = (mock_mapping, False)

        tags = {"natural": "peak"}

        result_type, new_mappings = OsmDataExtractor.determine_type(tags)

        assert result_type == "Szczyt"
        assert new_mappings == []
        mock_objects.get_or_create.assert_called_once_with(
            osm_key="natural", osm_value="peak", defaults={"target_type": "", "is_ignored": False}
        )

    @patch("infrastructure.adapters.osm_adapter.OsmTypeMapping.objects")
    def test_determine_type_with_new_mapping(self, mock_objects):
        """Test określania typu z nowym mapowaniem."""
        mock_mapping = Mock()
        mock_mapping.is_ignored = False
        mock_mapping.target_type = ""

        mock_objects.get_or_create.return_value = (mock_mapping, True)

        tags = {"natural": "peak"}

        result_type, new_mappings = OsmDataExtractor.determine_type(tags)

        assert result_type is None
        assert new_mappings == ["natural=peak"]

    @patch("infrastructure.adapters.osm_adapter.OsmTypeMapping.objects")
    def test_determine_type_ignored_mapping(self, mock_objects):
        """Test określania typu z ignorowanym mapowaniem."""
        mock_mapping = Mock()
        mock_mapping.is_ignored = True
        mock_mapping.target_type = "Szczyt"

        mock_objects.get_or_create.return_value = (mock_mapping, False)

        tags = {"natural": "peak"}

        result_type, new_mappings = OsmDataExtractor.determine_type(tags)

        assert result_type is None
        assert new_mappings == []

    @patch("infrastructure.adapters.osm_adapter.OsmTypeMapping.objects")
    def test_determine_type_multiple_classifying_keys(self, mock_objects):
        """Test określania typu z wieloma kluczami klasyfikującymi."""
        mock_mapping_ignored = Mock()
        mock_mapping_ignored.is_ignored = True
        mock_mapping_ignored.target_type = "Ignored Type"

        mock_mapping_valid = Mock()
        mock_mapping_valid.is_ignored = False
        mock_mapping_valid.target_type = "Szczyt"

        mock_objects.get_or_create.side_effect = [(mock_mapping_ignored, False), (mock_mapping_valid, False)]

        tags = {"natural": "peak", "tourism": "viewpoint"}

        result_type, new_mappings = OsmDataExtractor.determine_type(tags)

        assert result_type == "Szczyt"
        assert new_mappings == []

    @patch("infrastructure.adapters.osm_adapter.OsmTypeMapping.objects")
    def test_determine_type_no_classifying_keys(self, mock_objects):
        """Test określania typu bez kluczy klasyfikujących."""
        tags = {"name": "Test Peak", "ele": "1234"}

        result_type, new_mappings = OsmDataExtractor.determine_type(tags)

        assert result_type is None
        assert new_mappings == []
        mock_objects.get_or_create.assert_not_called()

    def test_extract_wikipedia_link_polish(self):
        """Test ekstrakcji linku do polskiej Wikipedii."""
        tags = {"wikipedia:pl": "Rysy"}

        result = OsmDataExtractor.extract_wikipedia_link(tags)
        assert result == "https://pl.wikipedia.org/wiki/Rysy"

    def test_extract_wikipedia_link_general(self):
        """Test ekstrakcji linku z ogólnego tagu wikipedia."""
        tags = {"wikipedia": "pl:Rysy"}

        result = OsmDataExtractor.extract_wikipedia_link(tags)
        assert result == "https://pl.wikipedia.org/wiki/Rysy"

    def test_extract_wikipedia_link_slovak(self):
        """Test ekstrakcji linku do słowackiej Wikipedii."""
        tags = {"wikipedia:sk": "Rysy"}

        result = OsmDataExtractor.extract_wikipedia_link(tags)
        assert result == "https://sk.wikipedia.org/wiki/Rysy"

    def test_extract_wikipedia_link_czech(self):
        """Test ekstrakcji linku do czeskiej Wikipedii."""
        tags = {"wikipedia:cs": "Sněžka"}

        result = OsmDataExtractor.extract_wikipedia_link(tags)
        assert result == "https://cs.wikipedia.org/wiki/Sněžka"

    def test_extract_wikipedia_link_priority(self):
        """Test priorytetu ekstrakcji linków wiki."""
        tags = {"wikipedia:pl": "Rysy", "wikipedia": "en:Rysy Peak", "wikipedia:sk": "Rysy"}

        result = OsmDataExtractor.extract_wikipedia_link(tags)
        assert result == "https://pl.wikipedia.org/wiki/Rysy"

    def test_extract_wikipedia_link_with_spaces(self):
        """Test ekstrakcji linku ze spacjami w tytule."""
        tags = {"wikipedia": "pl:Mount Everest"}

        result = OsmDataExtractor.extract_wikipedia_link(tags)
        assert result == "https://pl.wikipedia.org/wiki/Mount_Everest"

    def test_extract_wikipedia_link_no_colon_format(self):
        """Test ekstrakcji linku z formatem bez dwukropka."""
        tags = {"wikipedia": "Rysy"}

        result = OsmDataExtractor.extract_wikipedia_link(tags)
        assert result == "https://pl.wikipedia.org/wiki/Rysy"

    def test_extract_wikipedia_link_no_wiki_tags(self):
        """Test ekstrakcji linku gdy brak tagów wiki."""
        tags = {"name": "Test Peak", "ele": "1234"}

        result = OsmDataExtractor.extract_wikipedia_link(tags)
        assert result is None

    def test_classifying_keys_constant(self):
        """Test stałej CLASSIFYING_KEYS."""
        expected_keys = {"natural", "tourism", "historic", "waterway", "man_made", "building", "tower:type"}

        assert OsmDataExtractor.CLASSIFYING_KEYS == expected_keys
