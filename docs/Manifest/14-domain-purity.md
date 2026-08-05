# Domain Purity Contract

**Status:** Architektoniczny  
**Zakres:** Wszystkie projekty w architekturze heksagonalnej

---

## Filozofia

Domena jest rdzeniem aplikacji. Nie zależy od frameworków, baz danych, bibliotek ML ani żadnych zewnętrznych szczegółów implementacyjnych. Domena żyje dłużej niż każda biblioteka której używasz.

**Zasada:** Jeśli usuniesz Django, FastAPI, Torch i Pydantic — domena nadal musi się kompilować i przechodzić testy.

---

## Dozwolone zależności w `domain/`

Tylko biblioteka standardowa Pythona:

```
domain/
├── entities/       # dataclasses, klasy Pythona
├── value_objects/  # frozen dataclasses, __eq__, __hash__
├── services/       # czyste funkcje i klasy
└── exceptions.py   # własne wyjątki dziedziczące z Exception
```

**Uwaga o portach:** Porty (interfejsy `Protocol`/`ABC`) należą do `application/ports/` — nie do `domain/`. Domena nie wie że "coś" ją obsługuje. Szczegóły: `22-ports-adapters-dto-contract.md`.

**Dozwolone importy:**
- `from __future__ import annotations`
- `from dataclasses import dataclass, field`
- `from typing import Protocol, Any, Optional` — `Protocol` dozwolony dla domenowych strategii (np. `ScoringStrategy`), nie dla portów infrastrukturalnych
- `from abc import ABC, abstractmethod` — j.w.
- `from enum import Enum`
- `import datetime`, `import uuid`, `import decimal`

**Zakaz:**

| Biblioteka | Powód zakazu |
|------------|--------------|
| `pydantic` | Framework zewnętrzny — narusza izolację domeny |
| `django` / `sqlalchemy` | ORM — domena nie zna bazy danych |
| `torch` / `numpy` | ML — domena nie zna infrastruktury obliczeniowej |
| `requests` / `httpx` | Sieć — domena nie komunikuje się z zewnętrzem |
| `fastapi` / `flask` | Web framework — domena nie zna HTTP |
| `icontract` | Biblioteka zewnętrzna — kontrakty domenowe wyrażamy przez `assert` i własne wyjątki |
| `pandera` | Walidacja DataFrame — domena nie zna struktury tabelarycznej |
| `loguru` / `logging` | Logging — domena nie loguje, to szczegół infrastrukturalny |
| `random` | Niedeterministyczność — patrz `17-determinism-contract.md` |
| `os` | Konfiguracja środowiskowa — domena nie czyta zmiennych env, patrz `20-configuration-contract.md` |

### Zakaz w bloku `TYPE_CHECKING` — klasyczne obejście

```python
# Zakaz — pozornie bezpieczne, ale narusza izolację:
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas  # ❌ nadal naruszenie kontraktu
    from pydantic import BaseModel  # ❌
```

Blok `TYPE_CHECKING` jest wykonywany przez type checkery (mypy, pyright) — domena deklaruje zależność od biblioteki nawet jeśli nie importuje jej w runtime. `audit_contracts.py` wykrywa i raportuje importy w `TYPE_CHECKING` jako osobną kategorię naruszeń.

### Kontrakty w domenie bez `icontract`

```python
# Zamiast @icontract.require(lambda x: x > 0)
def calculate_score(value: float) -> float:
    if value <= 0:
        raise InvalidScoreInput("Score input must be positive")
    return value * 1.5
```

---

## Pydantic — gdzie należy

| Warstwa | Status Pydantic | Uzasadnienie |
|---------|----------------|--------------|
| `domain/` | **Zakaz** | Narusza izolację — domena zależy od frameworka |
| `application/dto/` | **Zalecane** | DTO to kontrakt API, walidacja wejścia/wyjścia use case'ów |
| `infrastructure/` | **Dozwolone** | Walidacja odpowiedzi z zewnętrznych API |
| `apps/` / `adapters/` | **Dozwolone** | Modele request/response warstwy webowej |

### Wzorzec: `to_domain()` / `from_domain()`

DTO może importować Encję. Encja nie może importować DTO — nigdy.

