"""Testy dla formularzy Django."""

from unittest.mock import Mock, patch

from django.contrib.gis.geos import Point
from django.test import RequestFactory

from apps.badges.forms import DatalistTextInput, TouristObjectAdminForm
from apps.badges.models import TouristObject
from infrastructure.adapters.osm_adapter import OsmAdapterError


class TestDatalistTextInput:
    """Testy widżetu DatalistTextInput."""

    def test_init_with_datalist(self):
        """Test inicjalizacji z listą danych."""
        datalist = ["Szczyt", "Schronisko", "Jaskinia"]
        widget = DatalistTextInput(datalist)
        
        assert widget.datalist == datalist

    def test_render_generates_correct_html(self):
        """Test generowania poprawnego HTML."""
        datalist = ["Szczyt", "Schronisko"]
        widget = DatalistTextInput(datalist)
        
        html = widget.render("field_name", "test_value")
        
        # Sprawdzamy czy zawiera pole input z atrybutem list
        assert 'name="field_name"' in html
        assert 'value="test_value"' in html
        assert 'list="datalist_field_name"' in html
        
        # Sprawdzamy czy zawiera datalist
        assert '<datalist id="datalist_field_name">' in html
        assert '<option value="Szczyt">' in html
        assert '<option value="Schronisko">' in html

    def test_render_with_none_attrs(self):
        """Test renderowania z atrybutami None."""
        datalist = ["Test"]
        widget = DatalistTextInput(datalist)
        
        html = widget.render("field", None, attrs=None)
        
        assert 'list="datalist_field"' in html
        assert '<option value="Test">' in html

    def test_render_with_existing_attrs(self):
        """Test renderowania z istniejącymi atrybutami."""
        datalist = ["Test"]
        widget = DatalistTextInput(datalist)
        
        html = widget.render("field", "value", attrs={"class": "form-control"})
        
        assert 'class="form-control"' in html
        assert 'list="datalist_field"' in html


