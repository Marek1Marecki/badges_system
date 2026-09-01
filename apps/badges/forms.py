"""Niestandardowe formularze dla panelu administracyjnego."""

import logging

from django import forms
from django.contrib import messages
from django.core.cache import cache
from django.utils.html import format_html, format_html_join
from unfold.widgets import UnfoldAdminTextInputWidget

from apps.badges.models import TouristObject

logger = logging.getLogger(__name__)


# 1. TWORZYMY WIDŻET DATALIST (Dropdown, w którym można pisać własny tekst)
class DatalistTextInput(UnfoldAdminTextInputWidget):
    """Widżet pola tekstowego z listą podpowiedzi."""

    def __init__(self, datalist, *args, **kwargs):
        """Inicjalizuje widżet z listą podpowiedzi."""
        super().__init__(*args, **kwargs)
        self.datalist = datalist

    def render(self, name, value, attrs=None, renderer=None):
        """

        Args:
          name:
          value:
          attrs: (Default value = None)
          renderer: (Default value = None)

        Returns:

        """
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
    """Wymusza logiczną spójność danych podczas wprowadzania w panelu Admina.
    Zasada: Albo podajesz OSM_ID (wtedy resztę pobierzemy synchronicznie),
    albo podajesz Nazwę i Punkt na mapie (własny obiekt PTTK).

    Args:

    Returns:

    """

    class Meta:
        """Metakonfiguracja ModelForm dla TouristObject."""

        model = TouristObject
        fields = "__all__"

    # 2. PODPINAMY WIDŻET DO POLA 'TYPE' PRZY ŁADOWANIU FORMULARZA
    def __init__(self, *args, **kwargs):
        """Dostosowuje pole typu jako nieobowiązkowe."""
        super().__init__(*args, **kwargs)

        # Wyłączamy wymóg podawania typu w przeglądarce, bo uzupełnimy go z OSM
        self.fields["type"].required = False

        # SECURITY (AUDYT-071): Caching unikalnych typów z TTL, żeby uniknąć
        # N+1 w adminie — .distinct() na każdym wierszu w liście.
        cache_key = "tourist_object_types"
        try:
            existing_types = cache.get(cache_key)
        except Exception:
            existing_types = None
        if existing_types is None:
            try:
                existing_types = list(TouristObject.objects.values_list("type", flat=True).distinct())
            except Exception:
                existing_types = []
            try:
                cache.set(cache_key, existing_types, timeout=300)
            except Exception:
                logger.warning("Cache write failed for tourist_object_types; continuing without cache")

        # Zawsze pokazujemy te podstawowe na liście, nawet w pustej bazie
        default_types = ["Szczyt", "Schronisko", "Jaskinia", "Zamek/Ruiny", "Przełęcz"]

        # Łączymy w jedną alfabetyczną listę unikalnych wartości
        all_types = sorted(set(existing_types + default_types))

        # Wstrzykujemy nasz nowy widżet do pola 'type'
        self.fields["type"].widget = DatalistTextInput(datalist=all_types)

    def clean(self):
        """Wymusza spójność danych: albo OSM_ID, albo nazwa + geometria."""
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
