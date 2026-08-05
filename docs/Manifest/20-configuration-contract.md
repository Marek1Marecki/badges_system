# Configuration Contract

**Status:** Egzekwowalny  
**Zakres:** Wszystkie projekty Python

---

## Filozofia

Konfiguracja to szczegół infrastrukturalny. Domena i logika aplikacji nie wiedzą skąd pochodzi wartość konfiguracyjna — otrzymują ją przez dependency injection z warstwy bootstrap.

**Zasada:** `os.getenv()` wyłącznie w warstwie bootstrap. Pozostałe warstwy otrzymują gotowe wartości.

---

## Standard: pydantic-settings

`pydantic-settings` jest standardem zarządzania konfiguracją dla wszystkich projektów z zewnętrznymi zmiennymi środowiskowymi.

**Uzasadnienie:** Pydantic-settings łączy trzy rzeczy w jednym miejscu — odczyt zmiennych środowiskowych, walidację typów i wartości domyślne. Błąd konfiguracji (brakująca zmienna, zły typ) jest wykrywany przy starcie aplikacji, nie w trakcie działania.

```toml
# pyproject.toml
dependencies = ["pydantic-settings>=2.0.0"]
```

---

## Wzorzec: Settings w warstwie bootstrap

```python
# infrastructure/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_file_required=False,  # produkcja dostarcza sekrety przez env kontenera, nie plik
        # extra="ignore" NIE jest tu potrzebne — dotyczy nieznanych pól modelu, nie pliku .env
    )

    # Database
    database_url: str
    db_pool_size: int = 5

    # Application
    app_env: str = "development"
    debug: bool = False
    secret_key: str

    # Feature flags
    feature_new_dashboard: bool = False
    feature_export_pdf: bool = False

    # External APIs
    hf_token: str = ""
    google_sheets_key: str = ""
```

```python
# bootstrap.py (lub manage.py, wsgi.py, main.py)
from infrastructure.config import AppSettings
from application.use_cases.create_meeting import CreateMeeting
from infrastructure.adapters.clock import SystemClock
from infrastructure.adapters.uuid_generator import UuidGenerator
from infrastructure.adapters.persistence.meeting_repository import MeetingRepository


def build_container() -> dict:
    settings = AppSettings()  # jedyne miejsce odczytu env

    return {
        "create_meeting": CreateMeeting(
            repository=MeetingRepository(database_url=settings.database_url),
            clock=SystemClock(),
            id_generator=UuidGenerator(),
            max_duration=settings.max_meeting_duration,  # wstrzykiwana wartość
        ),
    }
```

Warstwy `domain/` i `application/` nigdy nie widzą `AppSettings` — otrzymują tylko konkretne wartości przez konstruktory.

---

## Środowiska (dev / prod)

### Strategia: jeden model ustawień, różne pliki .env

```
.env.example    ← commitowany, lista wszystkich kluczy bez wartości
.env            ← lokalny development (gitignore)
.env.test       ← CI / testy integracyjne (gitignore lub GitHub Secrets)
.env.prod       ← produkcja (tylko GitHub Secrets / secret manager)
```

```python
# infrastructure/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

_env_file = os.getenv("ENV_FILE", ".env")  # jedyne dozwolone os.getenv w config


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_required=False,  # brak pliku nie jest błędem — produkcja używa env kontenera
    )
    ...
```

**Dlaczego `env_file_required=False`:** Na produkcji sekrety są wstrzykiwane przez środowisko kontenera (K8s Secrets, ECS Task Definition, `--env-file` w `docker run`) — fizyczny plik `.env.prod` nie istnieje na dysku kontenera i nie powinien istnieć. Bez tej flagi pydantic-settings w wersji 2.x rzuca `ValidationError` przy braku pliku. Jeśli zmienna środowiskowa jest wymagana a nie istnieje — pydantic-settings i tak zgłosi błąd walidacji przy starcie aplikacji.
```

**Dlaczego `os.getenv` jest tutaj dozwolony:** `infrastructure/` jest warstwą zewnętrzną — według Layer Dependency Matrix może zawierać `os`. `audit_contracts.py` skanuje `domain/` i `application/`, nie `infrastructure/`. Wyjątek jest świadomy i ograniczony do jednego miejsca: `infrastructure/config.py` na poziomie modułu (nie wewnątrz klas ani use case'ów).

Uruchamianie z konkretnym plikiem:

```bash
ENV_FILE=.env.test make test-all
ENV_FILE=.env.prod make docker-up
```

### Walidacja spójności środowisk

```python
# infrastructure/config.py
from pydantic import field_validator


