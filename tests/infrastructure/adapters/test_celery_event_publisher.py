"""Testy dla CeleryEventPublisher."""

from datetime import date
from unittest.mock import MagicMock, patch

from domain.events import AscentLogged, BadgeStatusChanged, ProfileUpdated, UserProgressStateChanged
from infrastructure.adapters.celery_event_publisher import CeleryEventPublisher


class TestCeleryEventPublisher:
    """Testy publikatora zdarzeń Celery."""

    def test_publishes_user_progress_event_eager(self) -> None:
        """Publikuje UserProgressStateChanged gdy CELERY_TASK_ALWAYS_EAGER=True."""
        publisher = CeleryEventPublisher()
        event = UserProgressStateChanged(profile_id=1)

        with patch("celery.current_app.send_task") as mock_send:
            with patch("django.conf.settings.CELERY_TASK_ALWAYS_EAGER", True):
                publisher.publish(event)

        mock_send.assert_called_once_with(
            "apps.badges.tasks.recalculate_poi_scores_task", args=[1]
        )

    def test_publishes_user_progress_event_on_commit(self) -> None:
        """Publikuje zdarzenie po commicie gdy CELERY_TASK_ALWAYS_EAGER=False."""
        publisher = CeleryEventPublisher()
        event = UserProgressStateChanged(profile_id=42)

        with patch("celery.current_app.send_task") as mock_send:
            with patch("django.db.transaction.on_commit") as mock_on_commit:
                with patch("django.conf.settings.CELERY_TASK_ALWAYS_EAGER", False):
                    publisher.publish(event)

        mock_on_commit.assert_called_once()
        mock_send.assert_not_called()

    def test_non_user_progress_event_is_ignored(self) -> None:
        """Inne zdarzenia niż UserProgressStateChanged są ignorowane."""
        publisher = CeleryEventPublisher()

        other_event = MagicMock()
        other_event.__class__.__name__ = "SomeOtherEvent"

        publisher.publish(other_event)

    def test_badge_status_changed_persists_audit_log(self) -> None:
        """BadgeStatusChanged zapisuje rekord AuditLog (AUDYT-051)."""
        publisher = CeleryEventPublisher()
        event = BadgeStatusChanged(
            actor_user_id=7,
            badge_code="KGP",
            version_code="v1",
            new_status="COMPLETED",
            reason="manual override",
        )

        with patch("apps.tourists.models.AuditLog.objects.create") as mock_create:
            publisher.publish(event)

        mock_create.assert_called_once_with(
            actor_id=7,
            action="BadgeStatusChanged",
            target_type="BadgeVersion",
            target_id="KGP/v1",
            payload={
                "actor_user_id": 7,
                "badge_code": "KGP",
                "version_code": "v1",
                "new_status": "COMPLETED",
                "reason": "manual override",
            },
        )

    def test_ascent_logged_persists_audit_log(self) -> None:
        """AscentLogged zapisuje rekord AuditLog (AUDYT-051)."""
        publisher = CeleryEventPublisher()
        event = AscentLogged(
            actor_profile_id=3,
            peak_id=42,
            ascent_date=date(2024, 6, 15),
        )

        with patch("apps.tourists.models.AuditLog.objects.create") as mock_create:
            publisher.publish(event)

        mock_create.assert_called_once_with(
            actor_id=None,
            action="AscentLogged",
            target_type="AscentLog",
            target_id="profile=3/peak=42",
            payload={
                "actor_profile_id": 3,
                "peak_id": 42,
                "ascent_date": "2024-06-15",
            },
        )

    def test_profile_updated_persists_audit_log(self) -> None:
        """ProfileUpdated zapisuje rekord AuditLog z listą zmienionych pól (AUDYT-037/051)."""
        publisher = CeleryEventPublisher()
        event = ProfileUpdated(
            actor_user_id=1,
            target_profile_id=9,
            changed_fields=("nickname", "preferred_base_map"),
        )

        with patch("apps.tourists.models.AuditLog.objects.create") as mock_create:
            publisher.publish(event)

        mock_create.assert_called_once_with(
            actor_id=1,
            action="ProfileUpdated",
            target_type="TouristProfile",
            target_id="9",
            payload={
                "actor_user_id": 1,
                "target_profile_id": 9,
                "changed_fields": ["nickname", "preferred_base_map"],
            },
        )