```python
# domain/entities/meeting.py — czysta klasa Pythona
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Meeting:
    id: str
    title: str
    date: datetime
    duration_minutes: int

    def is_long(self) -> bool:
        return self.duration_minutes > 60


# application/dto/meeting_dtos.py — Pydantic DTO
from pydantic import BaseModel, field_validator
from domain.entities.meeting import Meeting  # DTO zna Encję ✓


class MeetingInputDTO(BaseModel):
    title: str
    date: datetime
    duration_minutes: int

    @field_validator("duration_minutes")
    def must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Duration must be positive")
        return v

    def to_domain(self, id: str, created_at: datetime) -> Meeting:
        """Fabryka: DTO → Encja domenowa."""
        return Meeting(
            id=id,
            title=self.title,
            date=self.date,
            duration_minutes=self.duration_minutes,
        )


class MeetingOutputDTO(BaseModel):
    id: str
    title: str
    is_long: bool

    @classmethod
    def from_domain(cls, entity: Meeting) -> "MeetingOutputDTO":
        """Fabryka: Encja domenowa → DTO."""
        return cls(
            id=entity.id,
            title=entity.title,
            is_long=entity.is_long(),
        )
```

Use case używa fabryk:

```python
class CreateMeeting:
    def execute(self, dto: MeetingInputDTO) -> MeetingOutputDTO:
        meeting = dto.to_domain(
            id=self.id_generator.generate(),
            created_at=self.clock.now(),
        )
        saved = self.repository.save(meeting)
        return MeetingOutputDTO.from_domain(saved)
```

---

## Import Direction Contract

Kierunek importów musi być jednostronny — zawsze do wewnątrz. Nigdy na zewnątrz.

```
tests/ → infrastructure/ → application/ → domain/
                                          ↑
                                    (tylko stdlib)
```

| Warstwa | Może importować | Nie może importować |
|---------|----------------|---------------------|
| `domain/` | Tylko stdlib | Wszystko inne |
| `application/` | `domain/` + stdlib | `infrastructure/` |
| `infrastructure/` | `application/`, `domain/`, biblioteki | — |
| `tests/` | Wszystko | — |

**Kluczowa zasada:** `application/` nie importuje `infrastructure/`. Zależność jest odwrócona przez porty (Ports & Adapters).

---

## Egzekwowanie przez import-linter

```bash
uv add --group dev-slim import-linter
```

### Wariant A — Klasyczna struktura heksagonalna

Stosowany gdy `domain/`, `application/`, `infrastructure/` są osobnymi pakietami (np. clean_badges):

```ini
# .importlinter
[importlinter]
root_packages =
    domain
    application
    apps

[importlinter:contract:domain-purity]
name = Domain must not import from application or infrastructure
type = forbidden
source_modules = domain
forbidden_modules =
    application
    apps

[importlinter:contract:application-purity]
name = Application must not import from infrastructure
type = forbidden
source_modules = application
forbidden_modules =
    apps

[importlinter:contract:layers]
name = Hexagonal Architecture Layers
type = layers
layers =
    apps
    application
    domain
```

### Wariant B — Django monolit (per-app)

Stosowany gdy domena i infrastruktura mieszkają w tej samej hierarchii `apps.*` (np. GTD_Planner). Kontrakt `layers` nie jest możliwy — definiujemy `forbidden` per-aplikacja.

`include_external_packages = True` jest konieczne żeby import-linter widział `django` jako zakazany moduł zewnętrzny.

```ini
# .importlinter
[importlinter]
root_packages =
    apps
include_external_packages = True

[importlinter:contract:tasks-domain-purity]
name = Tasks Domain must not import from Django or infrastructure
type = forbidden
source_modules =
    apps.tasks.domain
forbidden_modules =
    django
    apps.tasks.adapters
    apps.tasks.models
    apps.tasks.views

[importlinter:contract:calendar-domain-purity]
name = Calendar Domain must not import from Django or infrastructure
type = forbidden
source_modules =
    apps.calendar_app.domain
forbidden_modules =
    django
    apps.calendar_app.adapters
    apps.calendar_app.models
    apps.calendar_app.views
```

Każda nowa aplikacja Django wymaga osobnego bloku kontraktu.

Dodaj do `make check` (przez target `type-check`):
```makefile
type-check:
    uv run mypy $(PY_DIRS)
    uv run lint-imports
```

---

## Layer Dependency Matrix

