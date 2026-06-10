"""Kontekst weryfikacyjny dla Czystej Domeny.

Zgodnie z INVARIANTS.md (T-02) i modelem domenowym, ten obiekt
wstrzykuje stan turysty i czasu do bezstanowych reguł biznesowych.
"""

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True)
class VerificationContext:
    """Stan zewnętrzny (Turysta + Czas) przekazywany do ewaluacji reguł."""

    evaluation_time: datetime
    tourist_birth_date: date | None = None
    club_join_dates: dict[str, date] = field(default_factory=dict)

    # Kody odznak, które turysta ma w statusie COMPLETED (dla PrerequisiteBadgeRule)
    completed_badge_codes: frozenset[str] = field(default_factory=frozenset)
