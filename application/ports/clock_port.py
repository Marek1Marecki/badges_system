"""Port dla dostawcy czasu — zgodnie z 17-determinism-contract.md.

Zamiast wywoływać datetime.now() bezpośrednio w logice biznesowej,
use case'y otrzymują implementację tego portu przez konstruktor.
Pozwala to na pełną kontrolę czasu w testach (FakeClock).
"""

from datetime import datetime
from typing import Protocol


class ClockPort(Protocol):
    """Interfejs dostawcy aktualnego czasu."""

    def now(self) -> datetime:
        """Zwraca aktualny czas jako obiekt datetime ze strefą czasową."""
        ...
