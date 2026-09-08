"""Panele administracyjne dla hierarchii odznak (Badge -> Version -> Tier)."""

from datetime import date

from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from apps.badges.admin.filters import PeakInBadgeFilter
from apps.badges.admin.inlines import BadgeTierInline
from apps.badges.models import BadgeModel, BadgeVersionModel, TouristObject


@admin.register(BadgeModel)
class BadgeAdmin(ModelAdmin):
    """Panel zarządzania samymi odznakami (nazwy)."""

    list_display = ("name", "code", "organizer", "is_booklet_required")
    list_filter = ("is_booklet_required", "organizer")
    search_fields = ("name", "code")


@admin.register(BadgeVersionModel)
class BadgeVersionAdmin(ModelAdmin):
    """Panel Wersji Odznaki (Tu przypinamy szczyty i definiujemy stopnie)."""

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Ochrona pola z regułami przed zniszczeniem przez Unfold.

        Args:
          db_field:
          request:
          **kwargs:

        Returns:
        """
        if db_field.name == "rules":
            return db_field.formfield(**kwargs)
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """KWARANTANNA: W puli odznak pokazujemy TYLKO obiekty gotowe.

        Args:
          db_field:
          request:
          **kwargs:

        Returns:
        """
        if db_field.name == "pool_peaks":
            kwargs["queryset"] = TouristObject.objects.filter(status="READY")
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    list_display = ("badge", "version_code", "valid_from", "valid_to", "temporal_status_label")
    list_filter = ("badge", "valid_from", PeakInBadgeFilter)

    search_fields = ("version_code", "badge__name", "pool_peaks__name")

    filter_horizontal = ("pool_peaks",)

    inlines = [BadgeTierInline]

    fieldsets = (
        ("Metadane", {"fields": ("badge", "version_code", "valid_from", "valid_to")}),
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

    @admin.display(description="Status Czasowy", ordering="valid_to")
    def temporal_status_label(self, obj: BadgeVersionModel) -> str:
        """Etykieta UX końcówki okresu obowiązywania (AKTYWNA / WYGASŁA / Zbliża się)."""
        today = date.today()
        if obj.valid_to is None:
            return str(format_html('<span style="color:green">🟢 AKTYWNA</span>'))
        if obj.valid_to < today:
            return str(format_html('<span style="color:red">🔴 WYGASŁA</span>'))
        if (obj.valid_to - today).days <= 30:
            return str(
                format_html('<span style="color:orange">🟠 ZAMYKA SIĘ ZA {} DNI</span>', (obj.valid_to - today).days)
            )
        return str(format_html("<span>🔵 AKTYWNA</span>"))
