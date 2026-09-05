"""Zdarzenia domenowe (Domain Events).

Opisują fakty, które zaszły w systemie. Służą do asynchronicznego powiadamiania infrastruktury (np. odpalania przeliczeń
w Celery) bez sprzęgania z nią warstwy domeny i aplikacji.
"""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DomainEvent:
    """Bazowa klasa dla wszystkich zdarzeń domenowych."""

    pass


@dataclass(frozen=True)
class UserProgressStateChanged(DomainEvent):
    """Zdarzenie emitowane, gdy stan postępów turysty ulegnie zmianie.

    Wyzwalane m.in. po dodaniu logu wejścia, usunięciu logu, lub zmianie subskrybowanych odznak.
    """

    profile_id: int


@dataclass(frozen=True)
class AscentLogged(DomainEvent):
    """Zdarzenie audytowe: turysta zalogował wejście.

    Używane przez AUDYT-051 (audit log) oraz AUDYT-051 jako część śladu zmian.
    """

    actor_profile_id: int
    object_id: int
    ascent_date: date


@dataclass(frozen=True)
class BadgeStatusChanged(DomainEvent):
    """Zdarzenie audytowe: weryfikator PTTK zmienił status odznaki.

    Chroni przed nieautoryzowanymi cofnięciami (AUDYT-051 — kto, kiedy, co).
    """

    actor_user_id: int
    badge_code: str
    version_code: str
    new_status: str
    reason: str


@dataclass(frozen=True)
class ProfileUpdated(DomainEvent):
    """Zdarzenie audytowe: profil turysty został zmodyfikowany.

    Emisja od `TouristProfileAggregate` (AUDYT-037) — np. zmiana nicka, planu.
    `changed_fields` = zbiór nazw polów, które uległy zmianie.
    """

    actor_user_id: int
    target_profile_id: int
    changed_fields: tuple[str, ...]
