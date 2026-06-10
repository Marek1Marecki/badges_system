"""Data Transfer Objects (DTO) dla wejść użytkownika."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from domain.value_objects.ascent import Ascent


class AscentDTO(BaseModel):
    """Zhydrowany snapshot wejścia turysty używany przez porty aplikacyjne.

    `region_ids` są płaskimi ID z CQRS, dzięki czemu przyszłe reguły wildcard
    mogą działać bez importowania GIS lub odpytywania infrastruktury w domenie.
    """

    model_config = ConfigDict(frozen=True)

    peak_id: int = Field(gt=0)
    ascent_date: date
    region_ids: frozenset[int] = Field(default_factory=frozenset)

    def to_domain(self) -> Ascent:
        """Konwertuje snapshot na Value Object rozumiany przez obecną domenę."""
        return Ascent(
            peak_id=self.peak_id,
            ascent_date=self.ascent_date,
            region_ids=self.region_ids,  # <--- DODANO PRZEKAZYWANIE REGIONÓW
        )


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
