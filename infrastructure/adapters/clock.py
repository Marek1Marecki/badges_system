"""Produkcyjna implementacja ClockPort.

Używa django.utils.timezone.now() zamiast datetime.now(), bo aplikacja korzysta z Django i USE_TZ=True — timezone.now()
zawsze zwraca datetime ze strefą UTC niezależnie od ustawień systemu operacyjnego.
"""

from datetime import datetime

from django.utils import timezone


class SystemClock:
    """Produkcyjny dostawca czasu — zwraca aktualny czas UTC z Django."""

    def now(self) -> datetime:
        """Zwraca aktualny czas jako datetime ze strefą UTC."""
        result: datetime = timezone.now()
        return result
