"""Testy dla formularzy Django."""

from unittest.mock import patch

from django.contrib.gis.geos import Point
from django.test import RequestFactory

from apps.badges.forms import DatalistTextInput, TouristObjectAdminForm
from apps.badges.models import TouristObject


class TestDatalistTextInput:
    """Testy widżetu DatalistTextInput."""

    def test_init_with_datalist(self):
        datalist = ["Szczyt", "Schronisko", "Jaskinia"]
        widget = DatalistTextInput(datalist)
        assert widget.datalist == datalist

    def test_render_generates_correct_html(self):
        datalist = ["Szczyt", "Schronisko"]
        widget = DatalistTextInput(datalist)
        html = widget.render("field_name", "test_value")
        assert 'name="field_name"' in html
        assert 'value="test_value"' in html
        assert 'list="datalist_field_name"' in html
        assert '<datalist id="datalist_field_name">' in html
        assert '<option value="Szczyt">' in html
        assert '<option value="Schronisko">' in html

    def test_render_with_none_attrs(self):
        datalist = ["Test"]
        widget = DatalistTextInput(datalist)
        html = widget.render("field", None, attrs=None)
        assert 'list="datalist_field"' in html
        assert '<option value="Test">' in html

    def test_render_with_existing_attrs(self):
        datalist = ["Test"]
        widget = DatalistTextInput(datalist)
        html = widget.render("field", "value", attrs={"class": "form-control"})
        assert 'class="form-control"' in html
        assert 'list="datalist_field"' in html


class TestTouristObjectAdminForm:
    """Testy formularza TouristObjectAdminForm."""

    def test_form_meta_configuration(self):
        form = TouristObjectAdminForm()
        assert form._meta.model == TouristObject
        assert "name" in form.fields
        assert "geom" in form.fields
        assert "osm_id" in form.fields

    def test_init_sets_type_field_not_required(self):
        form = TouristObjectAdminForm()
        assert form.fields["type"].required is False

    @patch("apps.badges.forms.TouristObject.objects.values_list")
    def test_init_with_database_types(self, mock_values_list):
        mock_values_list.return_value.distinct.return_value = ["Szczyt", "Schronisko"]
        form = TouristObjectAdminForm()
        widget = form.fields["type"].widget
        assert isinstance(widget, DatalistTextInput)
        assert "Szczyt" in widget.datalist
        assert "Schronisko" in widget.datalist
        assert "Jaskinia" in widget.datalist

    @patch("apps.badges.forms.TouristObject.objects.values_list")
    def test_init_handles_database_exception(self, mock_values_list):
        mock_values_list.side_effect = Exception("Database error")
        form = TouristObjectAdminForm()
        widget = form.fields["type"].widget
        assert isinstance(widget, DatalistTextInput)
        assert "Szczyt" in widget.datalist
        assert "Schronisko" in widget.datalist

    def test_clean_manual_mode_without_name(self):
        form = TouristObjectAdminForm(data={"name": "", "geom": Point(0, 0, srid=4326).wkt})
        with patch.object(form, "validate_unique"):
            is_valid = form.is_valid()
        assert is_valid is False
        assert "name" in form.errors
        assert "Gdy wpisujesz obiekt ręcznie (bez OSM ID), nazwa jest wymagana." in form.errors["name"]

    def test_clean_manual_mode_without_geom(self):
        form = TouristObjectAdminForm(data={"name": "Test Object", "geom": "", "status": "DRAFT"})
        with patch.object(form, "validate_unique"):
            is_valid = form.is_valid()
        assert is_valid is False
        assert "geom" in form.errors
        assert "Gdy wpisujesz obiekt ręcznie (bez OSM ID), musisz postawić punkt na mapie." in form.errors["geom"]

    @patch("apps.badges.forms.TouristObject.objects.values_list")
    def test_clean_manual_mode_with_all_required_fields(self, mock_values_list):
        mock_values_list.return_value.distinct.return_value = []
        form = TouristObjectAdminForm(
            data={
                "name": "Test Object",
                "type": "Szczyt",
                "status": "DRAFT",
                "geom": Point(19.0, 50.0, srid=4326).wkt,
            }
        )
        with patch.object(form, "validate_unique"):
            is_valid = form.is_valid()
        assert is_valid is True
        assert form.cleaned_data["name"] == "Test Object"

    @patch("apps.badges.forms.messages")
    def test_clean_manual_mode_without_code_shows_message(self, mock_messages):
        request = RequestFactory().post("/")
        form = TouristObjectAdminForm(data={"name": "Test Object", "geom": Point(0, 0, srid=4326).wkt})
        form.request = request
        with patch.object(form, "validate_unique"):
            form.is_valid()
        mock_messages.info.assert_called_once()

    @patch("apps.badges.forms.TouristObject.objects.values_list")
    def test_clean_osm_mode_skips_validation(self, mock_values_list):
        mock_values_list.return_value.distinct.return_value = []
        form = TouristObjectAdminForm(data={"osm_id": "node/123", "name": "", "geom": "", "status": "DRAFT"})
        with patch.object(form, "validate_unique"):
            is_valid = form.is_valid()
        assert is_valid is True

    @patch("apps.badges.forms.TouristObject.objects.values_list")
    def test_clean_without_request_object(self, mock_values_list):
        mock_values_list.return_value.distinct.return_value = []
        form = TouristObjectAdminForm(
            data={
                "name": "Test Object",
                "status": "DRAFT",
                "geom": Point(19.0, 50.0, srid=4326).wkt,
            }
        )
        with patch.object(form, "validate_unique"):
            is_valid = form.is_valid()
        assert is_valid is True

    @patch("apps.badges.forms.TouristObject.objects.values_list")
    def test_clean_editing_existing_object(self, mock_values_list):
        mock_values_list.return_value.distinct.return_value = []
        existing_obj = TouristObject(pk=1)
        form = TouristObjectAdminForm(
            data={
                "name": "Updated Object",
                "geom": Point(0, 0, srid=4326).wkt,
                "status": "DRAFT",
            },
            instance=existing_obj,
        )
        form.fields["name"].required = True
        form.fields["geom"].required = True
        with patch.object(form, "validate_unique"):
            is_valid = form.is_valid()
        assert is_valid is True
        assert form.cleaned_data["name"] == "Updated Object"
