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
from django.db.models import F, Q
from django.forms.models import BaseInlineFormSet
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.html import format_html
from leaflet.admin import LeafletGeoAdminMixin
from unfold.admin import ModelAdmin, TabularInline

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
    OsmSyncConflict,
    OsmTypeMapping,
    ProvinceModel,
    ProximityCandidate,
    SubprovinceModel,
    SyncConflictStatus,
    TouristObject,
    TouristRegionModel,
    VoivodeshipModel,
)
from apps.badges.tasks import (
    build_tourist_region_geometry_task,
    calculate_object_regions_task,
    fetch_osm_data_task,
    scan_proximity_candidates_task,
)


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


class ReadOnlyMapAdmin(LeafletGeoAdminMixin, ModelAdmin):
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


class ObjectRegionCacheInline(TabularInline):
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
class OsmTypeMappingAdmin(ModelAdmin):
    list_display = ("osm_key", "osm_value", "target_type", "is_ignored")
    list_editable = ("target_type", "is_ignored")  # Pozwala wpisywać tekst bezpośrednio na liście!
    list_filter = (PendingMappingFilter, "osm_key")
    search_fields = ("osm_key", "osm_value", "target_type")


@admin.register(TouristObject)
class TouristObjectAdmin(LeafletGeoAdminMixin, ModelAdmin):
    """Główny panel tworzenia punktów (Słownik Obiektów)."""

    form = TouristObjectAdminForm
    list_display = ("name", "type", "altitude", "osm_id", "status", "code", "is_active", "last_sync_check")
    list_filter = ("status", "is_active", "type", RegionLevelFilter)
    search_fields = ("name", "alt_name", "osm_id", "code")
    actions = [
        "recalculate_regions_async",
        "add_to_badge_version",
        "show_ids_for_json",
        "mark_as_ready",
        "retry_osm_fetch",
        "run_proximity_scanner",
    ]
    modifiable = True
    settings_overrides = {
        "DEFAULT_CENTER": (52.0, 19.0),
        "DEFAULT_ZOOM": 5,
    }
    inlines = [ObjectRegionCacheInline]
    readonly_fields = ("status", "osm_error", "local_names", "last_sync_check", "get_related_badges")

    fieldsets = (
        (
            "Złoty Standard (Curated)",
            {
                "fields": (
                    "is_active",
                    "status",  # Dodajemy do widoku, ale będzie read-only dzięki liście wyżej
                    "osm_error",  # Dodajemy do widoku, ale będzie read-only
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
                "fields": ("existence_start", "existence_end"),
                "description": "Zarządzanie widocznością obiektu w czasie (przydatne m.in. dla wież i schronisk).",
                "classes": ("collapse",),
            },
        ),
        (
            "Ewidencja i Relacje",
            {
                "fields": ("code", "parent_object", "get_related_badges"),
            },
        ),
        (
            "Integracja z OSM (Data Lake)",
            {
                "fields": ("osm_id", "osm_version", "osm_timestamp", "osm_raw_tags", "last_sync_check"),
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

        needs_osm_fetch = False

        # Jeśli to nowy obiekt z OSM, lub zmieniono mu OSM ID -> ustaw na "Pobieranie"
        if obj.osm_id and (not change or "osm_id" in form.changed_data):
            obj.status = "FETCHING_OSM"
            obj.osm_error = None
            needs_osm_fetch = True
        elif not obj.osm_id and obj.status == "DRAFT":
            # Ręczny obiekt od razu jest "Gotowy"
            obj.status = "READY"

        super().save_model(request, obj, form, change)

        from django.db import transaction

        if needs_osm_fetch:
            transaction.on_commit(lambda: fetch_osm_data_task.delay(obj.id))
        else:
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

    # NOWA AKCJA: Wymuszenie statusu Gotowy
    @admin.action(description="Oznacz wybrane obiekty jako GOTOWE (READY)")
    def mark_as_ready(self, request, queryset):
        """Szybka akcja do aktualizacji statusów historycznych rekordów."""
        updated_count = queryset.update(status="READY")
        self.message_user(request, f"Zaktualizowano status {updated_count} obiektów na 'Gotowy (Przeliczony)'.")

    @admin.action(description="[OSM] Ponów pobieranie danych z OSM dla zaznaczonych")
    def retry_osm_fetch(self, request, queryset):
        count = 0
        for obj in queryset.filter(osm_id__isnull=False).exclude(osm_id=""):
            obj.status = "FETCHING_OSM"
            obj.osm_error = None
            obj.save(update_fields=["status", "osm_error"])
            fetch_osm_data_task.delay(obj.id)
            count += 1
        self.message_user(request, f"Ponowiono pobieranie OSM dla {count} obiektów.")

    @admin.action(description="[Celery] Uruchom Radar Zbliżeniowy 150m (Szukaj Klastrów)")
    def run_proximity_scanner(self, request, queryset):
        """Wrzuca zadanie skanowania całej bazy do Celery."""
        scan_proximity_candidates_task.delay()
        self.message_user(
            request, "Wysłano zadanie Skanera do Celery. Za kilka sekund sprawdź zakładkę 'Radar Klastrowania'."
        )

    @admin.display(description="Wykorzystywany w odznakach")
    def get_related_badges(self, obj: TouristObject) -> str:
        """Wyświetla listę odznak, do których przypisany jest ten obiekt."""
        from django.utils.html import format_html, format_html_join

        if not obj.pk:
            return "Obiekt jeszcze nie zapisany."

        # Odpytujemy odwrotną relację ManyToMany.
        # Używamy select_related, by pobrać nazwy odznak jednym zapytaniem SQL.
        versions = obj.badgeversionmodel_set.select_related("badge").all()

        if not versions:
            return "Brak przypisań do jakiejkolwiek odznaki."

        # Generujemy elegancką listę w HTML
        items = ((f"{v.badge.name} ({v.version_code})",) for v in versions)
        list_html = format_html_join("\n", "<li>{}</li>", items)

        # Tłumimy błąd mypy (no-any-return) dla format_html
        return format_html('<ul style="margin-left: 0; padding-left: 20px;">{}</ul>', list_html)  # type: ignore[no-any-return]


@admin.register(OrganizerModel)
class OrganizerAdmin(ModelAdmin):
    list_display = ("name", "is_booklet_required", "has_publication_consent", "club_rules_link")
    # Dodano filtr boczny (szybkie szukanie tych bez zgody)
    list_filter = (
        "is_booklet_required",
        "has_publication_consent",
    )
    search_fields = ("name",)


@admin.register(BadgeModel)
class BadgeAdmin(ModelAdmin):
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


class BadgeTierInline(TabularInline):
    """Wbudowany formularz pozwalający zdefiniować stopnie prosto z widoku Wersji Odznaki."""

    model = BadgeTierModel
    formset = BadgeTierInlineFormSet
    extra = 1
    fields = ("name", "order", "required_peaks_count", "badge_image")


@admin.register(BadgeVersionModel)
class BadgeVersionAdmin(ModelAdmin):
    """Panel Wersji Odznaki (Tu przypinamy szczyty i definiujemy stopnie)."""

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Ochrona pola z regułami przed zniszczeniem przez Unfold."""
        if db_field.name == "rules":
            # Wywołujemy natywną metodę pola, CAŁKOWICIE POMIJAJĄC mechanizmy Unfolda.
            # Dzięki temu django-jsonform odzyskuje kontrolę i renderuje swój kreator reguł.
            return db_field.formfield(**kwargs)

        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """KWARANTANNA: W puli odznak pokazujemy TYLKO obiekty gotowe, by Admin nie zepsuł reguł."""
        if db_field.name == "pool_peaks":
            kwargs["queryset"] = TouristObject.objects.filter(status="READY")
        return super().formfield_for_manytomany(db_field, request, **kwargs)

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


class ResolutionDirectionFilter(SimpleListFilter):
    """Niestandardowy filtr w bocznym menu do wyłapywania kierunku klastrowania."""

    title = "Kierunek połączenia (Dla Rozwiązanych)"
    parameter_name = "direction"

    def lookups(self, request, model_admin):
        return (
            ("A_PARENT", "A jest Rodzicem (A ➔ B)"),
            ("B_PARENT", "B jest Rodzicem (A ⬅ B)"),
        )

    def queryset(self, request, queryset):
        # Używamy funkcji F() aby baza sama porównała dwie kolumny w locie!
        if self.value() == "A_PARENT":
            return queryset.filter(obj_b__parent_object=F("obj_a"))
        if self.value() == "B_PARENT":
            return queryset.filter(obj_a__parent_object=F("obj_b"))
        return queryset


@admin.register(ProximityCandidate)
class ProximityCandidateAdmin(ModelAdmin):
    # ZMIANA 1: Zamiast "status", używamy nowej metody "get_detailed_status"
    list_display = ("get_obj_a_info", "get_obj_b_info", "distance_meters", "get_detailed_status", "created_at")

    # ZMIANA 2: Dodajemy nasz nowy filtr obok standardowego
    list_filter = ("status", ResolutionDirectionFilter)
    search_fields = ("obj_a__name", "obj_b__name")

    # ZMIANA 3: Optymalizacja N+1 zapytań (Dobra praktyka dla wydajności panelu)
    def get_queryset(self, request):
        """Pobieramy obiekty powiązane z góry, by nie obciążać bazy w każdej linijce."""
        qs = super().get_queryset(request)
        return qs.select_related("obj_a", "obj_b")

    # ZMIANA 4: Nowa metoda wyświetlająca status
    @admin.display(description="Status / Relacja")
    def get_detailed_status(self, obj: ProximityCandidate) -> str:
        """Dynamicznie określa relację na podstawie faktycznego stanu w bazie."""
        # Jeśli para jest oznaczona jako rozwiązana, sprawdzamy kto ostatecznie jest rodzicem
        if obj.status == "RESOLVED":
            # Ponieważ zastosowaliśmy select_related wyżej, odwołanie do ID nie obciąża bazy!
            if obj.obj_b.parent_object_id == obj.obj_a_id:
                return "✔ Połączone (A jest Rodzicem)"
            elif obj.obj_a.parent_object_id == obj.obj_b_id:
                return "✔ Połączone (B jest Rodzicem)"
            return "✔ Rozwiązane (Zmieniono ręcznie poza radarem)"

        # Dla PENDING i IGNORED zwracamy standardową, czytelną etykietę z modelu
        return str(obj.get_status_display())

    @admin.display(description="Obiekt A (Lewy)")
    def get_obj_a_info(self, obj: ProximityCandidate) -> str:
        """Generuje czytelny opis Obiektu A wraz z linkiem do edycji."""
        url = f"/admin/badges/touristobject/{obj.obj_a.id}/change/"
        type_str = obj.obj_a.type
        # Tłumimy błąd mypy: format_html zwraca SafeString/Any, co jest tutaj pożądane
        return format_html('<a href="{}">{} [{}]</a>', url, obj.obj_a.name, type_str)  # type: ignore[no-any-return]

    @admin.display(description="Obiekt B (Prawy)")
    def get_obj_b_info(self, obj: ProximityCandidate) -> str:
        """Generuje czytelny opis Obiektu B wraz z linkiem do edycji."""
        url = f"/admin/badges/touristobject/{obj.obj_b.id}/change/"
        type_str = obj.obj_b.type
        return format_html('<a href="{}">{} [{}]</a>', url, obj.obj_b.name, type_str)  # type: ignore[no-any-return]

    def has_add_permission(self, request) -> bool:
        return False

    actions = ["make_a_parent", "make_b_parent", "ignore_pair"]

    @admin.action(description="POŁĄCZ: Lewy obiekt (A) jest Rodzicem Prawego (B)")
    def make_a_parent(self, request, queryset):
        self._resolve_pairs(queryset, parent_is="A")

    @admin.action(description="POŁĄCZ: Prawy obiekt (B) jest Rodzicem Lewego (A)")
    def make_b_parent(self, request, queryset):
        self._resolve_pairs(queryset, parent_is="B")

    @admin.action(description="IGNORUJ: Obiekty nie są powiązane (np. dwa osobne szczyty)")
    def ignore_pair(self, request, queryset):
        queryset.update(status="IGNORED")

    def _resolve_pairs(self, queryset, parent_is: str):
        """Mechanika łączenia w Klastry i inteligentnego ignorowania rodzeństwa."""
        for candidate in queryset.filter(status="PENDING"):
            if parent_is == "A":
                parent = candidate.obj_a
                child = candidate.obj_b
            else:
                parent = candidate.obj_b
                child = candidate.obj_a

            # 1. Zapisujemy relację
            child.parent_object = parent
            child.save(update_fields=["parent_object"])

            # 2. Oznaczamy tę parę jako rozwiązaną
            candidate.status = "RESOLVED"
            candidate.save(update_fields=["status"])

            # 3. AUTO-RESOLVE RODZEŃSTWA (Zgodnie z naszymi ustaleniami!)
            # Jeśli dziecko ma już w Radarze inne pary ze statusem PENDING
            # z obiektami, które też są dziećmi tego samego rodzica -> Zignoruj je!
            siblings_ids = parent.child_objects.values_list("id", flat=True)

            ProximityCandidate.objects.filter(status="PENDING").filter(
                Q(obj_a=child, obj_b_id__in=siblings_ids) | Q(obj_b=child, obj_a_id__in=siblings_ids)
            ).update(status="IGNORED")


@admin.register(OsmSyncConflict)
class OsmSyncConflictAdmin(ModelAdmin):
    list_display = ("tourist_object", "field_name", "old_value", "new_value", "status", "created_at")
    list_filter = ("status", "field_name")
    search_fields = ("tourist_object__name", "tourist_object__osm_id")

    def has_add_permission(self, request) -> bool:
        return False  # To roboty zgłaszają konflikty, nie ludzie!

    actions = ["accept_changes", "reject_changes"]

    @admin.action(description="AKCEPTUJ: Nadpisz nasze dane wartością z OSM")
    def accept_changes(self, request, queryset):
        """Nadpisuje dane w modelu TouristObject nową wartością."""
        count = 0
        for conflict in queryset.filter(status=SyncConflictStatus.PENDING):
            obj = conflict.tourist_object
            field = conflict.field_name
            val = conflict.new_value

            # Bezpieczne rzutowanie typów przed zapisem do bazy
            if field == "altitude":
                setattr(obj, field, int(val) if val else None)
            elif field == "is_active":
                # Gdy wykryjemy "Ducha" (usunięte z OSM)
                setattr(obj, field, val == "True")
            else:
                setattr(obj, field, val)

            # Zapisujemy tylko zmienione pole w obiekcie głównym
            obj.save(update_fields=[field])

            # Oznaczamy konflikt jako załatwiony
            conflict.status = SyncConflictStatus.ACCEPTED
            conflict.save(update_fields=["status"])
            count += 1

        self.message_user(request, f"Zaakceptowano {count} zmian i zaktualizowano obiekty główne.")

    @admin.action(description="ODRZUĆ: Ignoruj zmiany z OSM (Zostaw nasze dane)")
    def reject_changes(self, request, queryset):
        """Odrzuca propozycję, pozostawiając stary stan bazy."""
        count = queryset.filter(status=SyncConflictStatus.PENDING).update(status=SyncConflictStatus.REJECTED)
        self.message_user(request, f"Odrzucono {count} propozycji. Nasze dane pozostały nienaruszone.")
