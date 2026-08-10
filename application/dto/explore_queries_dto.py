"""Modele odczytu (DTO) dla widoków eksploracji i rankingów."""

from pydantic import BaseModel, ConfigDict


class BadgeCodeNameDTO(BaseModel):
    """Mały obiekt odznaki do linkowania na frontendzie."""

    code: str
    name: str


class RankingItemDTO(BaseModel):
    """Pojedynczy element rankingu (szczyt lub zsumowany klaster)."""

    model_config = ConfigDict(frozen=True)

    is_family: bool
    cluster_score: int
    cluster_id: int | None
    cluster_name: str | None
    items: list[dict]  # Lista słowników reprezentujących dzieci (szczyty/schroniska)


class RegionRankingItemDTO(BaseModel):
    """Pojedynczy element rankingu regionów."""

    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    score: int
    level: str


class PoiRankingResponseDTO(BaseModel):
    """Całkowity stan dla widoku Rankingu Celów."""

    model_config = ConfigDict(frozen=True)

    active_progresses: list[dict]
    subscribed_badge_codes: list[str]
    ranking: list[RankingItemDTO]


class RegionRankingResponseDTO(BaseModel):
    """Całkowity stan dla widoku Rankingu Regionów."""

    model_config = ConfigDict(frozen=True)

    level: str
    ranking: list[RegionRankingItemDTO]
