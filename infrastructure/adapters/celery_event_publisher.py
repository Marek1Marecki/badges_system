"""Publikator zdarzeń używający Celery jako szyny asynchronicznej.

Rejestruje także zdarzenia w tabeli `audit_log` (AUDYT-051), co pozwala
odtworzyć 'kto, kiedy, co' dla operacji krytycznych.
"""

from typing import Any

from django.conf import settings
from django.db import transaction

from application.ports.event_publisher_port import DomainEventPublisherPort
from domain.events import (
    AscentLogged,
    BadgeStatusChanged,
    DomainEvent,
    ProfileUpdated,
    UserProgressStateChanged,
)


def _persist_audit_log(action: str, target_type: str, target_id: str, payload: dict[str, Any]) -> None:
    """Zapisuje zdarzenie do tabeli `audit_log`.

    Oddzielona funkcja, by nie tworzyć zależności infrastruktury
    wewnątrz `domain/`.
    """
    from apps.tourists.models import AuditLog

    AuditLog.objects.create(
        actor_id=payload.get("actor_user_id"),
        action=action,
        target_type=target_type,
        target_id=target_id,
        payload=payload,
    )


class CeleryEventPublisher(DomainEventPublisherPort):
    """Tłumaczy czyste zdarzenia domenowe na konkretne taski Celery.

    Jednocześnie trwale zapisuje każde zdarzenie w `audit_log` (AUDYT-051).
    """

    def publish(self, event: DomainEvent) -> None:
        """Publikuje zdarzenie.

        Gwarantuje uruchomienie po commicie DB (lub natychmiast w testach).
        """
        if isinstance(event, UserProgressStateChanged):
            from apps.badges.tasks import recalculate_poi_scores_task

            if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
                recalculate_poi_scores_task.delay(event.profile_id)
            else:
                transaction.on_commit(lambda: recalculate_poi_scores_task.delay(event.profile_id))

        elif isinstance(event, BadgeStatusChanged):
            _persist_audit_log(
                action="BadgeStatusChanged",
                target_type="BadgeVersion",
                target_id=f"{event.badge_code}/{event.version_code}",
                payload={
                    "actor_user_id": event.actor_user_id,
                    "badge_code": event.badge_code,
                    "version_code": event.version_code,
                    "new_status": event.new_status,
                    "reason": event.reason,
                },
            )

        elif isinstance(event, AscentLogged):
            _persist_audit_log(
                action="AscentLogged",
                target_type="AscentLog",
                target_id=f"profile={event.actor_profile_id}/peak={event.peak_id}",
                payload={
                    "actor_profile_id": event.actor_profile_id,
                    "peak_id": event.peak_id,
                    "ascent_date": str(event.ascent_date),
                },
            )

        elif isinstance(event, ProfileUpdated):
            _persist_audit_log(
                action="ProfileUpdated",
                target_type="TouristProfile",
                target_id=str(event.target_profile_id),
                payload={
                    "actor_user_id": event.actor_user_id,
                    "target_profile_id": event.target_profile_id,
                    "changed_fields": list(event.changed_fields),
                },
            )
