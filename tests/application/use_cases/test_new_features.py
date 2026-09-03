"""Szybkie testy jednostkowe dla nowych Use Case'ów z Fazy C.

Oparte na mockach, by uniknąć łączenia się z PostGIS/Redis.
Pokrywają logistykę, mapy oraz skrapera aktualności.
"""

from unittest.mock import MagicMock

import pytest

from application.dto.map_dto import MapExploreRequestDTO
from application.exceptions import ConflictError, UseCaseError

# 1. LOGISTYKA KANBAN
from application.use_cases.advance_logistic_status import AdvanceLogisticStatusUseCase


class TestAdvanceLogisticStatusUseCase:
    """Testy AdvanceLogisticStatusUseCase."""

    def test_raises_when_progress_not_found(self) -> None:
        """Rzuca błąd gdy postęp nie istnieje."""
        repo = MagicMock()
        repo.get_progress_by_id.return_value = None
        uc = AdvanceLogisticStatusUseCase(repo, MagicMock())

        with pytest.raises(UseCaseError, match="nie istnieje"):
            uc.execute(1, 1, "WAITING_FOR_SEND", "2026-01-01", actor_user_id=1)

    def test_raises_when_domain_not_completed(self) -> None:
        """Rzuca błąd gdy domena nie jest zakończona."""
        repo = MagicMock()
        prog = MagicMock(domain_status="IN_PROGRESS")
        repo.get_progress_by_id.return_value = prog
        uc = AdvanceLogisticStatusUseCase(repo, MagicMock())

        with pytest.raises(ConflictError, match="Nie można aktualizować"):
            uc.execute(1, 1, "WAITING_FOR_SEND", "2026-01-01", actor_user_id=1)

    def test_raises_on_invalid_transition(self) -> None:
        """Rzuca błąd przy nieprawidłowym przejściu statusu."""
        repo = MagicMock()
        prog = MagicMock(domain_status="COMPLETED", logistic_status="WAITING_FOR_VERIFICATION")
        repo.get_progress_by_id.return_value = prog
        uc = AdvanceLogisticStatusUseCase(repo, MagicMock())

        # Próba nieprawidłowego przejścia (WAITING_FOR_VERIFICATION -> ALBUM nie jest dozwolone)
        with pytest.raises(ConflictError, match="Niedozwolone przejście"):
            uc.execute(1, 1, "ALBUM", "2026-01-01", actor_user_id=1)

    def test_success_transition(self) -> None:
        """Prawidłowo aktualizuje status logistyczny."""
        repo = MagicMock()
        publisher = MagicMock()
        prog = MagicMock(
            domain_status="COMPLETED",
            logistic_status="WAITING_FOR_VERIFICATION",
            progress_id=42,
            badge_code="KGP",
            version_id=3,
        )
        repo.get_progress_by_id.return_value = prog
        uc = AdvanceLogisticStatusUseCase(repo, publisher)

        uc.execute(1, 1, "WAITING_FOR_RECEIVING", "2026-01-01", actor_user_id=9)
        repo.update_logistic_status.assert_called_once_with(
            progress_id=42, logistic_status="WAITING_FOR_RECEIVING", status_date="2026-01-01"
        )
        publisher.publish.assert_called_once()


# 2. EXPLORE MAP (GEOJSON)
from application.use_cases.explore_map import ExploreMapUseCase


