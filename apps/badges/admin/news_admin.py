"""Panel administracyjny dla wiadomości o odznakach (News Items)."""

from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from apps.badges.models import BadgeNewsItem


@admin.register(BadgeNewsItem)
class BadgeNewsItemAdmin(ModelAdmin):
    """Panel wiadomości związanych z odznakami."""

    list_display = ("badge_name", "change_type", "change_date_str", "is_read", "created_at", "source_link")
    list_filter = ("is_read", "change_type")
    search_fields = ("badge_name",)
    readonly_fields = ("badge_name", "change_type", "change_date_str", "source_url", "is_read", "created_at")

    actions = ["mark_as_read"]

    def has_add_permission(self, request) -> bool:
        """"""  # noqa: D401
        return False  # Ochrona: To robot zrzuca newsy, nie człowiek

    @admin.display(description="Źródło")
    def source_link(self, obj: BadgeNewsItem) -> str:
        """"""  # noqa: D401
        return format_html('<a href="{}" target="_blank">Otwórz stronę</a>', obj.source_url)  # type: ignore[no-any-return]

    @admin.action(description="Oznacz wybrane jako PRZECZYTANE (Archiwizuj)")
    def mark_as_read(self, request, queryset):
        """"""  # noqa: D401
        count = queryset.update(is_read=True)
        self.message_user(request, f"Zarchiwizowano {count} aktualności.")
