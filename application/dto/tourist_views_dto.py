"""Typed DTOs dla turystycznych widoków HTML (AUDYT-016 — QueryService Layer).

Use Case'y odczytowe zwracają te DTO zamiast surowych modeli Django,
osobiędzielając `apps.tourists.views` (Delivery) od `apps.badges.models`
Bounded Contextu słowników PTTK.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict


class BadgeCatalogEntryResponseDTO(BaseModel):
    """Jedna pozycja w katalogu odznak."""

    model_config = ConfigDict(frozen=True)

    id: int
    code: str
    name: str
    organizer_name: str
    current_version_id: int | None
    is_subscribed: bool
    domain_status: str
    badge: Any


class BadgeTierInfoDTO(BaseModel):
    """Tier z evaluation lub z DB (unifikowany interfejs dla HTML)."""

    model_config = ConfigDict(frozen=True)

    name: str
    required_count: int
    status: str
    image_url: str | None


class BadgeObjectDTO(BaseModel):
    """Obiekt w kolekcji odznaki (dla mapy szczytów)."""

    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    altitude: float | None
    score: float
    color: str


class BadgeDetailResponseDTO(BaseModel):
    """Szczegóły odznaki dla `badge_detail_view`."""

    model_config = ConfigDict(frozen=True)

    badge: Any
    progress: Any | None
    evaluation: dict[str, Any] | None
    objects_list: list[BadgeObjectDTO]
    target_version: Any | None
    tiers_info: list[BadgeTierInfoDTO]
    has_consent: bool


class ObjectRegionDTO(BaseModel):
    """Jedna pozycja regionu dla obiektu turystycznego."""

    model_config = ConfigDict(frozen=True)

    level: str
    name: str


class ObjectDetailResponseDTO(BaseModel):
    """Szczegóły obiektu turystycznego dla `object_detail_view`."""

    model_config = ConfigDict(frozen=True)

    obj: Any
    regions: list[ObjectRegionDTO]
    badges_list: list[dict[str, str]]
    score: float
    color: str
    ascents: list[Any]
    parent: Any | None
    children: list[Any]
    subscribed_badge_codes: list[str]


class RegionRankingEntryDTO(BaseModel):
    """Pozycja rankingu regionu."""

    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    type: str
    score: float
    color: str


class RegionContextResponseDTO(BaseModel):
    """Kontekst geograficzny regionu dla `region_detail_view`."""

    model_config = ConfigDict(frozen=True)

    region: Any
    region_level: str
    region_id: int
    extent: tuple[float, float, float, float] | None
    ranking_data: list[RegionRankingEntryDTO]
    total_objects: int
    parent_region: Any | None
    parent_level: str | None
    children_regions: list[Any]
    children_level: str | None
    neighbors: list[Any]


class OrganizerDetailResponseDTO(BaseModel):
    """Szczegóły organizatora dla `organizer_detail_view`.

    `organizer` to model ORM (`OrganizerModel`) — widok renderuje
    `{{ organizer }}` i `.badges.all()` bezpośrednio. DTO otacza go
    dla konsystencji z patternem DTO (AUDYT-016).
    """

    model_config = ConfigDict(frozen=True)

    organizer: Any
