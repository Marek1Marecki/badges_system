"""Data Transfer Objects (DTO) dla wejść użytkownika."""

from datetime import date

from pydantic import BaseModel, Field

from domain.value_objects.ascent import Ascent


class AscentInputDTO(BaseModel):
    """Waliduje dane logu wejścia pochodzące z zewnątrz (np. formularza/API)."""

    peak_id: int = Field(gt=0)
    ascent_date: date

    def to_domain(self) -> Ascent:
        """Konwertuje zwalidowane DTO na Value Object z warstwy domeny."""
        return Ascent(
            peak_id=self.peak_id,
            ascent_date=self.ascent_date,
        )


class VerifyBadgeRequestDTO(BaseModel):
    """Żądanie weryfikacji postępu zdobywania odznaki."""

    badge_code: str
    version_code: str
    ascents: list[AscentInputDTO]
