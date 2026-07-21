"""Testy jednostkowe zadań Celery (wrappers)."""

from unittest.mock import MagicMock, patch

import pytest

from apps.badges.tasks import (
    fetch_badge_news_task,
    fetch_osm_data_task,
    recalculate_poi_scores_task,
    run_osm_night_watchman_task,
    scan_proximity_candidates_task,
)


# Aby mock kontenera zachowywał się jak AppContainer (po kropce), używamy mocków właściwości.
@pytest.fixture
def mock_container():
    container = MagicMock()
    # Konfiguracja Mocków
    container.fetch_osm_data = MagicMock()
    container.scan_proximity_candidates = MagicMock()
    container.run_osm_night_watchman = MagicMock()
    container.poi_scoring_service = MagicMock()
    container.fetch_badge_news = MagicMock()
    return container


class TestFetchOsmDataTask:
    @patch("bootstrap.get_container")
    @patch("apps.badges.tasks.calculate_object_regions_task.delay")
    def test_successful_fetch(self, mock_delay, mock_get_container, mock_container):
        mock_get_container.return_value = mock_container
        mock_container.fetch_osm_data.execute.return_value = "Sukces"

        result = fetch_osm_data_task(42)

        mock_container.fetch_osm_data.execute.assert_called_once_with(42)
        mock_delay.assert_called_once_with(42)
        assert result == "Sukces"

    @patch("bootstrap.get_container")
    @patch("apps.badges.tasks.calculate_object_regions_task.delay")
    def test_use_case_error(self, mock_delay, mock_get_container, mock_container):
        from application.exceptions import UseCaseError

        mock_get_container.return_value = mock_container
        mock_container.fetch_osm_data.execute.side_effect = UseCaseError("Błąd logiki")

        result = fetch_osm_data_task(99)

        assert "Błąd logiki" in result


class TestScanProximityCandidatesTask:
    @patch("bootstrap.get_container")
    def test_successful_scan(self, mock_get_container, mock_container):
        mock_get_container.return_value = mock_container
        mock_container.scan_proximity_candidates.execute.return_value = 5

        result = scan_proximity_candidates_task()

        assert result == "5"

    @patch("bootstrap.get_container")
    def test_exception_handling(self, mock_get_container, mock_container):
        mock_get_container.return_value = mock_container
        mock_container.scan_proximity_candidates.execute.side_effect = Exception("Test error")

        with pytest.raises(Exception):
            scan_proximity_candidates_task()


class TestRunOsmNightWatchmanTask:
    @patch("bootstrap.get_container")
    def test_successful_run_with_default_batch(self, mock_get_container, mock_container):
        mock_get_container.return_value = mock_container
        mock_container.run_osm_night_watchman.execute.return_value = "Stróż skończył."

        result = run_osm_night_watchman_task()

        mock_container.run_osm_night_watchman.execute.assert_called_once_with(batch_size=50)
        assert result == "Stróż skończył."

    @patch("bootstrap.get_container")
    def test_successful_run_with_custom_batch(self, mock_get_container, mock_container):
        mock_get_container.return_value = mock_container

        result = run_osm_night_watchman_task(batch_size=10)

        mock_container.run_osm_night_watchman.execute.assert_called_once_with(batch_size=10)

    @patch("bootstrap.get_container")
    def test_exception_handling(self, mock_get_container, mock_container):
        mock_get_container.return_value = mock_container
        mock_container.run_osm_night_watchman.execute.side_effect = Exception("Watchman error")

        with pytest.raises(Exception):
            run_osm_night_watchman_task()


class TestRecalculatePoiScoresTask:
    @patch("bootstrap.get_container")
    def test_successful_recalculation(self, mock_get_container, mock_container):
        mock_get_container.return_value = mock_container

        result = recalculate_poi_scores_task(42)

        mock_container.poi_scoring_service.recalculate_and_cache_for_profile.assert_called_once_with(42)
        assert "Sukces" in result
        assert "42" in result

    @patch("bootstrap.get_container")
    def test_unexpected_error_logs_and_raises(self, mock_get_container, mock_container):
        mock_get_container.return_value = mock_container
        mock_container.poi_scoring_service.recalculate_and_cache_for_profile.side_effect = Exception("Unexpected")

        with pytest.raises(Exception, match="Unexpected"):
            recalculate_poi_scores_task(99)


class TestFetchBadgeNewsTask:
    @patch("bootstrap.get_container")
    def test_successful_fetch(self, mock_get_container, mock_container):
        mock_get_container.return_value = mock_container
        mock_container.fetch_badge_news.execute.return_value = 10

        result = fetch_badge_news_task()

        mock_container.fetch_badge_news.execute.assert_called_once()
        assert result == "10"

    @patch("bootstrap.get_container")
    def test_exception_handling(self, mock_get_container, mock_container):
        mock_get_container.return_value = mock_container
        mock_container.fetch_badge_news.execute.side_effect = Exception("News error")

        with pytest.raises(Exception):
            fetch_badge_news_task()
