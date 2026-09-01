"""Data Transfer Objects (DTO) dla widoków mapowych.

Zgodnie z ADR-013, chroni Czystą Domenę przed typami GIS z PostGIS. Współrzędne są przekazywane jako czyste wartości
zmiennoprzecinkowe (float).
"""

from pydantic import BaseModel, ConfigDict, Field


class MapExploreRequestDTO(BaseModel):
    """Zwalidowane żądanie eksploracji mapy na zadanym obszarze (BBox).

    AUDYT-049: wymusza bezwzględny zakres geograficzny, by zapobiec
    atakowi DoS przez fałszywy wektor bbox (np. ``-999,-999,999,999``).
    Pydantic odrzuca poza zakresem jeszcze przed dotarciem do PostGIS.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    profile_id: int
    min_lon: float = Field(ge=-180, le=180)
    min_lat: float = Field(ge=-90, le=90)
    max_lon: float = Field(ge=-180, le=180)
    max_lat: float = Field(ge=-90, le=90)

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
