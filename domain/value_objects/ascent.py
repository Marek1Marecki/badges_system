"""Wartości domenowe dla systemu odznak."""

from dataclasses import dataclass
from datetime import date
from enum import Enum


class ActivityType(Enum):
    """Typy dozwolonych aktywności górskich."""

    HIKING = "HIKING"
    CYCLING = "CYCLING"
    SKIING = "SKIING"


@dataclass(frozen=True)
class Ascent:
    """Fakt historyczny: Wejście na szczyt. Value Object."""

    peak_id: int
    ascent_date: date
    activity: ActivityType
