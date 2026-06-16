"""Przypadek użycia: Eksploracja Mapy (Generowanie GeoJSON).

Zgodnie z ADR-011 i ADR-013: Łączy szybkie zapytanie przestrzenne (BBox)
z pre-kalkulowanymi stanami z pamięci Cache (Kolor i Punktacja POI).
"""

from typing import Any

from application.dto.map_dto import MapExploreRequestDTO
from application.ports.cache_port import CachePort
from application.ports.map_port import MapRepositoryPort


class ExploreMapUseCase:
    """Buduje spersonalizowaną warstwę GeoJSON z kolorami dla turysty."""

    def __init__(self, map_repository: MapRepositoryPort, cache: CachePort) -> None:
        """Inicjalizuje use case z repozytorium map i cache."""
        self._map_repo = map_repository
        self._cache = cache

    def execute(self, request: MapExploreRequestDTO) -> dict[str, Any]:
        """Zwraca gotowy do wyświetlenia słownik w formacie GeoJSON."""
        # 1. Pobranie fizycznych obiektów z okna mapy (Docinanie BBox)
        objects = self._map_repo.get_objects_in_bbox(
            min_lon=request.min_lon,
            min_lat=request.min_lat,
            max_lon=request.max_lon,
            max_lat=request.max_lat,
            badge_code=request.badge_code,
            region_level=request.region_level,
            region_id=request.region_id,
        )

        # 2. Pobranie zmaterializowanych statystyk dla użytkownika z Redis (O(1))
        cache_key = f"map_state:{request.user_id}"
        cached_data = self._cache.get(cache_key) or {}

        # Redis serializuje klucze słownika jako stringi, więc zachowujemy str(id)
        colors = cached_data.get("colors", {})
        scores = cached_data.get("scores", {})

        # 3. Złożenie formatu GeoJSON (FeatureCollection)
        features = []
        for obj in objects:
            # Jeśli obiektu nie ma w cache (bo np. turysta nie subskrybuje jego odznaki),
            # staje się dla niego wizualnie "szary" i nie przynosi punktów.
            # POPRAWKA: Szukamy najpierw po int (natywny Cache Django),
            # a awaryjnie po str (czysty JSON). Jeśli brak trafień -> GRAY / 0.
            color = colors.get(obj.id, colors.get(str(obj.id), "GRAY"))
            score = scores.get(obj.id, scores.get(str(obj.id), 0))

            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [obj.lon, obj.lat],  # GeoJSON wymusza [Lon, Lat]
                    },
                    "properties": {
                        "id": obj.id,
                        "name": obj.name,
                        "type": obj.type,
                        "peak_color": color,
                        "potential_score": score,
                    },
                }
            )

        return {"type": "FeatureCollection", "features": features}
