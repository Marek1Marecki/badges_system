"""Obiekty Wynikowe (Value Objects) dla procesu weryfikacji odznak."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TierResult:
    """Reprezentuje wynik ewaluacji dla konkretnego stopnia odznaki."""

    tier_id: int
    name: str
    status: str  # np. "COMPLETED", "IN_PROGRESS", "NOT_STARTED"
    required_count: int


@dataclass(frozen=True)
class VerificationResult:
    """Reprezentuje pełny wynik ewaluacji całej odznaki."""

    verified: bool
    status: str  # np. "COMPLETED", "IN_PROGRESS", "NOT_STARTED"
    valid_ascents_count: int
    errors: list[str] = field(default_factory=list)
    tiers: list[TierResult] = field(default_factory=list)