class TestExploreMapUseCase:
    """Testy ExploreMapUseCase."""

    def test_builds_geojson_successfully(self) -> None:
        """Buduje GeoJSON z koloryfikacją i wynikami."""
        repo = MagicMock()
        cache = MagicMock()

        # Symulacja bazy danych
        obj_mock = MagicMock(id=1, name="Rysy", type="Szczyt", lon=20.0, lat=49.0)
        repo.get_objects_in_bbox.return_value = [obj_mock]

        # Symulacja Redis (dane w postaci stringów)
        cache.get.return_value = {"colors": {"1": "RED"}, "scores": {"1": 100}}

        uc = ExploreMapUseCase(repo, cache)
        dto = MapExploreRequestDTO(profile_id=1, min_lon=0, min_lat=0, max_lon=1, max_lat=1)

        result = uc.execute(dto)
        assert result.type == "FeatureCollection"
        assert len(result.features) == 1
        assert result.features[0].properties["peak_color"] == "RED"
        assert result.features[0].properties["potential_score"] == 100

    def test_defaults_to_gray_when_no_cache(self) -> None:
        """Domyślnie szary kolor i zerowy wynik gdy brak cache."""
        repo = MagicMock()
        repo.get_objects_in_bbox.return_value = [MagicMock(id=2, name="Test", type="Szczyt", lon=0, lat=0)]
        cache = MagicMock()
        cache.get.return_value = None  # Brak klucza w Redis

        uc = ExploreMapUseCase(repo, cache)
        result = uc.execute(MapExploreRequestDTO(profile_id=1, min_lon=0, min_lat=0, max_lon=1, max_lat=1))

        assert result.features[0].properties["peak_color"] == "GRAY"
        assert result.features[0].properties["potential_score"] == 0


# 3. KAFELKI WEKTOROWE (MVT)
from application.use_cases.get_mvt_tile import GetMvtTileUseCase


class TestGetMvtTileUseCase:
    """Testy GetMvtTileUseCase."""

    def test_raises_on_invalid_layer(self) -> None:
        """Rzuca błąd przy nieznanej warstwie."""
        repo = MagicMock()
        cache = MagicMock()
        uc = GetMvtTileUseCase(repo, cache)

        with pytest.raises(UseCaseError, match="Nieznana warstwa"):
            uc.execute("invalid_layer", 0, 0, 0)

    def test_success_returns_bytes(self) -> None:
        """Zwraca skompresowane dane kafelka MVT."""
        import gzip

        repo = MagicMock()
        repo.get_tile.return_value = b"tile_data"
        cache = MagicMock()
        cache.get.return_value = None
        uc = GetMvtTileUseCase(repo, cache)

        result = uc.execute("country", 0, 0, 0)
        # Use case zwraca skompresowane dane gzip
        assert result == gzip.compress(b"tile_data")
        repo.get_tile.assert_called_once_with("country", 0, 0, 0)


# 4. SCRAPER AKTUALNOŚCI (NEWS)
from application.use_cases.fetch_badge_news import FetchBadgeNewsUseCase


class TestFetchBadgeNewsUseCase:
    """Testy FetchBadgeNewsUseCase."""

    def test_fail_silently_on_scraper_error(self) -> None:
        """Cicho obsługuje błąd scrapera."""
        scraper = MagicMock()
        scraper.fetch_news.side_effect = Exception("HTTP 500")
        repo = MagicMock()

        uc = FetchBadgeNewsUseCase(scraper, repo)
        result = uc.execute()

        assert "PRZERWANO (Ciche niepowodzenie)" in result
        repo.save_news_item.assert_not_called()

    def test_returns_empty_when_no_items(self) -> None:
        """Zwraca komunikat gdy brak elementów."""
        scraper = MagicMock()
        scraper.fetch_news.return_value = []
        uc = FetchBadgeNewsUseCase(scraper, MagicMock())
        assert "Nie znaleziono żadnych elementów" in uc.execute()

    def test_saves_new_items_successfully(self) -> None:
        """Zapisuje nowe wpisy, pomija duplikaty."""
        scraper = MagicMock()
        scraper.fetch_news.return_value = ["item1", "item2"]
        repo = MagicMock()
        # Pierwszy wpis nowy (True), drugi to duplikat (False)
        repo.save_news_item.side_effect = [True, False]

        uc = FetchBadgeNewsUseCase(scraper, repo)
        result = uc.execute()

        assert "z czego 1 to nowe wpisy" in result
        assert repo.save_news_item.call_count == 2
