"""Obiekty wartości (Value Objects) dla logów wejść turysty."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Ascent:
    """Fakt historyczny: Reprezentuje pojedyncze wejście na szczyt (wycieczkę)."""

    peak_id: int
    ascent_date: date
