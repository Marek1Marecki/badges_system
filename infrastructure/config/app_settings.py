"""Konfiguracja aplikacji — jedyne miejsce odczytu zmiennych środowiskowych.

Zgodnie z 20-configuration-contract.md:
- os.getenv() wyłącznie tutaj, nigdy w domain/ ani application/
- AppSettings waliduje i dostarcza gotowe wartości do bootstrap/
- pydantic-settings obsługuje .env, zmienne środowiskowe i walidację typów
"""

import os

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Jedyne dozwolone os.getenv w infrastructure/ — wybór pliku .env per środowisko.
# Na produkcji sekrety są wstrzykiwane przez env kontenera, plik nie istnieje.
_env_file = os.getenv("ENV_FILE", ".env")


class AppSettings(BaseSettings):
    """Centralna konfiguracja aplikacji.

    Wczytuje zmienne z pliku .env (lub ENV_FILE) oraz ze środowiska kontenera.
    Przy braku pliku nie rzuca błędu — produkcja dostarcza wartości przez env.
    Błąd brakującej wymaganej zmiennej jest wykrywany przy starcie aplikacji.
    """

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ------------------------------------------------------------------
    # Django
    # ------------------------------------------------------------------
    secret_key: str
    debug: bool = False
    allowed_hosts: str = "localhost,127.0.0.1"
    app_env: str = "development"

    # ------------------------------------------------------------------
    # Baza danych (PostGIS)
    # ------------------------------------------------------------------
    database_url: str

    # ------------------------------------------------------------------
    # Celery / Redis
    # ------------------------------------------------------------------
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # ------------------------------------------------------------------
    # OSM / Overpass
    # ------------------------------------------------------------------
    overpass_api_url: str = "https://overpass-api.de/api/interpreter"
    overpass_timeout_seconds: int = 30

    # ------------------------------------------------------------------
    # Logowanie
    # ------------------------------------------------------------------
    log_level: str = "INFO"
    log_json: bool = False  # True na produkcji → JSON dla ELK/Loki

    # ------------------------------------------------------------------
    # Feature flags
    # ------------------------------------------------------------------
    feature_osm_night_watchman: bool = True
    feature_proximity_scan: bool = True

    # ------------------------------------------------------------------
    # Walidatory
    # ------------------------------------------------------------------
    @model_validator(mode="after")
    def debug_not_in_production(self) -> AppSettings:
        """Blokuje debug=True na produkcji."""
        if self.debug and self.app_env == "production":
            raise ValueError("debug=True jest zakazany w środowisku produkcyjnym")
        return self

    @field_validator("log_level")
    @classmethod
    def valid_log_level(cls, v: str) -> str:
        """Waliduje poziom logowania."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"log_level musi być jednym z: {allowed}")
        return upper

    # ------------------------------------------------------------------
    # Autoryzacja i OAuth
    # ------------------------------------------------------------------
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""

    mapy_cz_api_key: str = ""
