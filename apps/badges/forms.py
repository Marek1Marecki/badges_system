"""Niestandardowe formularze dla panelu administracyjnego."""

from django import forms
from django.contrib import messages
from django.utils.html import format_html, format_html_join
from unfold.widgets import UnfoldAdminTextInputWidget

from apps.badges.models import TouristObject


# 1. TWORZYMY WIDŻET DATALIST (Dropdown, w którym można pisać własny tekst)
class DatalistTextInput(UnfoldAdminTextInputWidget):
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

        # TRYB 1: RĘCZNY (Brak OSM ID)
        if not osm_id:
            if not name:
                self.add_error("name", "Gdy wpisujesz obiekt ręcznie (bez OSM ID), nazwa jest wymagana.")
            if not geom:
                self.add_error("geom", "Gdy wpisujesz obiekt ręcznie (bez OSM ID), musisz postawić punkt na mapie.")

            if not code and hasattr(self, "request"):
                messages.info(
                    self.request,
                    "Wskazówka: Tworzysz obiekt ręczny. Rozważ dodanie 'Unikalnego Kodu PTTK' dla lepszej ewidencji.",
                )

        # W trybie OSM (gdy jest osm_id) nie sprawdzamy już nic,
        # bo asynchroniczny task w Celery pobierze resztę danych!
        return cleaned_data
