"""Panel administracyjny dla konfliktów synchronizacji danych OSM."""

from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.badges.models import OsmSyncConflict, SyncConflictStatus


@admin.register(OsmSyncConflict)
class OsmSyncConflictAdmin(ModelAdmin):
    """Panel konfliktów synchronizacji danych OSM."""

    list_display = ("tourist_object", "field_name", "old_value", "new_value", "status", "created_at")
    list_filter = ("status", "field_name")
    search_fields = ("tourist_object__name", "tourist_object__osm_id")

    def has_add_permission(self, request) -> bool:
        """"""  # noqa: D401
        return False  # To roboty zgłaszają konflikty, nie ludzie!

    actions = ["accept_changes", "reject_changes"]

    @admin.action(description="AKCEPTUJ: Nadpisz nasze dane wartością z OSM")
    def accept_changes(self, request, queryset):
        """Nadpisuje dane w modelu TouristObject nową wartością.

        Args:
          request:
          queryset:

        Returns:
        """
        count = 0
        for conflict in queryset.filter(status=SyncConflictStatus.PENDING):
            obj = conflict.tourist_object
            field = conflict.field_name
            val = conflict.new_value

            if field == "altitude":
                setattr(obj, field, int(val) if val else None)
            elif field == "is_active":
                setattr(obj, field, val == "True")
            else:
                setattr(obj, field, val)

            obj.save(update_fields=[field])

            conflict.status = SyncConflictStatus.ACCEPTED
            conflict.save(update_fields=["status"])
            count += 1

        self.message_user(request, f"Zaakceptowano {count} zmian i zaktualizowano obiekty główne.")

    @admin.action(description="ODRZUĆ: Ignoruj zmiany z OSM (Zostaw nasze dane)")
    def reject_changes(self, request, queryset):
        """Odrzuca propozycję, pozostawiając stary stan bazy.

        Args:
          request:
          queryset:

        Returns:
        """
        count = queryset.filter(status=SyncConflictStatus.PENDING).update(status=SyncConflictStatus.REJECTED)
        self.message_user(request, f"Odrzucono {count} propozycji. Nasze dane pozostały nienaruszone.")
