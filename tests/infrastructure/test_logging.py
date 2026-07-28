"""Testy jednostkowe dla AppSettings.

Zgodnie z 20-configuration-contract.md:
- Testy nie czytają .env — używają jawnych wartości przez konstruktor
- Weryfikujemy walidatory (debug na produkcji, log_level)
- Weryfikujemy wartości domyślne
"""

import pytest

from infrastructure.config import AppSettings

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_MINIMAL = {
    "secret_key": "test-secret-key-not-for-production-min-50-chars-padding",
    "database_url": "postgresql+psycopg://test:test@localhost:5432/test_db",
}


# ---------------------------------------------------------------------------
# Wartości domyślne
# ---------------------------------------------------------------------------


def test_default_debug_is_false(monkeypatch) -> None:
    # Izolujemy od terminala
    monkeypatch.delenv("DEBUG", raising=False)
    # Przekazujemy _env_file=None ORAZ Twoje piękne minimalne dane wejściowe
    settings = AppSettings(_env_file=None, **VALID_MINIMAL)
    assert settings.debug is False


def test_default_app_env_is_development(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("ENV_FILE", ".env.dummy_nonexistent")

    from infrastructure.config.app_settings import AppSettings

    settings = AppSettings()

    assert settings.app_env == "development"


def test_default_log_level_is_info() -> None:
    settings = AppSettings(_env_file=None, **VALID_MINIMAL)
    assert settings.log_level == "INFO"


def test_default_log_json_is_false() -> None:
    settings = AppSettings(**VALID_MINIMAL)
    assert settings.log_json is False


def test_default_overpass_timeout() -> None:
    settings = AppSettings(_env_file=None, **VALID_MINIMAL)
    assert settings.overpass_timeout_seconds == 30


# ---------------------------------------------------------------------------
# Walidator: debug na produkcji
# ---------------------------------------------------------------------------


def test_debug_true_in_production_raises() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="debug=True jest zakazany"):
        AppSettings(**VALID_MINIMAL, debug=True, app_env="production")


def test_debug_true_in_development_is_allowed() -> None:
    settings = AppSettings(**VALID_MINIMAL, debug=True, app_env="development")
    assert settings.debug is True


def test_debug_false_in_production_is_allowed() -> None:
    settings = AppSettings(**VALID_MINIMAL, debug=False, app_env="production")
    assert settings.debug is False


# ---------------------------------------------------------------------------
# Walidator: log_level
# ---------------------------------------------------------------------------


def test_log_level_is_normalized_to_uppercase() -> None:
    settings = AppSettings(**VALID_MINIMAL, log_level="debug")
    assert settings.log_level == "DEBUG"


def test_invalid_log_level_raises() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        AppSettings(**VALID_MINIMAL, log_level="VERBOSE")


@pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
def test_all_valid_log_levels_are_accepted(level: str) -> None:
    settings = AppSettings(**VALID_MINIMAL, log_level=level)
    assert settings.log_level == level


# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------


def test_feature_flags_default_to_true() -> None:
    settings = AppSettings(**VALID_MINIMAL)
    assert settings.feature_osm_night_watchman is True
    assert settings.feature_proximity_scan is True


def test_feature_flags_can_be_disabled() -> None:
    settings = AppSettings(
        **VALID_MINIMAL,
        feature_osm_night_watchman=False,
        feature_proximity_scan=False,
    )
    assert settings.feature_osm_night_watchman is False
    assert settings.feature_proximity_scan is False
