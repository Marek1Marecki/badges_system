"""Data Transfer Object (DTO) dla relacji regionalnych obiektu (CQRS)."""

from pydantic import BaseModel, ConfigDict


class ObjectRegionDTO(BaseModel):
    """Reprezentuje płaską relację pomiędzy obiektem turystycznym a regionem PTTK."""

    model_config = ConfigDict(frozen=True)

    object_id: int
    region_id: int
    region_level: str
    distance_meters: float
