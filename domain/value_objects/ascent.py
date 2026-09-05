"""Obiekty wartości (Value Objects) dla logów wejść turysty."""

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Ascent:
    """Fakt historyczny: Reprezentuje pojedyncze wejście na obiekt turystyczny (wejście)."""

    object_id: int
    ascent_date: date
    region_ids: frozenset[int] = field(default_factory=frozenset)
