"""Data Transfer Objects dla kontekstu użytkownika i subskrypcji.

Zgodnie z zasadą Domain Purity, domena nie może odpytywać bazy o profil użytkownika.
Te DTO służą do transportu danych z infrastruktury do Use Case'ów.
"""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class TouristProfileDTO(BaseModel):
    """Zunifikowany profil turysty (Konto Rodzinne + Profil + Limity)."""

    model_config = ConfigDict(frozen=True)

    profile_id: int  # <--- ZMIANA
    is_main_profile: bool  # <--- ZMIANA
    email: str
    nickname: str
    birth_date: date | None = None

    # Słownik: Kod Organizatora/Klubu -> Data dołączenia
    club_join_dates: dict[str, date] = Field(default_factory=dict)

    # System Quota (Freemium)
    active_plan: str
    max_photos_per_ascent: int
    max_active_badges: int


class BadgeProgressDTO(BaseModel):
    """Snapshot stanu zdobywania danej odznaki przez turystę."""

    model_config = ConfigDict(frozen=True)

    progress_id: int
    profile_id: int  # <--- ZMIANA
    badge_code: str
    version_id: int | None
    cycle_number: int

    # Stany Domenowe (Matematyczne)
    domain_status: str  # np. 'NOT_STARTED', 'IN_PROGRESS', 'COMPLETED'

    # Stany Logistyczne (Osobisty Kanban)
    logistic_status: str | None  # np. 'WAITING_FOR_VERIFICATION', 'ALBUM'
    logistic_status_date: date | None


class LogisticStatusUpdateDTO(BaseModel):
    """Waliduje żądanie zmiany statusu logistycznego odznaki przez turystę."""

    logistic_status: str
    status_date: date


class UpdateProfileRequestDTO(BaseModel):
    """Waliduje dane aktualizacji profilu przez API."""

    nickname: str | None = None
    birth_date: date | None = None
    preferred_base_map: str | None = None
