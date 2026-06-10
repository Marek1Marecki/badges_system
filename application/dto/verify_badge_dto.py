"""Data Transfer Objects (DTO) dla weryfikacji odznak."""

from pydantic import BaseModel


class VerifyBadgeRequestDTO(BaseModel):
    """Żądanie weryfikacji postępu zdobywania odznaki."""

    user_id: int
    badge_code: str
    cycle_number: int = 1
