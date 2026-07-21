"""Publikator zdarzeń używający Celery jako szyny asynchronicznej."""

from django.db import transaction

from application.ports.event_publisher_port import DomainEventPublisherPort
from domain.events import DomainEvent, UserProgressStateChanged


class CeleryEventPublisher(DomainEventPublisherPort):
    """Tłumaczy czyste zdarzenia domenowe na konkretne taski Celery."""

    def publish(self, event: DomainEvent) -> None:
        """Publikuje zdarzenie. Gwarantuje uruchomienie po commicie DB."""
        if isinstance(event, UserProgressStateChanged):
            # Leniwy import rozwiązuje błąd Circular Import w architekturze heksagonalnej
            from apps.badges.tasks import recalculate_poi_scores_task

            # Delegujemy przeliczanie punktów do tła, bezpiecznie po transakcji
            transaction.on_commit(lambda: recalculate_poi_scores_task.delay(event.profile_id))
