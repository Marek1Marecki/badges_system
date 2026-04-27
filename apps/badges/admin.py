"""Konfiguracja panelu Django Admin dla systemu odznak."""

from django import forms
from django.contrib import (
    admin,
    messages,  # Dla lepszych komunikatów
)
from django.contrib.admin import (
    SimpleListFilter,
    helpers,  # Do przekazania kontekstu akcji
)
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from django.http import HttpResponseRedirect
from django.shortcuts import render
from leaflet.admin import LeafletGeoAdmin

from apps.badges.forms import TouristObjectAdminForm
from apps.badges.models import (
    BadgeModel,
    BadgeTierModel,
    BadgeVersionModel,
    CountryModel,
    MacroregionModel,
    MesoregionModel,
    ObjectRegionCache,
    OrganizerModel,
    OsmTypeMapping,
    ProvinceModel,
    SubprovinceModel,
    TouristObject,
    TouristRegionModel,
    VoivodeshipModel,
)
from apps.badges.tasks import build_tourist_region_geometry_task, calculate_object_regions_task


class AddToBadgeForm(forms.Form):
    """Prosty formularz do okienka pośredniego w Akcji Admina."""

    badge_version = forms.ModelChoiceField(
        queryset=BadgeVersionModel.objects.none(),  # Domyślnie puste przy ładowaniu pliku
        label="Wybierz Wersję Odznaki",
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Baza odpytywana JEDYNIE w momencie faktycznego otwarcia okienka przez Admina!
        self.fields["badge_version"].queryset = BadgeVersionModel.objects.select_related("badge").all()


class ReadOnlyMapAdmin(LeafletGeoAdmin):
    """Bazowa klasa admina pokazująca kształty GIS tylko do odczytu."""

    modifiable = False
    settings_overrides = {
        "DEFAULT_CENTER": (52.0, 19.0),
        "DEFAULT_ZOOM": 5,
    }


@admin.register(CountryModel)
class CountryAdmin(ReadOnlyMapAdmin):
    list_display = ("name", "code", "order")


@admin.register(VoivodeshipModel)
class VoivodeshipAdmin(ReadOnlyMapAdmin):
    list_display = ("name", "code", "country")
    list_filter = ("country",)


@admin.register(ProvinceModel)
class ProvinceAdmin(ReadOnlyMapAdmin):
    list_display = ("name", "code", "country")


@admin.register(SubprovinceModel)
class SubprovinceAdmin(ReadOnlyMapAdmin):
    list_display = ("name", "code", "province")


@admin.register(MacroregionModel)
class MacroregionAdmin(ReadOnlyMapAdmin):
    list_display = ("name", "code", "subprovince")
    search_fields = ("name", "code")


@admin.register(MesoregionModel)
class MesoregionAdmin(ReadOnlyMapAdmin):
    list_display = ("name", "code", "macroregion")
    search_fields = ("name", "code")


class ObjectRegionCacheInline(admin.TabularInline):
    model = ObjectRegionCache
    extra = 0
    readonly_fields = ("region_level", "region_id", "region_name", "distance_meters")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class RegionLevelFilter(SimpleListFilter):
    """
    Pozwala filtrować listę obiektów turystycznych na podstawie naszej
    płaskiej, zdenormalizowanej tabeli CQRS (ObjectRegionCache).
    """

    # Nazwa wyświetlana w panelu po prawej stronie
    title = "Region (CQRS Cache)"

    # Parametr w URL (np. ?region_cache=Polska)
    parameter_name = "region_cache"

    def lookups(self, request, model_admin):
        """Zwraca listę opcji do wyboru w dropdownie filtra."""
        # Pobieramy wszystkie unikalne nazwy regionów, które zostały przypisane
        # do jakiegokolwiek obiektu przez Celery.
        # Używamy flat=True i distinct(), by lista była krótka i szybka.
        regions = ObjectRegionCache.objects.values_list("region_name", flat=True).distinct().order_by("region_name")

        # Zwracamy listę tupli (wartość_w_url, nazwa_wyświetlana)
        return [(region, region) for region in regions]

    def queryset(self, request, queryset):
        """Filtruje główny QuerySet obiektów na podstawie wyboru Admina."""
        if self.value():
            # Znajdujemy obiekty, które mają w swoim Cache'u wybrany region
            # (korzystając z relacji 'cached_regions' zdefiniowanej w modelu)
            return queryset.filter(cached_regions__region_name=self.value()).distinct()
        return queryset


class PendingMappingFilter(admin.SimpleListFilter):
    """Filtr pokazujący tylko te wpisy, które czekają na Twoją decyzję."""

    title = "Status mapowania"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return (
            ("pending", "Oczekujące na decyzję (Inbox)"),
            ("mapped", "Zmapowane (Gotowe)"),
            ("ignored", "Ignorowane"),
        )

    def queryset(self, request, queryset):
        if self.value() == "pending":
            return queryset.filter(target_type__isnull=True, is_ignored=False) | queryset.filter(
                target_type__exact="", is_ignored=False
            )
        if self.value() == "mapped":
            return queryset.exclude(target_type__isnull=True).exclude(target_type__exact="").filter(is_ignored=False)
        if self.value() == "ignored":
            return queryset.filter(is_ignored=True)
        return queryset


@admin.register(OsmTypeMapping)
class OsmTypeMappingAdmin(admin.ModelAdmin):
    list_display = ("osm_key", "osm_value", "target_type", "is_ignored")
    list_editable = ("target_type", "is_ignored")  # Pozwala wpisywać tekst bezpośrednio na liście!
    list_filter = (PendingMappingFilter, "osm_key")
    search_fields = ("osm_key", "osm_value", "target_type")


@admin.register(TouristObject)
class TouristObjectAdmin(LeafletGeoAdmin):
    """Główny panel tworzenia punktów (Słownik Obiektów)."""

    form = TouristObjectAdminForm
    list_display = ("name", "type", "altitude", "osm_id", "code", "is_active")
    list_filter = ("is_active", "type", RegionLevelFilter)
    search_fields = ("name", "alt_name", "osm_id", "code")
    actions = ["recalculate_regions_async", "add_to_badge_version", "show_ids_for_json"]
    modifiable = True
    settings_overrides = {
        "DEFAULT_CENTER": (52.0, 19.0),
        "DEFAULT_ZOOM": 5,
    }
    inlines = [ObjectRegionCacheInline]

    fieldsets = (
        (
            "Złoty Standard (Curated)",
            {
                "fields": (
                    "name",
                    "alt_name",
                    "type",
                    "altitude",
                    "wikipedia_link",
                    "geom",
                )
            },
        ),
        (
            "Stan fizyczny i cykl życia",
            {
                "fields": ("is_active", "existence_start", "existence_end"),
                "description": "Zarządzanie widocznością obiektu w czasie (przydatne m.in. dla wież i schronisk).",
                "classes": ("collapse",),
            },
        ),
        (
            "Ewidencja i Relacje",
            {
                "fields": ("code", "parent_object"),
            },
        ),
        (
            "Integracja z OSM (Data Lake)",
            {
                "fields": ("osm_id", "osm_version", "osm_timestamp", "osm_raw_tags"),
                "classes": ("collapse",),
            },
        ),
        (
            "Dane Wyliczane w Tle (CQRS)",
            {
                "fields": ("local_names",),
                "classes": ("collapse",),
            },
        ),
    )

    def get_form(self, request, obj=None, **kwargs):
        """Wstrzykujemy obiekt request do formularza, by móc wyświetlać Alerty."""
        form = super().get_form(request, obj, **kwargs)
        form.request = request  # <-- Przypinamy request!
        return form

    def save_model(self, request, obj, form, change):
        """Nadpisuje standardowy zapis, by wyzwolić przeliczanie geograficzne w tle."""
        super().save_model(request, obj, form, change)
        from django.db import transaction

        transaction.on_commit(lambda: calculate_object_regions_task.delay(obj.id))

    @admin.action(description="[Celery] Przelicz geografię (w tle) dla zaznaczonych")
    def recalculate_regions_async(self, request, queryset):
        """Wysyła zadania do kolejki Celery dla każdego zaznaczonego obiektu."""
        count = 0
        for obj in queryset:
            calculate_object_regions_task.delay(obj.id)
            count += 1
        self.message_user(request, f"Wysłano {count} obiektów do asynchronicznego przeliczenia w tle.")

    @admin.action(description="Przypnij zaznaczone obiekty do Wersji Odznaki...")
    def add_to_badge_version(self, request, queryset):
        """Akcja z okienkiem pośrednim do masowego przypisywania obiektów do odznaki."""

        # Jeśli formularz został zatwierdzony w okienku pośrednim
        if "apply" in request.POST:
            form = AddToBadgeForm(request.POST)
            if form.is_valid():
                badge_version = form.cleaned_data["badge_version"]
                badge_version.pool_peaks.add(*queryset)

                self.message_user(
                    request,
                    f"Pomyślnie przypisano {queryset.count()} obiektów do odznaki {badge_version}.",
                    level=messages.SUCCESS,
                )
                return HttpResponseRedirect(request.get_full_path())
        else:
            # Wyświetlamy pusty formularz (pierwsze wejście z listy akcji)
            form = AddToBadgeForm()

        # Przekazujemy wszystko do naszego własnego szablonu
        context = {
            **self.admin_site.each_context(request),
            "title": "Przypnij do odznaki",
            "objects": queryset,
            "form": form,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        }

        return render(request, "admin/badges/add_to_badge_action.html", context)

    @admin.action(description="Pokaż ID zaznaczonych obiektów (do skopiowania w reguły JSON)")
    def show_ids_for_json(self, request, queryset):
        """Generuje listę ID po przecinku, by Admin mógł je łatwo skopiować."""
        # Pobieramy IDki
        ids = list(queryset.values_list("id", flat=True))
        # Zamieniamy na string z przecinkami
        ids_str = ", ".join(str(i) for i in ids)

        # Wyświetlamy jako zielony komunikat (możesz to zaznaczyć myszką i skopiować)
        self.message_user(request, f"Skopiuj te ID do reguły JSON: {ids_str}")


@admin.register(OrganizerModel)
class OrganizerAdmin(admin.ModelAdmin):
    list_display = ("name", "is_booklet_required", "has_publication_consent", "club_rules_link")
    # Dodano filtr boczny (szybkie szukanie tych bez zgody)
    list_filter = (
        "is_booklet_required",
        "has_publication_consent",
    )
    search_fields = ("name",)


@admin.register(BadgeModel)
class BadgeAdmin(admin.ModelAdmin):
    """Panel zarządzania samymi odznakami (nazwy)."""

    list_display = ("name", "code", "organizer", "is_booklet_required")
    list_filter = ("is_booklet_required", "organizer")
    search_fields = ("name", "code")


class BadgeTierInlineFormSet(BaseInlineFormSet):
    """Walidator dla wierszy stopni odznaki (FormSet)."""

    def clean(self):
        super().clean()
        # Jeśli formularze mają już inne błędy, nie sprawdzamy dalej
        if any(self.errors):
            return

        orders = set()
        for form in self.forms:
            # Pomijamy puste wiersze oraz te zaznaczone do usunięcia
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue

            order_val = form.cleaned_data.get("order")
            if order_val is not None:
                if order_val in orders:
                    raise ValidationError(
                        "Błąd: Kolejność zdobywania stopni (pole 'order') musi być unikalna w ramach jednej odznaki!"
                    )
                orders.add(order_val)


class BadgeTierInline(admin.TabularInline):
    """Wbudowany formularz pozwalający zdefiniować stopnie prosto z widoku Wersji Odznaki."""

    model = BadgeTierModel
    formset = BadgeTierInlineFormSet
    extra = 1
    fields = ("name", "order", "required_peaks_count", "badge_image")


@admin.register(BadgeVersionModel)
class BadgeVersionAdmin(admin.ModelAdmin):
    """Panel Wersji Odznaki (Tu przypinamy szczyty i definiujemy stopnie)."""

    list_display = ("badge", "version_code", "valid_from")
    list_filter = ("badge", "valid_from")

    # Nasz potężny widget z powrotem we właściwym miejscu!
    filter_horizontal = ("pool_peaks",)

    # Wyświetlamy stopnie bezpośrednio pod formularzem wersji
    inlines = [BadgeTierInline]

    fieldsets = (
        ("Metadane", {"fields": ("badge", "version_code", "valid_from")}),
        ("Archiwum Regulaminu", {"fields": ("official_link", "rules_link", "rules_text", "booklet_template_image")}),
        ("Reguły Biznesowe (Czysta Domena)", {"fields": ("rules",)}),
        (
            "Pula Dopuszczalnych Obiektów",
            {
                "fields": ("pool_peaks",),
                "description": (
                    "Wybierz wszystkie obiekty, z których turysta może zbierać punkty w tej wersji regulaminu."
                ),
            },
        ),
    )


@admin.register(TouristRegionModel)
class TouristRegionAdmin(ReadOnlyMapAdmin):
    """Panel do budowy nadrzędnych Regionów Turystycznych (np. Sudety)."""

    list_display = ("name", "code")
    search_fields = ("name", "code")

    # 4 potężne okienka do wybierania elementów składowych
    filter_horizontal = ("provinces", "subprovinces", "macroregions", "mesoregions")

    actions = ["rebuild_geometry"]

    def save_related(self, request, form, formsets, change):
        """
        Nadpisujemy save_related, a nie save_model.
        Dlaczego? Bo w Django relacje M2M (nasze filter_horizontal) są zapisywane
        DOPIERO PO zapisaniu samego modelu. Musimy wywołać Celery po zapisie M2M!
        """
        super().save_related(request, form, formsets, change)
        from django.db import transaction

        transaction.on_commit(lambda: build_tourist_region_geometry_task.delay(form.instance.id))

    @admin.action(description="[Celery] Przebuduj geometrię i zaktualizuj szczyty (CQRS)")
    def rebuild_geometry(self, request, queryset):
        """Opcja ręcznego przeliczenia na żądanie."""
        for obj in queryset:
            build_tourist_region_geometry_task.delay(obj.id)
        self.message_user(request, "Wysłano zadania generowania do Celery.")
