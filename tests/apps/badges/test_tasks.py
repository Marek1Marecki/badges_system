"""Testy dla zadań Celery.

Po refaktoryzacji tasks.py jest cienkim wrapperem — mockujemy metody
repozytoriów i use case'ów, nie ORM bezpośrednio.

Wzorzec testowania:
- patch na metodach repozytorium (infrastructure/adapters/)
- weryfikacja że task wywołuje use case z poprawnymi argumentami
- weryfikacja komunikatów zwrotnych
"""

from unittest.mock import MagicMock, patch

import pytest

from apps.badges.tasks import (
    fetch_badge_news_task,
    recalculate_poi_scores_task,
)

# ---------------------------------------------------------------------------
# TestRecalculatePoiScoresTask
# ---------------------------------------------------------------------------


class TestRecalculatePoiScoresTask:
    """Testy zadania recalculate_poi_scores_task."""

    def test_successful_recalculation(self) -> None:
        """Task z sukcesem wywołuje serwis z profile_id i zwraca komunikat."""

        with patch("bootstrap.get_container") as mock_get_container:
            mock_container = MagicMock()
            mock_service = MagicMock()
            mock_container.poi_scoring_service = mock_service
            mock_get_container.return_value = mock_container

            result = recalculate_poi_scores_task.__wrapped__(profile_id=1)

        assert "Sukces" in result
        assert "1" in result
        mock_service.recalculate_and_cache_for_profile.assert_called_once_with(1)

    def test_unexpected_error_logs_and_raises(self) -> None:
        """W przypadku awarii, task loguje błąd i propaguje wyjątek."""

        with (
            patch("bootstrap.get_container") as mock_get_container,
            patch("apps.badges.tasks.logger") as mock_logger,
        ):
            mock_container = MagicMock()
            mock_service = MagicMock()
            mock_service.recalculate_and_cache_for_profile.side_effect = Exception("Redis padł")
            mock_container.poi_scoring_service = mock_service
            mock_get_container.return_value = mock_container

            with pytest.raises(Exception, match="Redis padł"):
                recalculate_poi_scores_task.__wrapped__(profile_id=1)

            mock_logger.error.assert_called_once()
            assert "Nieoczekiwany błąd w recalculate_poi_scores_task" in mock_logger.error.call_args[0][0]

    def test_request_id_propagated_to_logs(self) -> None:
        """AUDYT-117: request_id z ContextVar łączy logi Celery z HTTP.

        Po refaktoryzacji ContextVar jest ustawiany w middleware HTTP /
        task_prerun hook (z headers Celery), a task go odczytuje
        bez dostępu do self.request — czyste dla testów.
        """
        from infrastructure.request_context import set_request_id

        with (
            patch("bootstrap.get_container") as mock_get_container,
            patch("apps.badges.tasks.logger") as mock_logger,
        ):
            mock_container = MagicMock()
            mock_service = MagicMock()
            mock_container.poi_scoring_service = mock_service
            mock_get_container.return_value = mock_container

            mock_logger.contextualize = MagicMock(return_value=mock_logger)

            set_request_id("req_abc123")
            try:
                recalculate_poi_scores_task.__wrapped__(profile_id=1)
            finally:
                set_request_id(None)

            assert mock_logger.contextualize.call_args.kwargs.get("request_id") == "req_abc123"


# ---------------------------------------------------------------------------
# TestFetchBadgeNewsTask
# ---------------------------------------------------------------------------


class TestFetchBadgeNewsTask:
    """Testy zadania fetch_badge_news_task."""

    def test_successful_fetch(self) -> None:
        """Task pobiera newsy i zwraca wynik."""
        with patch("bootstrap.get_container") as mock_get_container:
            mock_container = MagicMock()
            mock_use_case = MagicMock()
            mock_use_case.execute.return_value = "Pobrano 5 newsów"
            mock_container.fetch_badge_news = mock_use_case
            mock_get_container.return_value = mock_container

            result = fetch_badge_news_task()

        assert result == "Pobrano 5 newsów"
        mock_use_case.execute.assert_called_once()

    def test_exception_handling(self) -> None:
        """Task loguje błąd i rzuca wyjątek."""
        with patch("bootstrap.get_container") as mock_get_container:
            mock_container = MagicMock()
            mock_use_case = MagicMock()
            mock_use_case.execute.side_effect = Exception("News error")
            mock_container.fetch_badge_news = mock_use_case
            mock_get_container.return_value = mock_container

            try:
                fetch_badge_news_task()
            except Exception as e:
                assert "News error" in str(e)
