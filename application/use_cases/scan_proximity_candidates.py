"""Przypadek użycia: Skanowanie bazy w poszukiwaniu bliskich obiektów (Radar 150m).

Zgodnie z 14-domain-purity.md — zero importów apps/, django/, infrastructure/.
"""

from application.ports.region_cache_port import ProximityCandidateRepositoryPort

SEARCH_RADIUS_METERS = 150.0


class ScanProximityCandidatesUseCase:
    """Skanuje bazę szukając par obiektów bliskich sobie (Radar 150m)."""

    def __init__(self, proximity_repository: ProximityCandidateRepositoryPort) -> None:
        """Inicjalizuje use case.

        Args:
            proximity_repository: Adapter z metodami przestrzennymi.
        """
        self._repo = proximity_repository

    def execute(self) -> str:
        """Wykonuje skanowanie radarem przestrzennym (ST_DWithin).

        Returns:
            Tekstowy raport o ilości zapisanych potencjalnych klastrów.
        """
        # Szukamy kandydatów z portu (100 z wierzchu)
        unprocessed = self._repo.get_unprocessed_objects(limit=100)

        total_pairs = 0
        for obj_id, geom in unprocessed:
            if not geom:
                continue

            # Promień 150 metrów
            nearby_ids = self._repo.find_nearby_objects(obj_id, geom, distance_m=SEARCH_RADIUS_METERS)
            if nearby_ids:
                saved = self._repo.save_candidate_pairs(parent_id=obj_id, child_ids=nearby_ids)
                total_pairs += saved

        return f"Zakończono. Zapisano {total_pairs} nowych kandydatów do klastrowania."
