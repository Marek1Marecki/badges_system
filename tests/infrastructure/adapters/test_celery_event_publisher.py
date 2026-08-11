"""Testy dla CeleryEventPublisher."""

from unittest.mock import MagicMock, patch

import pytest

from domain.events import UserProgressStateChanged
from infrastructure.adapters.celery_event_publisher import CeleryEventPublisher


class TestCeleryEventPublisher:
    """Testy publikatora zdarzeń Celery."""

    def test_publishes_user_progress_event_eager(self):
        """Publikuje UserProgressStateChanged gdy CELERY_TASK_ALWAYS_EAGER=True."""
        publisher = CeleryEventPublisher()
        event = UserProgressStateChanged(profile_id=1)

        with patch("apps.badges.tasks.recalculate_poi_scores_task.delay") as mock_delay:
            with patch("django.conf.settings.CELERY_TASK_ALWAYS_EAGER", True):
                publisher.publish(event)

        mock_delay.assert_called_once_with(1)

    def test_publishes_user_progress_event_on_commit(self):
        """Publikuje zdarzenie po commicie gdy CELERY_TASK_ALWAYS_EAGER=False."""
        publisher = CeleryEventPublisher()
        event = UserProgressStateChanged(profile_id=42)

        with patch("apps.badges.tasks.recalculate_poi_scores_task.delay") as mock_delay:
            with patch("django.db.transaction.on_commit") as mock_on_commit:
                with patch("django.conf.settings.CELERY_TASK_ALWAYS_EAGER", False):
                    publisher.publish(event)

        mock_on_commit.assert_called_once()

    def test_non_user_progress_event_is_ignored(self):
        """Inne zdarzenia niż UserProgressStateChanged są ignorowane."""
        publisher = CeleryEventPublisher()

        other_event = MagicMock()
        other_event.__class__.__name__ = "SomeOtherEvent"

        publisher.publish(other_event)
