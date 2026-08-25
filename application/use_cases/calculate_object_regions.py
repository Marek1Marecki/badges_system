"""Przypadek użycia: Przeliczanie przynależności terytorialnej szczytów (CQRS)."""

from application.ports.clock_port import ClockPort
from application.ports.region_cache_port import RegionCacheRepositoryPort


class CalculateObjectRegionsUseCase:
    """Odświeża zmaterializowane widoki przynależności obiektów do regionów (M2M)."""

    def __init__(self, region_cache_repository: RegionCacheRepositoryPort, clock: ClockPort) -> None:
        """Inicjalizuje przypadek użycia przeliczania regionów."""
        self._repo = region_cache_repository
        self._clock = clock

    def execute(self, object_id: int) -> None:
        """Przelicza relacje przestrzenne w locie, delegując złączenia do portów.

        Args:
          object_id: ID obiektu turystycznego.

        Returns:
          None.
        """
        # 1. Sprawdzamy, czy obiekt istnieje i ma geometrię (delegacja do portu)
        has_geometry, raw_tags = self._repo.check_object_geometry_and_tags(object_id)
        if not has_geometry:
            return

        # 2. Czyścimy stare wpisy
        self._repo.clear_cache_for_object(object_id=object_id)

        # 3. Zasilanie Słownika M2M (Wydzielone bezpiecznie do infrastruktury)
        self._repo.recalculate_all_region_levels(object_id)

        # 4. Syntetyczne Regiony Turystyczne (Dziedziczenie)
        self._repo.recalculate_tourist_regions(object_id)

        # 5. Wyłuskanie nazw regionalnych z JSONB do twardych kolumn (Whitelisting OSM)
        if raw_tags:
            self._repo.extract_and_save_local_names(object_id, raw_tags)

        # Zmieniamy status po zakończeniu procedury Asymilacji
        self._repo.mark_object_as_ready(object_id)
