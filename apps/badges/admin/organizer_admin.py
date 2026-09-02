"""Panel administracyjny dla organizatorów odznak."""

from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.badges.models import OrganizerModel


@admin.register(OrganizerModel)
class OrganizerAdmin(ModelAdmin):
    """Panel administracyjny dla organizatorów odznak."""

    list_display = ("name", "is_booklet_required", "has_publication_consent", "club_rules_link")
    list_filter = (
        "is_booklet_required",
        "has_publication_consent",
    )
    search_fields = ("name",)
