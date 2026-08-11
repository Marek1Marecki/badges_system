"""Konfiguracja aplikacji — jedyne miejsce odczytu zmiennych środowiskowych.

Zgodnie z 20-configuration-contract.md:
- os.getenv() wyłącznie tutaj, nigdy w domain/ ani application/
- AppSettings waliduje i dostarcza gotowe wartości do bootstrap/
- pydantic-settings obsługuje .env, zmienne środowiskowe i walidację typów
"""

import os
from typing import Any
from urllib.parse import quote_plus

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Mechanizm ochronny z Audytu: Zabezpieczamy się przed wczytaniem produkcyjnych haseł w DEV
# Jeśli zmienna ENV_FILE nie została podana z zewnątrz (np. przez Makefile / Docker),
# domyślnie używamy środowiska deweloperskiego.
_env_file = os.getenv("ENV_FILE", ".env.dev")


class AppSettings(BaseSettings):
    """Centralne ustawienia aplikacji pobierane ze zmiennych środowiskowych."""

    model_config = SettingsConfigDict(
        # Czyta najpierw zmienne współdzielone, a potem nadpisuje je specyficznymi dla środowiska.
        env_file=(".env.shared", _env_file),
        env_file_encoding="utf-8",
        # env_file_required=False,
        extra="ignore",
    )

    # --- KONFIGURACJA PODSTAWOWA ---
    app_env: str = "development"
    debug: bool = False
    secret_key: str = "unsafe-default-key-for-dev-only-do-not-use"  # noqa: S105
    language_code: str = "pl"
    time_zone: str = "Europe/Warsaw"

    # Przechwytuje zmienną ALLOWED_HOSTS z pliku środowiskowego jako ciąg (np. "mojadomena.pl,www.mojadomena.pl")
    allowed_hosts_str: str = Field(default="", validation_alias="ALLOWED_HOSTS")

    # --- BAZA DANYCH ---
    postgres_user: str = "postgres"
    postgres_password: str = "password"  # noqa: S105
    postgres_db: str = "badges_system_db"
    postgres_host: str = Field(default="localhost")
    postgres_port: int = 5432

    # --- REDIS / CELERY ---
    redis_host: str = "redis"
    redis_port: int = 6379

    # --- AUTORYZACJA, OAUTH I ZEWNĘTRZNE API ---
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    mapy_cz_api_key: str = ""

    # --- KONFIGURACJA LOGÓW I INFRASTRUKTURY ---
    log_level: str = "INFO"
    log_json: bool = False

    # Timeout dla zewnętrznych strzałów do OSM API (w sekundach)
    overpass_timeout_seconds: int = 30

    # --- FEATURE FLAGS ---
    feature_proximity_scan: bool = True
    feature_osm_night_watchman: bool = True
    feature_new_dashboard: bool = False
    feature_export_pdf: bool = False

    # === WŁAŚCIWOŚCI WYLICZANE (Czysty Python, omijamy konflikty Pydantic v2) ===

    @property
    def database_url(self) -> str:
        """Automatycznie kompiluje pełny ciąg DSN (bezpieczne ze znakami specjalnymi)."""
        pwd = quote_plus(self.postgres_password)
        return f"postgis://{self.postgres_user}:{pwd}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def celery_broker_url(self) -> str:
        """Kompiluje URL do połączenia z Redisem."""
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    @property
    def celery_result_backend(self) -> str:
        """Kompiluje URL do składowania wyników Celery w Redis."""
        return f"redis://{self.redis_host}:{self.redis_port}/1"

    # --- WALIDATORY PYDANTIC (Przywrócenie logiki testowanej przez pytest) ---

    @field_validator("debug", mode="before")
    @classmethod
    def validate_debug(cls, v: Any) -> Any:
        """Mapuje niestandardowe wartości DEBUG (np. 'release') na boolean."""
        if isinstance(v, str) and v.strip().lower() == "release":
            return False
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Wymusza, by poziom logów był zawsze pisany dużymi literami i dozwolony."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper_v = v.upper()
        if upper_v not in valid_levels:
            raise ValueError(f"Nieprawidłowy poziom logowania: {v}. Dozwolone: {valid_levels}")
        return upper_v

    @model_validator(mode="after")
    def validate_debug_in_production(self):
        """Zabezpieczenie przed wyciekiem DEBUG=True na środowisko produkcyjne."""
        if self.app_env == "production" and self.debug is True:
            raise ValueError("debug=True jest zakazany")
        return self
