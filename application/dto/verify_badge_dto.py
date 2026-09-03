"""Data Transfer Objects (DTO) dla weryfikacji odznak.

AUDYT-124: Zastosowanie rigorystycznego DTO dla wyjść Use Case'ów,
zastępując luźne `dict[str, Any]` (Primitive Obsession).
"""

from pydantic import BaseModel, Field


class VerifyBadgeRequestDTO(BaseModel):
    """Żądanie weryfikacji postępu zdobywania odznaki."""

    profile_id: int
    badge_code: str
    cycle_number: int = 1


class TierResultResponseDTO(BaseModel):
    """Wynik weryfikacji dla jednego stopnia odznaki."""

    tier_id: int
    name: str
    status: str
    required_count: int


class VerifyBadgeResponseDTO(BaseModel):
    """Wynik weryfikacji odznaki (typowany OutputDTO — AUDYT-124).

    Zamienia luźny słownik zwracany przez `EvaluateBadgeProgressQuery`
    na rygorystyczny obiekt `BaseModel`, co zapewnia:
    - Mypy widzi kształt odpowiedzi API
    - Swagger/OpenAPI generuje się automatycznie
    - Frontend ma statyczny kontrakt
    """

    verified: bool
    status: str
    valid_ascents_count: int
    errors: list[str] = Field(default_factory=list)
    tiers: list[TierResultResponseDTO] = Field(default_factory=list)