class AppSettings(BaseSettings):
    app_env: str = "development"
    debug: bool = False

    @field_validator("debug")
    @classmethod
    def debug_not_in_production(cls, v: bool, info) -> bool:
        if v and info.data.get("app_env") == "production":
            raise ValueError("debug=True is forbidden in production environment")
        return v
```

---

## Feature Flags

Feature flags są częścią konfiguracji — nie hardkodujemy ich w kodzie.

```python
# infrastructure/config.py
class AppSettings(BaseSettings):
    # Konwencja: feature_<nazwa_funkcji>
    feature_new_dashboard: bool = False
    feature_export_pdf: bool = False
    feature_ai_suggestions: bool = False
```

```python
# application/use_cases/generate_report.py
class GenerateReport:
    def __init__(
        self,
        repository: ReportRepositoryPort,
        export_pdf_enabled: bool = False,  # wstrzykiwana flaga, nie os.getenv
    ) -> None:
        self._repository = repository
        self._export_pdf_enabled = export_pdf_enabled

    def execute(self, dto: ReportInputDTO) -> ReportOutputDTO:
        report = self._repository.get(dto.report_id)
        if self._export_pdf_enabled:
            ...
```

```python
# bootstrap.py
settings = AppSettings()

generate_report = GenerateReport(
    repository=ReportRepository(...),
    export_pdf_enabled=settings.feature_export_pdf,  # bootstrap wstrzykuje flagę
)
```

**Zasada:** feature flag jest bool przekazanym przez konstruktor — use case nie wie że pochodzi z `.env`.

Aktywacja flagi w development:

```bash
FEATURE_EXPORT_PDF=true make run
```

---

## Konfiguracja w testach

```python
# tests/conftest.py
import pytest
from infrastructure.config import AppSettings


@pytest.fixture
def test_settings() -> AppSettings:
    return AppSettings(
        database_url="postgresql://test:test@localhost:5436/test",
        secret_key="test-secret-key-not-for-production",
        app_env="test",
        debug=False,
        feature_new_dashboard=True,  # włącz flagę dla testów
    )
```

Testy nie czytają `.env` — używają jawnych wartości przez fixture. Gwarantuje to deterministyczność (patrz: `17-determinism-contract.md`).

---

## Egzekwowanie

### audit_contracts.py

`make check` (przez `audit_contracts.py`) wykrywa `os.getenv` w `application/`:

```
[CONFIGURATION CONTRACT] os.getenv in application/ — read env only in bootstrap
```

### Manualny audit

```bash
grep -r "os.getenv\|os.environ" domain/ application/
```

---

## Zakazane praktyki

```python
# Zakaz w domain/ i application/:
import os


class MeetingService:
    max_duration = int(os.getenv("MAX_DURATION", "60"))  # ❌


# Zakaz — settings jako singleton globalny importowany wszędzie:
from infrastructure.config import settings  # ❌ w domain/ i application/

settings.database_url  # domena nie zna konfiguracji


# Nakaz — wstrzykiwanie konkretnych wartości:
class MeetingService:
    def __init__(self, max_duration: int) -> None:
        self._max_duration = max_duration  # ✓
```

---

## Powiązanie z innymi kontraktami

| Kontrakt | Powiązanie |
|----------|-----------|
| Determinism Contract | `os.getenv` poza bootstrap = źródło niedeterminizmu |
| Secrets Management | `.env.example` definiuje wszystkie wymagane klucze |
| Domain Purity | `domain/` nie importuje `pydantic_settings` ani `os` |
| Makefile Contract | `make secrets-check` weryfikuje obecność kluczy z `.env.example` |
