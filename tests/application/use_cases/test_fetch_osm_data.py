"""Testy jednostkowe dla przypadków użycia OSM."""

from unittest.mock import MagicMock

import pytest

from application.exceptions import TransientInfrastructureError, UseCaseError
from application.use_cases.fetch_osm_data import FetchOsmDataUseCase, RunOsmNightWatchmanUseCase
from tests.fakes.clock import FakeClock


class TestFetchOsmDataUseCase:
    """Testy FetchOsmDataUseCase."""

    def test_fetch_success(self) -> None:
        """Pobiera dane OSM i aktualizuje obiekt."""
        repo = MagicMock()
        clock = FakeClock()
        repo.get_object_for_osm_fetch.return_value = {"id": 1, "osm_id": "node/1"}
        repo.fetch_from_osm.return_value = "fake_node"

        uc = FetchOsmDataUseCase(repo, clock)
        result = uc.execute(1)

        assert "Sukces" in result
        repo.update_object_from_osm.assert_called_once_with(1, "fake_node", {"id": 1, "osm_id": "node/1"})

    def test_fetch_not_found(self) -> None:
        """Rzuca błąd gdy obiekt nie istnieje."""
        repo = MagicMock()
        repo.get_object_for_osm_fetch.return_value = None
        uc = FetchOsmDataUseCase(repo, FakeClock())

        with pytest.raises(UseCaseError):
            uc.execute(1)

    def test_fetch_no_osm_id(self) -> None:
        """Pomija obiekt bez osm_id."""
        repo = MagicMock()
        repo.get_object_for_osm_fetch.return_value = {"id": 1, "osm_id": None}
        uc = FetchOsmDataUseCase(repo, FakeClock())

        result = uc.execute(1)
        assert "Pominięto" in result

    def test_fetch_infra_error_translated_to_usecase_error(self) -> None:
        """Infrastrukturalny błąd OSM jest tłumaczony na ApplicationException (AUDYT-123)."""
        repo = MagicMock()
        clock = FakeClock()
        repo.get_object_for_osm_fetch.return_value = {"id": 1, "osm_id": "node/1"}
        repo.fetch_from_osm.side_effect = TransientInfrastructureError("Overpass timeout")

        uc = FetchOsmDataUseCase(repo, clock)
        with pytest.raises(UseCaseError, match="niedostępna"):
            uc.execute(1)


class TestRunOsmNightWatchmanUseCase:
    """Testy RunOsmNightWatchmanUseCase."""

    def test_watchman_success(self) -> None:
        """Stróż OSM poprawnie synchronizuje obiekty."""
        repo = MagicMock()
        clock = FakeClock()
        repo.get_objects_for_sync.return_value = [{"id": 1, "osm_id": "node/1", "is_active": True}]

        mock_node = MagicMock()
        mock_node.tags = {}
        mock_node.version = 1
        mock_node.timestamp = "ts"

        repo.fetch_multiple_from_osm.return_value = {"node/1": mock_node}
        repo.detect_and_save_conflicts.return_value = 0

        uc = RunOsmNightWatchmanUseCase(repo, clock)
        result = uc.execute()

        assert "Stróż skończył" in result
        repo.update_object_after_sync.assert_called_once()

    def test_watchman_no_objects(self) -> None:
        """Zwraca komunikat gdy brak obiektów do synchronizacji."""
        repo = MagicMock()
        repo.get_objects_for_sync.return_value = []
        uc = RunOsmNightWatchmanUseCase(repo, FakeClock())
        assert "Brak obiektów" in uc.execute()

    def test_watchman_ghost_node_detection(self) -> None:
        """Wykrywa usunięte węzły OSM jako konflikty."""
        repo = MagicMock()
        repo.get_objects_for_sync.return_value = [{"id": 1, "osm_id": "node/1", "is_active": True}]
        # Zwracamy pusty słownik, co oznacza że OSM nie znalazł node/1 (został usunięty)
        repo.fetch_multiple_from_osm.return_value = {}

        uc = RunOsmNightWatchmanUseCase(repo, FakeClock())
        result = uc.execute()

        assert "Stróż skończył" in result
        # Powinien wygenerować konflikt "is_active -> False"
        repo.create_osm_sync_conflict.assert_called_once()
        repo.mark_sync_checked.assert_called_once()

    def test_watchman_osm_connection_failure(self) -> None:
        """Cicho obsługuje błąd połączenia z OSM."""
        repo = MagicMock()
        repo.get_objects_for_sync.return_value = [{"id": 1, "osm_id": "node/1", "is_active": True}]
        repo.fetch_multiple_from_osm.return_value = None

        uc = RunOsmNightWatchmanUseCase(repo, FakeClock())
        result = uc.execute()

        assert "PRZERWANO" in result
