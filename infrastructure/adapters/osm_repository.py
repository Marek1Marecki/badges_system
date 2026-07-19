"""Adapter repozytorium dla operacji OSM — pobieranie i zapis danych z OpenStreetMap.

Łączy OverpassClient (zewnętrzne HTTP) z operacjami ORM na modelach Django.
Use case'y FetchOsmDataUseCase i RunOsmNightWatchmanUseCase używają tego adaptera
zamiast bezpośrednich importów z apps/ i infrastructure/.

Zgodnie z 22-ports-adapters-dto-contract.md:
- Adapter zna Django ORM, OverpassClient i modele — use case'y nie
- Metody przyjmują i zwracają proste typy Pythona lub None
"""

from datetime import datetime
from typing import Any, cast

from application.ports.osm_port import (
    OsmNodeData,
    TouristObjectOsmSnapshot,
    TouristObjectOsmSyncSnapshot,
)
from infrastructure.adapters.osm_adapter import OsmAdapterError, OsmDataExtractor, OverpassClient


class OsmRepository:
    """Zarządza pobieraniem danych OSM i zapisem wyników do bazy Django."""

    def get_object_for_osm_fetch(self, object_id: int) -> TouristObjectOsmSnapshot | None:
        """Zwraca dane obiektu potrzebne do pobrania z OSM lub None."""
        from apps.badges.models import TouristObject

        try:
            obj = TouristObject.objects.get(id=object_id)
        except TouristObject.DoesNotExist:
            return None

        return {
            "id": obj.id,
            "osm_id": obj.osm_id,
            "name": obj.name,
            "alt_name": obj.alt_name,
            "altitude": obj.altitude,
            "wikipedia_link": obj.wikipedia_link,
            "has_geom": bool(obj.geom),
            "type": obj.type,
        }

    def fetch_from_osm(self, osm_id: str) -> OsmNodeData:
        """Pobiera dane węzła z Overpass API.

        Raises:
            OsmAdapterError: Przy błędzie połączenia lub parsowania.
        """
        client = OverpassClient()
        return client.fetch_object(osm_id)

    def fetch_multiple_from_osm(self, osm_ids: list[str]) -> dict[str, OsmNodeData] | None:
        """Pobiera dane wielu węzłów z Overpass API.

        Returns:
            Słownik {osm_id: node} lub None przy błędzie połączenia.
        """
        client = OverpassClient()
        try:
            return cast("dict[str, OsmNodeData]", client.fetch_multiple_objects(osm_ids))
        except OsmAdapterError:
            return None

    def update_object_from_osm(
        self,
        object_id: int,
        osm_node: OsmNodeData,
        current_data: TouristObjectOsmSnapshot,
    ) -> None:
        """Aktualizuje obiekt turystyczny danymi z OSM (Data Override — chroni ręczne dane)."""
        from django.contrib.gis.geos import Point

        from apps.badges.models import TouristObject

        obj = TouristObject.objects.get(id=object_id)
        obj.osm_raw_tags = osm_node.tags

        if not current_data.get("name"):
            ext_name = OsmDataExtractor.extract_name(osm_node.tags)
            if ext_name:
                obj.name = ext_name

        if not current_data.get("alt_name"):
            ext_alt = OsmDataExtractor.extract_alt_name(osm_node.tags, obj.name)
            if ext_alt:
                obj.alt_name = ext_alt

        if current_data.get("altitude") is None:
            ext_altit = OsmDataExtractor.extract_altitude(osm_node.tags)
            if ext_altit is not None:
                obj.altitude = ext_altit

        if not current_data.get("wikipedia_link"):
            ext_wiki = OsmDataExtractor.extract_wikipedia_link(osm_node.tags)
            if ext_wiki:
                obj.wikipedia_link = ext_wiki

        if osm_node.version:
            obj.osm_version = osm_node.version
        if osm_node.timestamp:
            obj.osm_timestamp = osm_node.timestamp

        if not current_data.get("has_geom"):
            obj.geom = Point(osm_node.longitude, osm_node.latitude, srid=4326)

        determined_type, _ = OsmDataExtractor.determine_type(osm_node.tags)
        if determined_type:
            obj.type = determined_type
        elif not current_data.get("type"):
            obj.type = "Inny punkt"

        obj.status = "READY"
        obj.osm_error = None
        obj.save()

    def get_objects_for_sync(self, batch_size: int) -> list[TouristObjectOsmSyncSnapshot]:
        """Zwraca partię obiektów do synchronizacji (najdawniej sprawdzane)."""
        from django.db.models import F

        from apps.badges.models import TouristObject

        qs = (
            TouristObject.objects.exclude(osm_id__isnull=True)
            .exclude(osm_id="")
            .order_by(F("last_sync_check").asc(nulls_first=True))[:batch_size]
        )

        return [
            {
                "id": obj.id,
                "osm_id": obj.osm_id,
                "altitude": obj.altitude,
                "wikipedia_link": obj.wikipedia_link,
                "is_active": obj.is_active,
            }
            for obj in qs
        ]

    def update_object_after_sync(
        self,
        object_id: int,
        osm_raw_tags: dict[str, Any],
        osm_version: int | None,
        osm_timestamp: datetime | None,
        last_sync_check: datetime,
    ) -> None:
        """Zapisuje wynik synchronizacji OSM do obiektu."""
        from apps.badges.models import TouristObject

        TouristObject.objects.filter(id=object_id).update(
            osm_raw_tags=osm_raw_tags,
            osm_version=osm_version,
            osm_timestamp=osm_timestamp,
            last_sync_check=last_sync_check,
        )

    def mark_sync_checked(self, object_id: int, checked_at: datetime) -> None:
        """Aktualizuje tylko pole last_sync_check."""
        from apps.badges.models import TouristObject

        TouristObject.objects.filter(id=object_id).update(last_sync_check=checked_at)

    def create_osm_sync_conflict(self, object_id: int, field_name: str, old_value: str, new_value: str) -> None:
        """Tworzy wpis konfliktu synchronizacji OSM jeśli nie istnieje."""
        from apps.badges.models import OsmSyncConflict, TouristObject

        obj = TouristObject.objects.get(id=object_id)
        OsmSyncConflict.objects.get_or_create(
            tourist_object=obj,
            field_name=field_name,
            defaults={"old_value": old_value, "new_value": new_value},
        )

    def detect_and_save_conflicts(
        self,
        object_id: int,
        current_data: TouristObjectOsmSyncSnapshot,
        osm_node: OsmNodeData,
    ) -> int:
        """Porównuje dane lokalne z OSM i zapisuje konflikty.

        Returns:
            Liczba nowo utworzonych konfliktów.
        """
        conflicts = 0

        ext_alt = OsmDataExtractor.extract_altitude(osm_node.tags)
        if ext_alt is not None and ext_alt != current_data.get("altitude"):
            self.create_osm_sync_conflict(
                object_id=object_id,
                field_name="altitude",
                old_value=str(current_data.get("altitude")),
                new_value=str(ext_alt),
            )
            conflicts += 1

        ext_wiki = OsmDataExtractor.extract_wikipedia_link(osm_node.tags)
        if ext_wiki and ext_wiki != current_data.get("wikipedia_link"):
            self.create_osm_sync_conflict(
                object_id=object_id,
                field_name="wikipedia_link",
                old_value=current_data.get("wikipedia_link") or "Brak",
                new_value=ext_wiki,
            )
            conflicts += 1

        return conflicts
