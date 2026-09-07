"""Panele administracyjne dla modelu regionu ADR-028 (RegionFlatModel)."""

from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.badges.models import RegionFlatModel


@admin.register(RegionFlatModel)
class RegionFlatAdmin(ModelAdmin):
    """Panel administracyjny dla płaskiego modelu regionów ADR-028."""

    list_display = ("name", "code", "level", "parent")
    list_filter = ("level",)
    search_fields = ("name", "code")
    autocomplete_fields = ["parent"]
    filter_horizontal = ["neighbors"]
