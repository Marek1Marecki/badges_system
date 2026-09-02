"""Inlines (TabularInline) używane w panelu Django Admin."""

from unfold.admin import TabularInline

from apps.badges.admin.forms import BadgeTierInlineFormSet
from apps.badges.models import BadgeTierModel, ObjectRegionCache


class ObjectRegionCacheInline(TabularInline):
    """Inline do przeglądania mapowania obiektu na regiony."""

    model = ObjectRegionCache
    extra = 0
    readonly_fields = ("region_level", "region_id", "region_name", "distance_meters")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        """"""  # noqa: D401
        return False


class BadgeTierInline(TabularInline):
    """Wbudowany formularz pozwalający zdefiniować stopnie prosto z widoku Wersji Odznaki."""

    model = BadgeTierModel
    formset = BadgeTierInlineFormSet
    extra = 1
    fields = ("name", "order", "required_peaks_count", "badge_image")
