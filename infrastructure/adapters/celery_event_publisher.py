"""Publikator zdarzeń używający Celery jako szyny asynchronicznej."""

from django.conf import settings
from django.db import transaction

from application.ports.event_publisher_port import DomainEventPublisherPort
from domain.events import DomainEvent, UserProgressStateChanged


class CeleryEventPublisher(DomainEventPublisherPort):
    """Tłumaczy czyste zdarzenia domenowe na konkretne taski Celery."""

    def publish(self, event: DomainEvent) -> None:
        """Publikuje zdarzenie.

        Gwarantuje uruchomienie po commicie DB (lub natychmiast w testach).
                Args:
                  event: DomainEvent:
                  event: DomainEvent:

                Returns:
        """
        if isinstance(event, UserProgressStateChanged):
            from apps.badges.tasks import recalculate_poi_scores_task

            if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
                recalculate_poi_scores_task.delay(event.profile_id)
            else:
                transaction.on_commit(lambda: recalculate_poi_scores_task.delay(event.profile_id))
