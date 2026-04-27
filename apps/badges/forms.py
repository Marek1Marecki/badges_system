"""Niestandardowe formularze dla panelu administracyjnego."""

from django import forms
from django.contrib import messages
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.utils.html import format_html, format_html_join

from apps.badges.models import TouristObject
from infrastructure.adapters.osm_adapter import OsmAdapterError, OsmDataExtractor, OverpassClient


# 1. TWORZYMY WIDŻET DATALIST (Dropdown, w którym można pisać własny tekst)
class DatalistTextInput(forms.TextInput):
    def __init__(self, datalist, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.datalist = datalist

    def render(self, name, value, attrs=None, renderer=None):
        list_id = f"datalist_{name}"
        if attrs is None:
            attrs = {}
        attrs["list"] = list_id

        # Generujemy standardowe pole tekstowe
        html = super().render(name, value, attrs, renderer)

        # Generujemy listę podpowiedzi
        options = format_html_join("", '<option value="{}">', ((item,) for item in self.datalist))
        datalist_html = format_html('<datalist id="{}">{}</datalist>', list_id, options)

        # MAGIA: Zwracamy połączony HTML bezpiecznie
        return format_html("{}{}", html, datalist_html)


class TouristObjectAdminForm(forms.ModelForm):
    """
    Wymusza logiczną spójność danych podczas wprowadzania w panelu Admina.
    Zasada: Albo podajesz OSM_ID (wtedy resztę pobierzemy synchronicznie),
    albo podajesz Nazwę i Punkt na mapie (własny obiekt PTTK).
    """

    class Meta:
        model = TouristObject
        fields = "__all__"

    # 2. PODPINAMY WIDŻET DO POLA 'TYPE' PRZY ŁADOWANIU FORMULARZA
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Wyłączamy wymóg podawania typu w przeglądarce, bo uzupełnimy go z OSM
        self.fields["type"].required = False

        # Pobieramy unikalne typy, które już mamy w bazie (zasilone przez OSM)
        try:
            existing_types = list(TouristObject.objects.values_list("type", flat=True).distinct())
        except Exception:
            existing_types = []

        # Zawsze pokazujemy te podstawowe na liście, nawet w pustej bazie
        default_types = ["Szczyt", "Schronisko", "Jaskinia", "Zamek/Ruiny", "Przełęcz"]

        # Łączymy w jedną alfabetyczną listę unikalnych wartości
        all_types = sorted(set(existing_types + default_types))

        # Wstrzykujemy nasz nowy widżet do pola 'type'
        self.fields["type"].widget = DatalistTextInput(datalist=all_types)

    def clean(self):
        cleaned_data = super().clean()
        osm_id = cleaned_data.get("osm_id")
        code = cleaned_data.get("code")
        name = cleaned_data.get("name")
        geom = cleaned_data.get("geom")

        # TRYB 1: RĘCZNY (Brak OSM_ID)
        if not osm_id:
            # Wymagamy nazwy i geometrii TYLKO wtedy, gdy nie jest to import z OSM
            if not name:
                self.add_error("name", "Gdy wpisujesz obiekt ręcznie (bez OSM ID), nazwa jest wymagana.")
            if not geom:
                self.add_error("geom", "Gdy wpisujesz obiekt ręcznie (bez OSM ID), musisz postawić punkt na mapie.")

            # Ostrzeżenie (Info), jeśli ręczny obiekt nie ma kodu ewidencji
            if not code and hasattr(self, "request"):
                messages.info(
                    self.request,
                    "Wskazówka: Tworzysz obiekt ręczny (bez OSM ID). "
                    "Rozważ dodanie 'Unikalnego Kodu' dla lepszej ewidencji.",
                )

            # Wychodzimy, bo dla obiektu ręcznego nie odpalamy pobieracza OSM!
            return cleaned_data

        else:
            # TRYB 2: AUTOMATYCZNY Z OSM
            client = OverpassClient()
            try:
                # Pobieramy pełne dane z zewnętrznego API
                osm_node = client.fetch_object(osm_id)
            except OsmAdapterError as e:
                self.add_error("osm_id", f"Nie można pobrać danych z OSM: {str(e)}")
                return cleaned_data

            # 1. Zasilamy nasz Data Lake (JSONB)
            cleaned_data["osm_raw_tags"] = osm_node.tags

            # 2. Inteligentna Ekstrakcja do Twardych Kolumn
            extracted_name = OsmDataExtractor.extract_name(osm_node.tags)
            if not name and extracted_name:
                cleaned_data["name"] = extracted_name

            # WYSKOKOŚĆ
            extracted_altitude = OsmDataExtractor.extract_altitude(osm_node.tags)
            if not cleaned_data.get("altitude") and extracted_altitude is not None:
                cleaned_data["altitude"] = extracted_altitude

            # ALTERNATYWNA NAZWA
            extracted_alt_name = OsmDataExtractor.extract_alt_name(osm_node.tags, cleaned_data.get("name"))
            if not cleaned_data.get("alt_name") and extracted_alt_name:
                cleaned_data["alt_name"] = extracted_alt_name

            # NOWE: Zapisanie metadanych do przyszłej synchronizacji!
            if osm_node.version:
                cleaned_data["osm_version"] = osm_node.version
            if osm_node.timestamp:
                cleaned_data["osm_timestamp"] = osm_node.timestamp

            extracted_wiki = OsmDataExtractor.extract_wikipedia_link(osm_node.tags)
            if not cleaned_data.get("wikipedia_link") and extracted_wiki:
                cleaned_data["wikipedia_link"] = extracted_wiki

            # NOWE: Automatyczne zasysanie daty powstania (np. wieże widokowe)
            # Działa zasada "Data Override" - jeśli wpisałeś datę z palca, nie nadpiszemy jej.
            extracted_start = OsmDataExtractor.extract_start_date(osm_node.tags)
            if not cleaned_data.get("existence_start") and extracted_start:
                cleaned_data["existence_start"] = extracted_start.isoformat()

            if not geom:
                geom = Point(osm_node.longitude, osm_node.latitude, srid=4326)
                cleaned_data["geom"] = geom

            # Inteligentna ekstrakcja typu z wykorzystaniem Słownika Mapowań
            determined_type, new_mappings = OsmDataExtractor.determine_type(osm_node.tags)
            current_type_in_form = cleaned_data.get("type")

            # 1. Jeśli słownik znalazł zmapowany typ (np. "Szczyt"), używamy go.
            if determined_type:
                cleaned_data["type"] = determined_type

            # 2. Jeśli słownik NIE znalazł (zwrócił None), ALE pole w formularzu
            #    coś zawiera (np. wpisałeś ręcznie "Szczyt" albo było stare "PEAK"),
            #    zostawiamy to w spokoju! Nie niszczymy danych użytkownika.
            elif current_type_in_form:
                cleaned_data["type"] = current_type_in_form

            # 3. W ostateczności (nowy obiekt i puste pole)
            else:
                cleaned_data["type"] = "Inny punkt"

            # Wyświetlamy inteligentne powiadomienie dla Admina
            if new_mappings and hasattr(self, "request"):
                messages.warning(
                    self.request,
                    f"⚠️ Odkryto nowe tagi OSM: {', '.join(new_mappings)}. "
                    f"Dodano je do Słownika Mapowań. Uzupełnij 'Typ docelowy'!",
                )

        # 2. RADAR ANTYDUPLIKATOWY
        if geom and hasattr(self, "request"):
            nearby_objects = TouristObject.objects.filter(geom__distance_lte=(geom, D(m=150)))

            if self.instance and self.instance.pk:
                nearby_objects = nearby_objects.exclude(pk=self.instance.pk)

            if nearby_objects.exists():
                names = []
                for obj in nearby_objects[:3]:
                    obj_name = obj.name if obj.name else "Obiekt bez nazwy"
                    names.append(obj_name)

                msg = (
                    f"⚠️ RADAR: W promieniu 150m istnieją już obiekty: {', '.join(names)}."
                    f"Upewnij się, że nie tworzysz duplikatu!"
                )
                messages.warning(self.request, msg)

        return cleaned_data
