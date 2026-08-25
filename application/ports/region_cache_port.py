"""Porty aplikacyjne dla buforowania relacji regionalnych i analityki GIS (CQRS)."""

from typing import Any, Protocol


class RegionCacheRepositoryPort(Protocol):
    """Odpowiada wyłącznie za operacje na zmaterializowanym widoku regionów (ObjectRegionCache)."""

    def check_object_geometry_and_tags(self, object_id: int) -> tuple[bool, dict[str, Any]]:
        """Zwraca (czy_ma_geometrie, osm_raw_tags)."""
        ...

    def clear_cache_for_object(self, object_id: int) -> None:
        """Usuwa wszystkie wpisy cache dla danego obiektu."""
        ...

    def clear_cache_for_region(self, region_id: int, region_level: str) -> None:
        """Usuwa wszystkie wpisy cache dla danego regionu i poziomu."""
        ...

    def recalculate_all_region_levels(self, object_id: int) -> None:
        """Odpytuje GIS z buforem 50m dla standardowych poziomów administracyjnych."""
        ...

    def recalculate_tourist_regions(self, object_id: int) -> None:
        """Kopiuje przypisania M2M do sztucznych regionów PTTK."""
        ...

    def extract_and_save_local_names(self, object_id: int, osm_raw_tags: dict[str, Any]) -> None:
        """Wyodrębnia lokalne nazwy z tagów OSM i zapisuje je."""
        ...

    def mark_object_as_ready(self, object_id: int) -> None:
        """Ustawia status obiektu na READY po zakończeniu asymilacji."""
        ...

    def get_related_regions(self, tourist_region_id: int) -> list[tuple[int, str]]:
        """Zwraca listę powiązanych regionów (ID, poziom)."""
        ...


class TouristRegionGeometryRepositoryPort(Protocol):
    """Odpowiada wyłącznie za zarządzanie fizyczną geometrią Regionów Turystycznych."""

    def get_regions_without_geometry(self) -> list[int]:
        """Zwraca listę regionów bez zdefiniowanej geometrii."""
        ...

    def update_region_geometry(self, region_id: int) -> bool:
        """Kompiluje i zapisuje złączony kształt wielokąta wewnątrz warstwy bazy.

        Zwraca sukces.
        """
        ...


class ProximityCandidateRepositoryPort(Protocol):
    """Odpowiada za radar przestrzenny wykrywający potencjalne klastry (Sąsiedztwo 150m)."""

    def get_unprocessed_objects(self, limit: int = 100) -> list[tuple[int, Any]]:
        """Zwraca obiekty bez rodzica, które nie zostały jeszcze ocenione."""
        ...

    def find_nearby_objects(self, object_id: int, geometry: Any, distance_m: float) -> list[int]:
        """Znajduje obiekty w zadanym promieniu od punktu."""
        ...

    def save_candidate_pairs(self, parent_id: int, child_ids: list[int]) -> int:
        """Zapisuje pary kandydatów do klastrowania, zwraca liczbę zapisanych."""
        ...
