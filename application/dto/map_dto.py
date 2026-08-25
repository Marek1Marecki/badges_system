"""Data Transfer Objects (DTO) dla widoków mapowych.

Zgodnie z ADR-013, chroni Czystą Domenę przed typami GIS z PostGIS. Współrzędne są przekazywane jako czyste wartości
zmiennoprzecinkowe (float).
"""

from pydantic import BaseModel, ConfigDict


class MapExploreRequestDTO(BaseModel):
    """Zwalidowane żądanie eksploracji mapy na zadanym obszarze (BBox)."""

    model_config = ConfigDict(frozen=True)

    profile_id: int
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    badge_code: str | None = None
    region_level: str | None = None
    region_id: int | None = None


class TouristObjectGeoDTO(BaseModel):
    """Reprezentuje płaski punkt na mapie zwrócony przez infrastrukturę (Adapter)."""

    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    type: str
    lon: float
    lat: float
