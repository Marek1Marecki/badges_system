"""Port dla Publikatora Zdarzeń Domenowych."""

from typing import Protocol

from domain.events import DomainEvent


class DomainEventPublisherPort(Protocol):
    """Abstrakcja infrastruktury powiadamiającej o zdarzeniach."""

    def publish(self, event: DomainEvent) -> None:
        """Publikuje zdarzenie (np.

        do message brokera, Celery lub na szynę lokalną).
                Args:
                  event: DomainEvent:
                  event: DomainEvent:

                Returns:
        """
        ...
