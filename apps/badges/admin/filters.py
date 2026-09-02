"""Filtry listy (SimpleListFilter) używane w panelu Django Admin."""

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import F

from apps.badges.models import ObjectRegionCache


class RegionLevelFilter(SimpleListFilter):
    """Pozwala filtrować listę obiektów turystycznych na podstawie naszej płaskiej,
    zdenormalizowanej tabeli CQRS (ObjectRegionCache).

    Args:

    Returns:
    """

    title = "Region (CQRS Cache)"
    parameter_name = "region_cache"

    def lookups(self, request, model_admin):
        """Zwraca listę opcji do wyboru w dropdownie filtra.

        Args:
          request:
          model_admin:

        Returns:
        """
        regions = ObjectRegionCache.objects.values_list("region_name", flat=True).distinct().order_by("region_name")
        return [(region, region) for region in regions]

    def queryset(self, request, queryset):
        """Filtruje główny QuerySet obiektów na podstawie wyboru Admina.

        Args:
          request:
          queryset:

        Returns:
        """
        if self.value():
            return queryset.filter(cached_regions__region_name=self.value()).distinct()
        return queryset


class PendingMappingFilter(admin.SimpleListFilter):
    """Filtr pokazujący tylko te wpisy, które czekają na Twoją decyzję."""

    title = "Status mapowania"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        """"""  # noqa: D401
        return (
            ("pending", "Oczekujące na decyzję (Inbox)"),
            ("mapped", "Zmapowane (Gotowe)"),
            ("ignored", "Ignorowane"),
        )

    def queryset(self, request, queryset):
        """"""  # noqa: D401
        if self.value() == "pending":
            return queryset.filter(target_type__isnull=True, is_ignored=False) | queryset.filter(
                target_type__exact="", is_ignored=False
            )
        if self.value() == "mapped":
            return queryset.exclude(target_type__isnull=True).exclude(target_type__exact="").filter(is_ignored=False)
        if self.value() == "ignored":
            return queryset.filter(is_ignored=True)
        return queryset


class PeakInBadgeFilter(SimpleListFilter):
    """Niestandardowy filtr pozwalający znaleźć wszystkie odznaki zawierające dany szczyt."""

    title = "Zawiera obiekt w puli"
    parameter_name = "has_peak"

    def lookups(self, request, model_admin):
        """"""  # noqa: D401
        from apps.badges.models import TouristObject

        used_peaks = (
            TouristObject.objects.filter(badgeversionmodel__isnull=False)
            .values_list("id", "name")
            .distinct()
            .order_by("name")
        )
        return [(pk, name) for pk, name in used_peaks]

    def queryset(self, request, queryset):
        """"""  # noqa: D401
        if self.value():
            return queryset.filter(pool_peaks__id=self.value())
        return queryset


class ResolutionDirectionFilter(SimpleListFilter):
    """Niestandardowy filtr w bocznym menu do wyłapywania kierunku klastrowania."""

    title = "Kierunek połączenia (Dla Rozwiązanych)"
    parameter_name = "direction"

    def lookups(self, request, model_admin):
        """"""  # noqa: D401
        return (
            ("A_PARENT", "A jest Rodzicem (A ➔ B)"),
            ("B_PARENT", "B jest Rodzicem (A ⬅ B)"),
        )

    def queryset(self, request, queryset):
        """"""  # noqa: D401
        if self.value() == "A_PARENT":
            return queryset.filter(obj_b__parent_object=F("obj_a"))
        if self.value() == "B_PARENT":
            return queryset.filter(obj_a__parent_object=F("obj_b"))
        return queryset


__all__ = [
    "PeakInBadgeFilter",
    "PendingMappingFilter",
    "RegionLevelFilter",
    "ResolutionDirectionFilter",
]