class TestTouristObjectAdminForm:
    """Testy formularza TouristObjectAdminForm."""

    def test_form_meta_configuration(self):
        """Test konfiguracji Meta klasy formularza."""
        form = TouristObjectAdminForm()
        assert form._meta.model == TouristObject
        assert "name" in form.fields
        assert "geom" in form.fields
        assert "osm_id" in form.fields

    def test_init_sets_type_field_not_required(self):
        """Test inicjalizacji ustawiającej pole type jako niewymagane."""
        form = TouristObjectAdminForm()
        assert form.fields["type"].required is False

    @patch('apps.badges.forms.TouristObject.objects.values_list')
    def test_init_with_database_types(self, mock_values_list):
        """Test inicjalizacji z typami z bazy danych."""
        mock_values_list.return_value.distinct.return_value = ["Szczyt", "Schronisko"]
        
        form = TouristObjectAdminForm()
        widget = form.fields["type"].widget
        
        assert isinstance(widget, DatalistTextInput)
        assert "Szczyt" in widget.datalist
        assert "Schronisko" in widget.datalist
        assert "Jaskinia" in widget.datalist  # default type

    @patch('apps.badges.forms.TouristObject.objects.values_list')
    def test_init_handles_database_exception(self, mock_values_list):
        """Test inicjalizacji obsługującej wyjątek bazy danych."""
        mock_values_list.side_effect = Exception("Database error")
        
        form = TouristObjectAdminForm()
        widget = form.fields["type"].widget
        
        assert isinstance(widget, DatalistTextInput)
        assert "Szczyt" in widget.datalist
        assert "Schronisko" in widget.datalist

    def test_clean_manual_mode_without_name(self):
        """Test czyszczenia danych w trybie ręcznym bez nazwy."""
        form = TouristObjectAdminForm(data={
            "name": "",
            "geom": Point(0, 0, srid=4326),
        })
        
        is_valid = form.is_valid()
        
        assert is_valid is False
        assert "name" in form.errors
        assert "Gdy wpisujesz obiekt ręcznie (bez OSM ID), nazwa jest wymagana." in form.errors["name"]

    def test_clean_manual_mode_without_geom(self):
        """Test czyszczenia danych w trybie ręcznym bez geometrii."""
        form = TouristObjectAdminForm(data={
            "name": "Test Object",
            "geom": "",
        })
        
        is_valid = form.is_valid()
        
        assert is_valid is False
        assert "geom" in form.errors
        assert "Gdy wpisujesz obiekt ręcznie (bez OSM ID), musisz postawić punkt na mapie." in form.errors["geom"]

    def test_clean_manual_mode_with_all_required_fields(self):
        """Test czyszczenia danych w trybie ręcznym z wszystkimi wymaganymi polami."""
        form = TouristObjectAdminForm(data={
            "name": "Test Object",
            "geom": Point(0, 0, srid=4326),
            "type": "Szczyt",
        })
        
        is_valid = form.is_valid()
        
        assert is_valid is True
        assert form.cleaned_data["name"] == "Test Object"

    @patch('apps.badges.forms.messages')
    def test_clean_manual_mode_without_code_shows_message(self, mock_messages):
        """Test czyszczenia danych w trybie ręcznym bez kodu pokazuje wiadomość."""
        request = RequestFactory().post('/')
        form = TouristObjectAdminForm(data={
            "name": "Test Object",
            "geom": Point(0, 0, srid=4326),
        })
        form.request = request
        
        form.is_valid()
        
        mock_messages.info.assert_called_once()

    @patch('apps.badges.forms.TouristObject.validate_unique')
    @patch('apps.badges.forms.TouristObject.objects.filter')
    @patch('apps.badges.forms.OverpassClient')
    @patch('apps.badges.forms.OsmDataExtractor')
    def test_clean_osm_mode_successful_extraction(
        self, mock_extractor, mock_client_class, mock_filter, mock_validate_unique
    ):
        """Test czyszczenia danych w trybie OSM z poprawnym ekstrakcją."""
        mock_filter.return_value.exists.return_value = False
        # Mock OverpassClient
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_osm_node = Mock()
        mock_osm_node.tags = {
            "name": "Test Peak",
            "ele": "1234",
            "wikipedia": "pl:Test Peak",
            "natural": "peak"
        }
        mock_osm_node.version = 1
        mock_osm_node.timestamp = "2023-01-01"
        mock_osm_node.latitude = 50.0
        mock_osm_node.longitude = 20.0
        mock_client.fetch_object.return_value = mock_osm_node
        
        # Mock OsmDataExtractor
        mock_extractor.extract_name.return_value = "Test Peak"
        mock_extractor.extract_altitude.return_value = 1234
        mock_extractor.extract_alt_name.return_value = ""
        mock_extractor.extract_wikipedia_link.return_value = "https://pl.wikipedia.org/wiki/Test_Peak"
        mock_extractor.determine_type.return_value = ("Szczyt", [])
        
        form = TouristObjectAdminForm(data={
            "osm_id": "node/123",
            "name": "",
            "altitude": "",
            "wikipedia_link": "",
        })
        
        is_valid = form.is_valid()
        
        assert is_valid is True
        assert form.cleaned_data["name"] == "Test Peak"
        assert form.cleaned_data["altitude"] == 1234
        assert form.cleaned_data["wikipedia_link"] == "https://pl.wikipedia.org/wiki/Test_Peak"
        assert form.cleaned_data["type"] == "Szczyt"
        assert form.cleaned_data["osm_raw_tags"] == mock_osm_node.tags
        assert form.cleaned_data["osm_version"] == 1
        assert form.cleaned_data["osm_timestamp"] == "2023-01-01"

    @patch('apps.badges.forms.OverpassClient')
    def test_clean_osm_mode_fetch_error(self, mock_client_class):
        """Test czyszczenia danych w trybie OSM z błędem pobierania."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.fetch_object.side_effect = OsmAdapterError("Network error")
        
        form = TouristObjectAdminForm(data={
            "osm_id": "node/123",
        })
        
        is_valid = form.is_valid()
        
        assert is_valid is False
        assert "osm_id" in form.errors
        assert "Nie można pobrać danych z OSM: Network error" in form.errors["osm_id"]

    @patch('apps.badges.forms.TouristObject.validate_unique')
    @patch('apps.badges.forms.TouristObject.objects.filter')
    @patch('apps.badges.forms.OverpassClient')
    @patch('apps.badges.forms.OsmDataExtractor')
    def test_clean_osm_mode_preserves_existing_data(
        self, mock_extractor, mock_client_class, mock_filter, mock_validate_unique
    ):
        """Test czyszczenia danych w trybie OSM zachowuje istniejące dane."""
        mock_filter.return_value.exists.return_value = False
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_osm_node = Mock()
        mock_osm_node.tags = {}
        mock_osm_node.timestamp = None
        mock_osm_node.version = None
        mock_osm_node.latitude = 50.0
        mock_osm_node.longitude = 20.0
        mock_client.fetch_object.return_value = mock_osm_node
        
        mock_extractor.extract_name.return_value = None
        mock_extractor.extract_altitude.return_value = None
        mock_extractor.extract_alt_name.return_value = None
        mock_extractor.extract_wikipedia_link.return_value = None
        mock_extractor.determine_type.return_value = (None, [])
        
        form = TouristObjectAdminForm(data={
            "osm_id": "node/123",
            "name": "Existing Name",
            "type": "Custom Type",
        })
        
        is_valid = form.is_valid()
        
        assert is_valid is True
        assert form.cleaned_data["name"] == "Existing Name"
        assert form.cleaned_data["type"] == "Custom Type"

    @patch('apps.badges.forms.TouristObject.validate_unique')
    @patch('apps.badges.forms.TouristObject.objects.filter')
    @patch('apps.badges.forms.OverpassClient')
    @patch('apps.badges.forms.OsmDataExtractor')
    def test_clean_osm_mode_fallback_type(self, mock_extractor, mock_client_class, mock_filter, mock_validate_unique):
        """Test czyszczenia danych w trybie OSM z typem domyślnym."""
        mock_filter.return_value.exists.return_value = False
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_osm_node = Mock()
        mock_osm_node.tags = {}
        mock_osm_node.timestamp = None
        mock_osm_node.version = None
        mock_osm_node.latitude = 50.0
        mock_osm_node.longitude = 20.0
        mock_client.fetch_object.return_value = mock_osm_node
        
        mock_extractor.extract_name.return_value = "OSM Object"
        mock_extractor.extract_altitude.return_value = None
        mock_extractor.extract_alt_name.return_value = None
        mock_extractor.extract_wikipedia_link.return_value = None
        mock_extractor.determine_type.return_value = (None, [])
        
        form = TouristObjectAdminForm(data={
            "osm_id": "node/123",
            "type": "",
        })
        
        is_valid = form.is_valid()
        
        assert is_valid is True
        assert form.cleaned_data["type"] == "Inny punkt"

    @patch('apps.badges.forms.TouristObject.validate_unique')
    @patch('apps.badges.forms.OverpassClient')
    @patch('apps.badges.forms.OsmDataExtractor')
    @patch('apps.badges.forms.messages')
    @patch('apps.badges.forms.TouristObject.objects.filter')
    def test_clean_with_nearby_objects_warning(
        self, mock_filter, mock_messages, mock_extractor, mock_client_class, mock_validate_unique
    ):
        """Test czyszczenia danych z ostrzeżeniem o pobliskich obiektach."""
        # Mock OSM
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_osm_node = Mock()
        mock_osm_node.tags = {}
        mock_osm_node.timestamp = None
        mock_osm_node.version = None
        mock_osm_node.latitude = 50.0
        mock_osm_node.longitude = 20.0
        mock_client.fetch_object.return_value = mock_osm_node
        
        mock_extractor.extract_name.return_value = "OSM Object"
        mock_extractor.extract_altitude.return_value = None
        mock_extractor.extract_alt_name.return_value = None
        mock_extractor.extract_wikipedia_link.return_value = None
        mock_extractor.determine_type.return_value = (None, [])
        
        # Mock nearby objects
        mock_nearby_obj = Mock()
        mock_nearby_obj.name = "Nearby Object"
        mock_queryset = Mock()
        mock_queryset.exists.return_value = True
        mock_queryset.__getitem__ = Mock(return_value=[mock_nearby_obj])
        mock_filter.return_value = mock_queryset
        
        request = RequestFactory().post('/')
        form = TouristObjectAdminForm(data={
            "osm_id": "node/123",
        })
        form.request = request
        
        is_valid = form.is_valid()
        
        assert is_valid is True
        mock_messages.warning.assert_called()

    @patch('apps.badges.forms.TouristObject.validate_unique')
    @patch('apps.badges.forms.TouristObject.objects.filter')
    @patch('apps.badges.forms.OverpassClient')
    @patch('apps.badges.forms.OsmDataExtractor')
    @patch('apps.badges.forms.messages')
    def test_clean_with_new_mappings_warning(
        self, mock_messages, mock_extractor, mock_client_class, mock_filter, mock_validate_unique
    ):
        """Test czyszczenia danych z ostrzeżeniem o nowych mapowaniach."""
        mock_filter.return_value.exists.return_value = False
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_osm_node = Mock()
        mock_osm_node.tags = {"new_tag": "new_value"}
        mock_osm_node.timestamp = None
        mock_osm_node.version = None
        mock_osm_node.latitude = 50.0
        mock_osm_node.longitude = 20.0
        mock_client.fetch_object.return_value = mock_osm_node
        
        mock_extractor.extract_name.return_value = "OSM Object"
        mock_extractor.extract_altitude.return_value = None
        mock_extractor.extract_alt_name.return_value = None
        mock_extractor.extract_wikipedia_link.return_value = None
        mock_extractor.determine_type.return_value = ("Szczyt", ["new_tag=new_value"])
        
        request = RequestFactory().post('/')
        form = TouristObjectAdminForm(data={
            "osm_id": "node/123",
        })
        form.request = request
        
        is_valid = form.is_valid()
        
        assert is_valid is True
        mock_messages.warning.assert_called_once()

    def test_clean_without_request_object(self):
        """Test czyszczenia danych bez obiektu request."""
        form = TouristObjectAdminForm(data={
            "name": "Test Object",
            "geom": Point(0, 0, srid=4326),
        })
        # Brak ustawienia form.request
        
        is_valid = form.is_valid()
        
        assert is_valid is True

    def test_clean_editing_existing_object(self):
        """Test czyszczenia danych podczas edycji istniejącego obiektu."""
        existing_obj = TouristObject(pk=1)
        form = TouristObjectAdminForm(data={
            "name": "Updated Object",
            "geom": Point(0, 0, srid=4326),
        }, instance=existing_obj)
        
        is_valid = form.is_valid()
        
        assert is_valid is True
        assert form.cleaned_data["name"] == "Updated Object"
