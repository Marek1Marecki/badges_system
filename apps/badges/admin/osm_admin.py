"""Panele administracyjne dla integracji OpenStreetMap."""

from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.html import format_html
from leaflet.admin import LeafletGeoAdminMixin
from unfold.admin import ModelAdmin

from apps.badges.admin.filters import PendingMappingFilter, RegionLevelFilter
from apps.badges.admin.forms import AddToBadgeForm
from apps.badges.admin.inlines import ObjectRegionCacheInline
from apps.badges.forms import TouristObjectAdminForm
from apps.badges.models import OsmTypeMapping, TouristObject
from apps.badges.tasks import (
    calculate_object_regions_task,
    fetch_osm_data_task,
    recalculate_object_regions_bulk_task,
    scan_proximity_candidates_task,
)


@admin.register(OsmTypeMapping)
class OsmTypeMappingAdmin(ModelAdmin):
    """Panel mapowania tagów OSM na typy obiektów."""

    list_display = ("osm_key", "osm_value", "target_type", "is_ignored")
    list_editable = ("target_type", "is_ignored")
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
                    "status",
                    "osm_error",
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
                "description": "Zarządzanie widocznością obiektu w czasie (przydatkie m.in. dla wież i schronisk).",
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
        """Wstrzykujemy obiekt request do formularza, by móc wyświetlać Alerty.

        Args:
          request:
          obj: (Default value = None)
          **kwargs:

        Returns:
        """
        form = super().get_form(request, obj, **kwargs)
        form.request = request  # <-- Przypinamy request!
        return form

    def get_list_filter(self, request):
        """Ustawia formularz i filtr, zachowując kompatybilność z oryginałem."""
        return self.list_filter

    def save_model(self, request, obj, form, change):
        """Nadpisuje standardowy zapis, by wyzwolić przeliczanie geograficzne w tle.

        Args:
          request:
          obj:
          form:
          change:

        Returns:
        """
        needs_osm_fetch = False

        if obj.osm_id and (not change or "osm_id" in form.changed_data):
            obj.status = "FETCHING_OSM"
            obj.osm_error = None
            needs_osm_fetch = True
        elif not obj.osm_id and obj.status == "DRAFT":
            obj.status = "READY"

        super().save_model(request, obj, form, change)

        from django.db import transaction

        if needs_osm_fetch:
            transaction.on_commit(lambda: fetch_osm_data_task.delay(obj.id))
        else:
            transaction.on_commit(lambda: calculate_object_regions_task.delay(obj.id))

    @admin.action(description="[Celery] Przelicz geografię (w tle) dla zaznaczonych")
    def recalculate_regions_async(self, request, queryset):
        """Wysyła batch task do Celery dla zaznaczonych obiektów (AUDYT-073 batching)."""
        object_ids = list(queryset.values_list("id", flat=True))
        recalculate_object_regions_bulk_task.delay(object_ids)
        self.message_user(
            request,
            f"Wysłano {len(object_ids)} obiektów do asynchronicznego przeliczenia w tle.",
        )

    @admin.action(description="Przypnij zaznaczone obiekty do Wersji Odznaki...")
    def add_to_badge_version(self, request, queryset):
        """Akcja z okienkiem pośrednim do masowego przypisywania obiektów do odznaki.

        Args:
          request:
          queryset:

        Returns:
        """
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
            form = AddToBadgeForm()

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
        """Generuje listę ID po przecinku, by Admin mógł je łatwo skopiować.

        Args:
          request:
          queryset:

        Returns:
        """
        ids = list(queryset.values_list("id", flat=True))
        ids_str = ", ".join(str(i) for i in ids)
        self.message_user(request, f"Skopiuj te ID do reguły JSON: {ids_str}")

    @admin.action(description="Oznacz wybrane obiekty jako GOTOWE (READY)")
    def mark_as_ready(self, request, queryset):
        """Szybka akcja do aktualizacji statusów historycznych rekordów.

        Args:
          request:
          queryset:

        Returns:
        """
        updated_count = queryset.update(status="READY")
        self.message_user(request, f"Zaktualizowano status {updated_count} obiektów na 'Gotowy (Przeliczony)'.")

    @admin.action(description="[OSM] Ponów pobieranie danych z OSM dla zaznaczonych")
    def retry_osm_fetch(self, request, queryset):
        """"""  # noqa: D401
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
        """Wrzuca zadanie skanowania całej bazy do Celery.

        Args:
          request:
          queryset:

        Returns:
        """
        scan_proximity_candidates_task.delay()
        self.message_user(
            request, "Wysłano zadanie Skanera do Celery. Za kilka sekund sprawdź zakładkę 'Radar Klastrowania'."
        )

    @admin.display(description="Wykorzystywany w odznakach")
    def get_related_badges(self, obj: TouristObject) -> str:
        """Wyświetla listę odznak, do których przypisany jest ten obiekt.

        Args:
          obj: TouristObject:

        Returns:
        """
        from django.utils.html import format_html_join

        if not obj.pk:
            return "Obiekt jeszcze nie zapisany."

        versions = obj.badgeversionmodel_set.select_related("badge").all()

        if not versions:
            return "Brak przypisań do jakiejkolwiek odznaki."

        items = ((f"{v.badge.name} ({v.version_code})",) for v in versions)
        list_html = format_html_join("\n", "<li>{}</li>", items)

        return format_html('<ul style="margin-left: 0; padding-left: 20px;">{}</ul>', list_html)  # type: ignore[no-any-return]
