"""Custom template filters for badge detail UI (AUDYT-099)."""

from django import template

register = template.Library()


@register.filter
def filter_by_lifecycle(ascents_with_status, lifecycle_value):
    """Filtruje listę AscentStatusResponseDTO po polu ``lifecycle``.

    Używany w szablonie ``badge_detail.html`` do izolacji wejść
    oznaczonych jako ``ORPHANED`` (AUDYT-099 Opcja C — Grandfather's Bin).
    """
    return [a for a in ascents_with_status if a.lifecycle == lifecycle_value]
