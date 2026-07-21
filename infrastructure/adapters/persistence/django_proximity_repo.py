"""Adapter dla systemu Radarowego Klastrowania (Proximity Scanner)."""

from typing import Any

from django.contrib.gis.measure import D

from application.ports.region_cache_port import ProximityCandidateRepositoryPort
from apps.badges.models import ProximityCandidate, TouristObject


class DjangoProximityRepository(ProximityCandidateRepositoryPort):
    """Przeszukuje obiekty blisko leżące, budując Skrzynkę Odbiorczą Klastrów."""

    def get_unprocessed_objects(self, limit: int = 100) -> list[tuple[int, Any]]:
        """Zwraca obiekty bez rodzica, które jeszcze nie zostały ocenione przez radar."""
        qs = TouristObject.objects.filter(parent_object__isnull=True, is_active=True, geom__isnull=False).exclude(
            # Omija te, które mają już wiszące zgłoszenie jako parent
            id__in=ProximityCandidate.objects.filter(status="PENDING").values_list("object_a_id", flat=True)
        )[:limit]

        return [(obj.id, obj.geom) for obj in qs]

    def find_nearby_objects(self, object_id: int, geometry: Any, distance_m: float) -> list[int]:
        """Wykorzystuje indeksy GiST PostGIS do błyskawicznego znalezienia sąsiadów w promieniu."""
        qs = TouristObject.objects.filter(
            geom__distance_lte=(geometry, D(m=distance_m)), is_active=True, parent_object__isnull=True
        ).exclude(id=object_id)

        return list(qs.values_list("id", flat=True))

    def save_candidate_pairs(self, parent_id: int, child_ids: list[int]) -> int:
        """Krzyżuje znalezione obiekty w pary, chroniąc przed duplikatami."""
        try:
            parent_obj = TouristObject.objects.get(id=parent_id)
        except TouristObject.DoesNotExist:
            return 0

        saved_count = 0
        for child_id in child_ids:
            try:
                child_obj = TouristObject.objects.get(id=child_id)
                # Ensure A -> B is the same as B -> A to avoid duplicates
                a, b = (parent_obj, child_obj) if parent_obj.id < child_obj.id else (child_obj, parent_obj)

                # Zapisujemy tylko jeśli taka para nie była nigdy procedowana
                _, created = ProximityCandidate.objects.get_or_create(
                    object_a=a, object_b=b, defaults={"status": "PENDING"}
                )
                if created:
                    saved_count += 1
            except TouristObject.DoesNotExist:
                continue

        return saved_count
