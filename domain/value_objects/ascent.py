"""Wartości domenowe dla systemu odznak."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Ascent:
    """Fakt historyczny: Reprezentuje pojedyncze wejście na szczyt. Value Object."""

    peak_id: int
    ascent_date: date
