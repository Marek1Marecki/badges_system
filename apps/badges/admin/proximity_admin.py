"""Panel administracyjny dla kandydatów na bliskie obiekty turystyczne."""

from django.contrib import admin
from django.db.models import Q
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from apps.badges.admin.filters import ResolutionDirectionFilter
from apps.badges.models import ProximityCandidate


@admin.register(ProximityCandidate)
class ProximityCandidateAdmin(ModelAdmin):
    """Panel kandydatów na bliskie obiekty turystyczne."""

    list_display = ("get_obj_a_info", "get_obj_b_info", "distance_meters", "get_detailed_status", "created_at")

    list_filter = ("status", ResolutionDirectionFilter)
    search_fields = ("obj_a__name", "obj_b__name")

    def get_queryset(self, request):
        """Pobieramy obiekty powiązane z góry, by nie obciążać bazy w każdej linijce.

        Args:
          request:

        Returns:
        """
        qs = super().get_queryset(request)
        return qs.select_related("obj_a", "obj_b")

    @admin.display(description="Status / Relacja")
    def get_detailed_status(self, obj: ProximityCandidate) -> str:
        """Dynamicznie określa relację na podstawie faktycznego stanu w bazie.

        Args:
          obj: ProximityCandidate:

        Returns:
        """
        if obj.status == "RESOLVED":
            if obj.obj_b.parent_object_id == obj.obj_a_id:
                return "✔ Połączone (A jest Rodzicem)"
            elif obj.obj_a.parent_object_id == obj.obj_b_id:
                return "✔ Połączone (B jest Rodzicem)"
            return "✔ Rozwiązane (Zmieniono ręcznie poza radarem)"

        return str(obj.get_status_display())

    @admin.display(description="Obiekt A (Lewy)")
    def get_obj_a_info(self, obj: ProximityCandidate) -> str:
        """Generuje czytelny opis Obiektu A wraz z linkiem do edycji.

        Args:
          obj: ProximityCandidate:

        Returns:
        """
        url = f"/admin/badges/touristobject/{obj.obj_a.id}/change/"
        type_str = obj.obj_a.type
        return format_html('<a href="{}">{} [{}]</a>', url, obj.obj_a.name, type_str)  # type: ignore[no-any-return]

    @admin.display(description="Obiekt B (Prawy)")
    def get_obj_b_info(self, obj: ProximityCandidate) -> str:
        """Generuje czytelny opis Obiektu B wraz z linkiem do edycji.

        Args:
          obj: ProximityCandidate:

        Returns:
        """
        url = f"/admin/badges/touristobject/{obj.obj_b.id}/change/"
        type_str = obj.obj_b.type
        return format_html('<a href="{}">{} [{}]</a>', url, obj.obj_b.name, type_str)  # type: ignore[no-any-return]

    def has_add_permission(self, request) -> bool:
        """"""  # noqa: D401
        return False

    actions = ["make_a_parent", "make_b_parent", "ignore_pair"]

    @admin.action(description="POŁĄCZ: Lewy obiekt (A) jest Rodzicem Prawego (B)")
    def make_a_parent(self, request, queryset):
        """"""  # noqa: D401
        self._resolve_pairs(queryset, parent_is="A")

    @admin.action(description="POŁĄCZ: Prawy obiekt (B) jest Rodzicem Lewego (A)")
    def make_b_parent(self, request, queryset):
        """"""  # noqa: D401
        self._resolve_pairs(queryset, parent_is="B")

    @admin.action(description="IGNORUJ: Obiekty nie są powiązane (np. dwa osobne szczyty)")
    def ignore_pair(self, request, queryset):
        """"""  # noqa: D401
        queryset.update(status="IGNORED")

    def _resolve_pairs(self, queryset, parent_is: str):
        """Mechanika łączenia w Klastry i inteligentnego ignorowania rodzeństwa.

        Args:
          queryset:
          parent_is: str:

        Returns:
        """
        for candidate in queryset.filter(status="PENDING"):
            if parent_is == "A":
                parent = candidate.obj_a
                child = candidate.obj_b
            else:
                parent = candidate.obj_b
                child = candidate.obj_a

            child.parent_object = parent
            child.save(update_fields=["parent_object"])

            candidate.status = "RESOLVED"
            candidate.save(update_fields=["status"])

            siblings_ids = parent.child_objects.values_list("id", flat=True)

            ProximityCandidate.objects.filter(status="PENDING").filter(
                Q(obj_a=child, obj_b_id__in=siblings_ids) | Q(obj_b=child, obj_a_id__in=siblings_ids)
            ).update(status="IGNORED")
