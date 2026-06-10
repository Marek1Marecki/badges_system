"""Obiekty wartości (Value Objects) dla logów wejść turysty."""

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Ascent:
    """Fakt historyczny: Reprezentuje pojedyncze wejście na szczyt (wycieczkę)."""

    peak_id: int
    ascent_date: date
    # Zgodnie z ADR-012 i R-03: płaskie ID regionów z CQRS
    region_ids: frozenset[int] = field(default_factory=frozenset)
