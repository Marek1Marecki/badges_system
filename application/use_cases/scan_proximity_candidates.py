"""Przypadek użycia: Skanowanie bazy w poszukiwaniu bliskich obiektów (Radar 150m).

Zgodnie z 14-domain-purity.md — zero importów apps/, django/, infrastructure/.
"""

from typing import Any


class ScanProximityCandidatesUseCase:
    """Skanuje bazę szukając par obiektów bliskich sobie (Radar 150m)."""

    SEARCH_RADIUS_METERS = 150.0

    def __init__(self, region_cache_repository: Any) -> None:
        """Inicjalizuje use case.

        Args:
            region_cache_repository: Adapter z metodami przestrzennymi.
        """
        self._repo = region_cache_repository

    def execute(self) -> str:
        """Wykonuje pełny skan bazy obiektów turystycznych.

        Returns:
            Komunikat tekstowy z wynikiem skanowania.
        """
        pairs = self._repo.find_proximity_candidates(self.SEARCH_RADIUS_METERS)

        created_count = 0
        for obj_a_id, obj_b_id, distance in pairs:
            created = self._repo.create_proximity_candidate(obj_a_id, obj_b_id, distance)
            if created:
                created_count += 1

        return f"Skanowanie zakończone. Utworzono {created_count} nowych kandydujących par."
