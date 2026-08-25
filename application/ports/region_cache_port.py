"""Porty aplikacyjne dla buforowania relacji regionalnych i analityki GIS (CQRS)."""

from typing import Any, Protocol


class RegionCacheRepositoryPort(Protocol):
    """Odpowiada wyłącznie za operacje na zmaterializowanym widoku regionów (ObjectRegionCache)."""

    def check_object_geometry_and_tags(self, object_id: int) -> tuple[bool, dict[str, Any]]:
        """Zwraca (czy_ma_geometrie, osm_raw_tags).

        Args:
          object_id: int:
          object_id: int:

        Returns:
        """
        ...

    def clear_cache_for_object(self, object_id: int) -> None:
        """Usuwa wszystkie wpisy cache dla danego obiektu.

        Args:
          object_id: int:
          object_id: int:

        Returns:
        """
        ...

    def clear_cache_for_region(self, region_id: int, region_level: str) -> None:
        """Usuwa wszystkie wpisy cache dla danego regionu i poziomu.

        Args:
          region_id: int:
          region_level: str:
          region_id: int:
          region_level: str:

        Returns:
        """
        ...

    def recalculate_all_region_levels(self, object_id: int) -> None:
        """Odpytuje GIS z buforem 50m dla standardowych poziomów administracyjnych.

        Args:
          object_id: int:
          object_id: int:

        Returns:
        """
        ...

    def recalculate_tourist_regions(self, object_id: int) -> None:
        """Kopiuje przypisania M2M do sztucznych regionów PTTK.

        Args:
          object_id: int:
          object_id: int:

        Returns:
        """
        ...

    def extract_and_save_local_names(self, object_id: int, osm_raw_tags: dict[str, Any]) -> None:
        """Wyodrębnia lokalne nazwy z tagów OSM i zapisuje je.

        Args:
          object_id: int:
          osm_raw_tags: dict[str:
          Any]:
          object_id: int:
          osm_raw_tags: dict[str:

        Returns:
        """
        ...

    def mark_object_as_ready(self, object_id: int) -> None:
        """Ustawia status obiektu na READY po zakończeniu asymilacji.

        Args:
          object_id: int:
          object_id: int:

        Returns:
        """
        ...

    def get_related_regions(self, tourist_region_id: int) -> list[tuple[int, str]]:
        """Zwraca listę powiązanych regionów (ID, poziom).

        Args:
          tourist_region_id: int:
          tourist_region_id: int:

        Returns:
        """
        ...


class TouristRegionGeometryRepositoryPort(Protocol):
    """Odpowiada wyłącznie za zarządzanie fizyczną geometrią Regionów Turystycznych."""

    def get_regions_without_geometry(self) -> list[int]:
        """Zwraca listę regionów bez zdefiniowanej geometrii."""
        ...

    def update_region_geometry(self, region_id: int) -> bool:
        """Kompiluje i zapisuje złączony kształt wielokąta wewnątrz warstwy bazy.

        Zwraca sukces.
                Args:
                  region_id: int:
                  region_id: int:

                Returns:
        """
        ...


class ProximityCandidateRepositoryPort(Protocol):
    """Odpowiada za radar przestrzenny wykrywający potencjalne klastry (Sąsiedztwo 150m)."""

    def get_unprocessed_objects(self, limit: int = 100) -> list[tuple[int, Any]]:
        """Zwraca obiekty bez rodzica, które nie zostały jeszcze ocenione.

        Args:
          limit: int:  (Default value = 100)
          limit: int:  (Default value = 100)

        Returns:

        """
        ...

    def find_nearby_objects(self, object_id: int, geometry: Any, distance_m: float) -> list[int]:
        """Znajduje obiekty w zadanym promieniu od punktu.

        Args:
          object_id: int:
          geometry: Any:
          distance_m: float:
          object_id: int:
          geometry: Any:
          distance_m: float:

        Returns:
        """
        ...

    def save_candidate_pairs(self, parent_id: int, child_ids: list[int]) -> int:
        """Zapisuje pary kandydatów do klastrowania, zwraca liczbę zapisanych.

        Args:
          parent_id: int:
          child_ids: list[int]:
          parent_id: int:
          child_ids: list[int]:

        Returns:
        """
        ...
