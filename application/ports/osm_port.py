"""Porty aplikacyjne dla synchronizacji danych OpenStreetMap."""

from datetime import datetime
from typing import Any, Protocol, TypedDict


class TouristObjectOsmSnapshot(TypedDict, total=False):
    """Minimalny obraz obiektu turystycznego potrzebny do pracy z OSM."""

    id: int
    osm_id: str | None
    name: str | None
    alt_name: str | None
    altitude: int | None
    wikipedia_link: str | None
    has_geom: bool
    type: str | None


class TouristObjectOsmSyncSnapshot(TypedDict):
    """Obiekt zakwalifikowany do nocnej synchronizacji OSM."""

    id: int
    osm_id: str
    altitude: int | None
    wikipedia_link: str | None
    is_active: bool


class OsmNodeData(Protocol):
    """Dane pojedynczego obiektu OSM używane przez przypadki użycia."""

    tags: dict[str, Any]
    version: int | None
    timestamp: datetime | None

    @property
    def latitude(self) -> float:
        """Szerokość geograficzna obiektu."""
        ...

    @property
    def longitude(self) -> float:
        """Długość geograficzna obiektu."""
        ...


class OsmRepositoryPort(Protocol):
    """Kontrakt repozytorium OSM widziany z warstwy aplikacyjnej."""

    def get_object_for_osm_fetch(self, object_id: int) -> TouristObjectOsmSnapshot | None:
        """Zwraca dane obiektu potrzebne do pobrania z OSM.

        Args:
          object_id: int:
          object_id: int:

        Returns:
        """
        ...

    def fetch_from_osm(self, osm_id: str) -> OsmNodeData:
        """Pobiera aktualne dane obiektu z OSM.

        Args:
          osm_id: str:
          osm_id: str:

        Returns:
        """
        ...

    def fetch_multiple_from_osm(self, osm_ids: list[str]) -> dict[str, OsmNodeData] | None:
        """Pobiera aktualne dane wielu obiektów z OSM.

        Args:
          osm_ids: list[str]:
          osm_ids: list[str]:

        Returns:
        """
        ...

    def update_object_from_osm(
        self,
        object_id: int,
        osm_node: OsmNodeData,
        current_data: TouristObjectOsmSnapshot,
    ) -> None:
        """Zapisuje dane pobrane z OSM do lokalnego obiektu.

        Args:
          object_id: int:
          osm_node: OsmNodeData:
          current_data: TouristObjectOsmSnapshot:
          object_id: int:
          osm_node: OsmNodeData:
          current_data: TouristObjectOsmSnapshot:

        Returns:
        """
        ...

    def get_objects_for_sync(self, batch_size: int) -> list[TouristObjectOsmSyncSnapshot]:
        """Zwraca partię obiektów do synchronizacji OSM.

        Args:
          batch_size: int:
          batch_size: int:

        Returns:
        """
        ...

    def update_object_after_sync(
        self,
        object_id: int,
        osm_raw_tags: dict[str, Any],
        osm_version: int | None,
        osm_timestamp: datetime | None,
        last_sync_check: datetime,
    ) -> None:
        """Aktualizuje metadane synchronizacji po udanym sprawdzeniu OSM.

        Args:
          object_id: int:
          osm_raw_tags: dict[str:
          Any]:
          osm_version: int | None:
          osm_timestamp: datetime | None:
          last_sync_check: datetime:
          object_id: int:
          osm_raw_tags: dict[str:
          osm_version: int | None:
          osm_timestamp: datetime | None:
          last_sync_check: datetime:

        Returns:
        """
        ...

    def mark_sync_checked(self, object_id: int, checked_at: datetime) -> None:
        """Oznacza obiekt jako sprawdzony w synchronizacji OSM.

        Args:
          object_id: int:
          checked_at: datetime:
          object_id: int:
          checked_at: datetime:

        Returns:
        """
        ...

    def create_osm_sync_conflict(self, object_id: int, field_name: str, old_value: str, new_value: str) -> None:
        """Tworzy konflikt synchronizacji OSM.

        Args:
          object_id: int:
          field_name: str:
          old_value: str:
          new_value: str:
          object_id: int:
          field_name: str:
          old_value: str:
          new_value: str:

        Returns:
        """
        ...

    def detect_and_save_conflicts(
        self,
        object_id: int,
        current_data: TouristObjectOsmSyncSnapshot,
        osm_node: OsmNodeData,
    ) -> int:
        """Porównuje stan lokalny z OSM i zapisuje konflikty.

        Args:
          object_id: int:
          current_data: TouristObjectOsmSyncSnapshot:
          osm_node: OsmNodeData:
          object_id: int:
          current_data: TouristObjectOsmSyncSnapshot:
          osm_node: OsmNodeData:

        Returns:
        """
        ...
