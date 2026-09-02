"""Panele administracyjne dla hierarchii odznak (Badge -> Version -> Tier)."""

from django.contrib import admin
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

    list_display = ("badge", "version_code", "valid_from")
    list_filter = ("badge", "valid_from", PeakInBadgeFilter)

    search_fields = ("version_code", "badge__name", "pool_peaks__name")

    filter_horizontal = ("pool_peaks",)

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
