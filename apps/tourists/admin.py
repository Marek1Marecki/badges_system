"""Konfiguracja panelu administracyjnego dla obszaru Turysty (B2C).

Zgodnie z zasadami z AGENT_SPEC.md: Wszystkie klasy muszą dziedziczyć po ModelAdmin z pakietu 'unfold', aby utrzymać
spójny motyw wizualny Tailwind CSS.
"""

from django.contrib import admin
from django.contrib.sites.models import Site
from unfold.admin import ModelAdmin

from apps.tourists.models import AscentLog, TouristProfile, UserBadgeProgress


@admin.register(TouristProfile)
class TouristProfileAdmin(ModelAdmin):
    """Panel główny dla profilu turysty i jego limitów (Freemium Quotas)."""

    list_display = ("nickname", "user", "active_plan", "max_photos_per_ascent", "max_active_badges")
    list_filter = ("active_plan",)
    search_fields = ("nickname", "user__email")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "Tożsamość Turysty",
            {
                "fields": ("user", "nickname", "birth_date"),
                "description": (
                    "Dane logowania pochodzą z autoryzacji Django (User). "
                    "Pamiętaj o ochronie wizerunku (Privacy by Default)."
                ),
            },
        ),
        (
            "Limity Subskrypcyjne (Quotas)",
            {
                "fields": ("active_plan", "max_photos_per_ascent", "max_active_badges"),
                "description": "Limity ograniczające obciążenie infrastruktury i określające pakiet usług.",
            },
        ),
        (
            "Przynależność Klubowa",
            {
                "fields": ("club_join_dates",),
                "description": "Słownik JSON z kodami klubów PTTK i datami zapisu (wpływa na Reguły Daty Zapisu).",
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(AscentLog)
class AscentLogAdmin(ModelAdmin):
    """Niezależny panel śledzący wszystkie wejścia na szczyty."""

    # ZMIANA: 'user' -> 'profile'
    list_display = ("profile", "peak", "ascent_date", "has_souvenir", "created_at")
    list_filter = ("ascent_date",)
    search_fields = ("profile__nickname", "profile__user__email", "peak__name", "peak__osm_id")
    # ZMIANA: 'user' -> 'profile'
    readonly_fields = ("profile", "peak", "ascent_date", "souvenir_image", "created_at")

    @admin.display(description="Pamiątka", boolean=True)
    def has_souvenir(self, obj: AscentLog) -> bool:
        """Szybki znacznik czy turysta wgrał zdjęcie.

        Args:
          obj: AscentLog:
          obj: AscentLog:

        Returns:
        """
        return bool(obj.souvenir_image)


@admin.register(UserBadgeProgress)
class UserBadgeProgressAdmin(ModelAdmin):
    """Niezależny panel stanu zdobywania odznak i Osobistego Trackera (Kanban)."""

    # ZMIANA: 'user' -> 'profile'
    list_display = ("profile", "badge", "version_code", "cycle_number", "domain_status", "logistic_status")
    list_filter = ("domain_status", "logistic_status", "cycle_number", "badge")
    search_fields = ("profile__nickname", "profile__user__email", "badge__name")
    # ZMIANA: 'user' -> 'profile'
    readonly_fields = ("profile", "badge", "version", "cycle_number", "domain_status", "created_at", "updated_at")

    fieldsets = (
        (
            "Tożsamość Odznaki i Prawa Nabyte",
            {
                "fields": ("profile", "badge", "cycle_number", "version"),
                "description": (
                    "Wersja pozostaje PUSTA do czasu zakotwiczenia pierwszym logiem (Prawa Nabyte - US-C05)."
                ),
            },
        ),
        (
            "Sito Domenowe (Matematyka)",
            {
                "fields": ("domain_status",),
                "description": (
                    "Status jest wyliczany w locie (On-Demand) przez Czystą Domenę "
                    "i zapisywany tu jako Snapshot. Administrator nie może go edytować."
                ),
            },
        ),
        (
            "Osobisty Tracker Logistyki",
            {
                "fields": ("logistic_status", "logistic_status_date"),
                "description": (
                    "Zarządzane przez Turystę. Śledzi postęp pocztowy (Kanban). "
                    "Stan ten jest ignorowany przez Domenę (Invariant S-03)."
                ),
            },
        ),
    )

    @admin.display(description="Wersja (Regulamin)")
    def version_code(self, obj: UserBadgeProgress) -> str:
        """Ułatwia podgląd wersji w głównej liście.

        Args:
          obj: UserBadgeProgress:
          obj: UserBadgeProgress:

        Returns:
        """
        return obj.version.version_code if obj.version else "BRAK (Oczekuje)"


# --- UNFOLDYZACJA ZEWNĘTRZNYCH PACZEK (Zgodnie z EC-043) ---

# Unregister default Site model provided by Django
admin.site.unregister(Site)


# Re-register with Unfold's ModelAdmin
@admin.register(Site)
class SiteAdmin(ModelAdmin):
    """Panel administracyjny dla profili turystycznych."""

    list_display = ("domain", "name")
    search_fields = ("domain", "name")
