"""Zdarzenia domenowe (Domain Events).

Opisują fakty, które zaszły w systemie. Służą do asynchronicznego powiadamiania infrastruktury (np. odpalania przeliczeń
w Celery) bez sprzęgania z nią warstwy domeny i aplikacji.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DomainEvent:
    """Bazowa klasa dla wszystkich zdarzeń domenowych."""

    pass


@dataclass(frozen=True)
class UserProgressStateChanged(DomainEvent):
    """Zdarzenie emitowane, gdy stan postępów turysty ulegnie zmianie.

    Wyzwalane m.in. po dodaniu logu wejścia, usunięciu logu, lub
    zmianie subskrybowanych odznak.

    Args:

    Returns:
    """

    profile_id: int