| Biblioteka | `domain/` | `application/` | `infrastructure/` | `tests/` |
|------------|-----------|----------------|-------------------|----------|
| `dataclasses`, `typing`, `abc` | ✅ | ✅ | ✅ | ✅ |
| `pydantic` | ❌ | ✅ zalecane | ✅ | ✅ |
| `pandera` | ❌ | ⚠️ tranzytowo | ✅ zalecane | ✅ |
| `pandas` | ❌ | ⚠️ tranzytowo | ✅ | ✅ |
| `loguru` / `logging` | ❌ | ❌ | ✅ | ✅ |
| `django` / `sqlalchemy` | ❌ | ❌ | ✅ | ✅ |
| `requests` / `httpx` | ❌ | ❌ | ✅ | ✅ |
| `torch` / `numpy` | ❌ | ❌ | ✅ | ✅ |
| `random` | ❌ | ❌ | ✅ | ✅ |
| `os` (getenv/environ) | ❌ | ❌ | ✅ | ✅ |
| `faker` | ❌ | ❌ | ❌ | ✅ |
| `hypothesis` | ❌ | ❌ | ❌ | ✅ |
| `vcrpy` | ❌ | ❌ | ❌ | ✅ |

### Pytanie audytowe

Podczas przeglądu repo zadaj jedno pytanie:

> Czy którakolwiek biblioteka z kolumny ❌ pojawia się w tej warstwie?

To jest binarne, mierzalne i egzekwowalne przez ruff + mypy + import-linter.

---

## Egzekwowanie przez Ruff (TID251)

```toml
[[tool.ruff.lint.flake8-tidy-imports.banned-api]]
module = "pydantic"
msg = "Pydantic is banned in domain/. Use application/dto/ instead."

[[tool.ruff.lint.flake8-tidy-imports.banned-api]]
module = "django"
msg = "Django is banned in domain/. Keep domain pure."

[[tool.ruff.lint.flake8-tidy-imports.banned-api]]
module = "logging"
msg = "logging is banned in domain/. Logging belongs in infrastructure/."

[[tool.ruff.lint.flake8-tidy-imports.banned-api]]
module = "loguru"
msg = "loguru is banned in domain/. Logging belongs in infrastructure/."

[[tool.ruff.lint.flake8-tidy-imports.banned-api]]
module = "random"
msg = "random is banned in domain/. Use injected IdGeneratorPort for randomness."

[[tool.ruff.lint.flake8-tidy-imports.banned-api]]
module = "datetime.datetime.utcnow"
msg = "datetime.utcnow() is banned. Use injected ClockPort instead."

[[tool.ruff.lint.flake8-tidy-imports.banned-api]]
module = "datetime.datetime.now"
msg = "datetime.now() is banned in domain/application. Use injected ClockPort instead."
```

**Uwaga:** ruff banned-api nie wykrywa importów ukrytych w bloku `TYPE_CHECKING`. To jest jedna z luk które zamknął `audit_contracts.py`.

---

## Manualny audit

```bash
# Sprawdź czy domena importuje cokolwiek spoza stdlib
grep -r "^import\|^from" domain/ | grep -v \
  "from __future__\|from dataclasses\|from typing\|from abc\|from enum\
  \|import datetime\|import uuid\|import decimal\|from domain"
```

## Podsumowanie narzędzi egzekwowania

| Narzędzie | Co wykrywa |
|-----------|-----------|
| ruff TID251 | Bezpośrednie importy zakazanych bibliotek |
| import-linter | Kierunek zależności między warstwami |
| mypy strict | Błędy typów — przypadkowe użycie typów zewnętrznych bibliotek |
| `audit_contracts.py` | Importy w `TYPE_CHECKING`; `datetime.now/utcnow`, `uuid4()`, `random.*` w domain/ i application/; `os` i `random` jako zakazane importy w domain/; `os.getenv` w application/; DataFrame w domain/; niezgodność wersji Pythona |

---

## Migracja istniejących projektów

1. Zidentyfikuj modele Pydantic w `domain/`
2. Utwórz odpowiednie `dataclass` w `domain/entities/`
3. Przenieś modele Pydantic do `application/dto/`
4. Zaktualizuj use case'y — mapowanie DTO ↔ encja
5. Testy muszą przejść na każdym kroku

Nie ma wyjątków od tej migracji dla projektów hex arch.
