"""Przypadek użycia: Obliczanie przynależności geograficznej obiektu turystycznego.

Zgodnie z 17-determinism-contract.md — czas wstrzykiwany przez ClockPort.
Zgodnie z 14-domain-purity.md — zero importów apps/, django/, infrastructure/.
"""

from typing import Any

from application.exceptions import UseCaseError
from application.ports.clock_port import ClockPort

RELEVANT_LANGS = ["pl", "cs", "sk", "de", "uk", "be", "szl", "csb", "hu", "ru", "rue"]


class CalculateObjectRegionsUseCase:
    """Oblicza i zapisuje przynależność geograficzną obiektu turystycznego."""

    def __init__(self, region_cache_repository: Any, clock: ClockPort) -> None:
        """Inicjalizuje use case.

        Args:
            region_cache_repository: Adapter wykonujący zapytania PostGIS.
            clock: Dostawca aktualnego czasu (wstrzykiwany — nie datetime.now()).
        """
        self._repo = region_cache_repository
        self._clock = clock

    def execute(self, object_id: int) -> str:
        """Oblicza regiony dla obiektu i aktualizuje cache.

        Args:
            object_id: ID obiektu TouristObject do przeliczenia.

        Returns:
            Komunikat tekstowy o statusie.

        Raises:
            UseCaseError: Gdy obiekt nie istnieje.
        """
        obj = self._repo.get_tourist_object(object_id)

        if obj is None:
            raise UseCaseError(f"Obiekt o ID {object_id} nie istnieje.")

        if not obj.has_geom:
            return f"Pominięto: Obiekt '{obj.name}' (ID: {object_id}) nie ma geometrii."

        matches = self._repo.find_regions_for_point(obj.geom)
        self._repo.replace_cache_for_object(object_id, matches)
        self._extract_and_save_local_names(obj, object_id)

        return f"Sukces: Przeliczono '{obj.name}'. Znaleziono {len(matches)} regionów."

    def _extract_and_save_local_names(self, obj: Any, object_id: int) -> None:
        """Wyodrębnia lokalne nazwy z tagów OSM i zapisuje przez adapter."""
        raw_tags = obj.osm_raw_tags
        if not raw_tags:
            return

        new_local_names: dict[str, str] = dict(obj.local_names or {})
        updated = False

        for lang_code in RELEVANT_LANGS:
            tag_key = f"name:{lang_code}"
            if tag_key not in raw_tags:
                continue
            val = raw_tags[tag_key]
            if val != obj.name and new_local_names.get(lang_code) != val:
                new_local_names[lang_code] = val
                updated = True

        if updated:
            self._repo.save_local_names(object_id, new_local_names)
