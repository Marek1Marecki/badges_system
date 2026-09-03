"""Przypadek użycia: Pobieranie i synchronizacja danych z OpenStreetMap.

Zgodnie z 14-domain-purity.md — zero importów apps/, django/, infrastructure/. Zgodnie z 17-determinism-contract.md —
czas wstrzykiwany przez ClockPort.
"""

from application.exceptions import TransientInfrastructureError, UseCaseError
from application.ports.clock_port import ClockPort
from application.ports.osm_port import OsmRepositoryPort


class FetchOsmDataUseCase:
    """Pobiera dane pojedynczego obiektu z OSM i aktualizuje model."""

    def __init__(self, osm_repository: OsmRepositoryPort, clock: ClockPort) -> None:
        """Inicjalizuje use case.

        Args:
            osm_repository: Adapter z metodami pobierania i zapisu danych OSM.
            clock: Dostawca aktualnego czasu.
        """
        self._repo = osm_repository
        self._clock = clock

    def execute(self, object_id: int) -> str:
        """Pobiera dane z OSM i aktualizuje obiekt turystyczny.

        Args:
          object_id: ID obiektu TouristObject do zaktualizowania.
          object_id: int:
          object_id: int:

        Returns:
          : Komunikat tekstowy o statusie.

        Raises:
          UseCaseError: Gdy obiekt nie istnieje lub nie ma OSM ID.
        """
        obj = self._repo.get_object_for_osm_fetch(object_id)

        if obj is None:
            raise UseCaseError(f"Obiekt o ID {object_id} nie istnieje.")

        osm_id = obj.get("osm_id")
        if not osm_id:
            return "Pominięto: Brak OSM ID."

        try:
            osm_node = self._repo.fetch_from_osm(osm_id)
            self._repo.update_object_from_osm(object_id, osm_node, obj)
        except TransientInfrastructureError as exc:
            raise UseCaseError(
                f"Usługa pobierania danych OSM jest chwilowo niedostępna dla obiektu {object_id}."
            ) from exc

        return f"Sukces: Pobrano dane OSM dla {osm_id}."


class RunOsmNightWatchmanUseCase:
    """Nocny skaner — wsadowa synchronizacja obiektów z OSM z wykrywaniem konfliktów."""

    def __init__(self, osm_repository: OsmRepositoryPort, clock: ClockPort) -> None:
        """Inicjalizuje use case.

        Args:
            osm_repository: Adapter z metodami synchronizacji OSM.
            clock: Dostawca aktualnego czasu — używany do last_sync_check.
        """
        self._repo = osm_repository
        self._clock = clock

    def execute(self, batch_size: int = 50) -> str:
        """Sprawdza partię obiektów w OSM i zgłasza konflikty.

        Args:
          batch_size: Liczba obiektów do sprawdzenia w jednym uruchomieniu.
          batch_size: int:  (Default value = 50)
          batch_size: int:  (Default value = 50)

        Returns:
          : Komunikat tekstowy z wynikiem skanowania.

        """
        objects_to_check = self._repo.get_objects_for_sync(batch_size)

        if not objects_to_check:
            return "Brak obiektów do synchronizacji."

        osm_ids = [obj["osm_id"] for obj in objects_to_check]
        osm_data_map = self._repo.fetch_multiple_from_osm(osm_ids)

        if osm_data_map is None:
            return "PRZERWANO: Błąd połączenia z API OSM."

        conflicts_created = 0
        updated_silently = 0
        current_time = self._clock.now()

        for obj in objects_to_check:
            object_id = obj["id"]
            osm_node = osm_data_map.get(obj["osm_id"])

            if not osm_node:
                self._repo.create_osm_sync_conflict(
                    object_id=object_id,
                    field_name="is_active",
                    old_value=str(obj["is_active"]),
                    new_value="False",
                )
                conflicts_created += 1
                self._repo.mark_sync_checked(object_id, current_time)
                continue

            new_conflicts = self._repo.detect_and_save_conflicts(object_id, obj, osm_node)
            conflicts_created += new_conflicts

            self._repo.update_object_after_sync(
                object_id=object_id,
                osm_raw_tags=osm_node.tags,
                osm_version=osm_node.version,
                osm_timestamp=osm_node.timestamp,
                last_sync_check=current_time,
            )
            updated_silently += 1

        return (
            f"Stróż skończył. Obiektów: {len(objects_to_check)}. "
            f"Konflikty: {conflicts_created}. Zaktualizowano cicho: {updated_silently}."
        )
