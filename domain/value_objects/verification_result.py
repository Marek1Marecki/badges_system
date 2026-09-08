"""Obiekty Wynikowe (Value Objects) dla procesu weryfikacji odznak."""

from dataclasses import dataclass, field

from domain.value_objects.ascent_status import AscentStatus


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
    # AUDYT-099: Pełny raport każdego wejścia + jego status (ACTIVE/ORPHANED)
    ascents_with_status: list[AscentStatus] = field(default_factory=list)
