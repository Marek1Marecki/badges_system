"""Data Transfer Objects (DTO) dla weryfikacji odznak."""

from pydantic import BaseModel

from application.dto.ascent_dto import AscentInputDTO


class VerifyBadgeRequestDTO(BaseModel):
    """Żądanie weryfikacji postępu zdobywania odznaki."""

    badge_code: str
    version_code: str
    ascents: list[AscentInputDTO]
