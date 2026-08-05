# Ports, Adapters & DTO Contract

**Status:** Architektoniczny
**Zakres:** Wszystkie projekty w architekturze heksagonalnej

---

## Filozofia

Ports & Adapters (architektura heksagonalna) to mechanizm który pozwala domenie nie wiedzieć nic o świecie zewnętrznym. Port to interfejs — kontrakt który `application/` definiuje i oczekuje. Adapter to implementacja — szczegół który `infrastructure/` dostarcza.

DTO (Data Transfer Object) to kontrakt granicy warstwy — nie obiekt domenowy, nie model ORM. Jest miejscem gdzie dane zewnętrzne są walidowane i tłumaczone na język domeny.

---

## Porty — gdzie i przez kogo

**Zasada:** Porty są własnością `application/` — definiuje je warstwa która ich używa, nie która je implementuje.

```
application/ports/
├── clock_port.py           # ClockPort — dostarczanie czasu
├── id_generator_port.py    # IdGeneratorPort — generowanie ID
├── unit_of_work.py         # UnitOfWorkPort — granica transakcji
├── meeting_repository.py   # MeetingRepositoryPort — trwałość encji
└── notification_port.py    # NotificationPort — powiadomienia zewnętrzne
```

```python
# application/ports/meeting_repository.py
from typing import Protocol
from domain.entities.meeting import Meeting


class MeetingRepositoryPort(Protocol):
    def save(self, meeting: Meeting) -> Meeting: ...
    def get_by_id(self, meeting_id: str) -> Meeting | None: ...
    def list_all(self) -> list[Meeting]: ...
```

**Zakaz:** `domain/` nie definiuje portów infrastrukturalnych. Domena definiuje tylko abstrakcje domenowe (encje, value objects, reguły biznesowe) — nie wie że "coś" ją persystuje.

```python
# Zakaz — domena nie zna pojęcia "repozytorium"
# domain/repositories/meeting_repo.py  ← ten katalog nie powinien istnieć

# Nakaz — port należy do application/
# application/ports/meeting_repository.py  ← tu jest właściwe miejsce
```

---

## Adaptery — gdzie i przez kogo

**Zasada:** Adaptery należą do `infrastructure/` i implementują porty zdefiniowane przez `application/`.

```
infrastructure/adapters/
├── clock/
│   └── system_clock.py         # implementuje ClockPort
├── persistence/
│   ├── django_meeting_repo.py  # implementuje MeetingRepositoryPort
│   └── file_meeting_repo.py    # alternatywna implementacja
├── ml/
│   └── whisper_adapter.py      # adapter zewnętrznej biblioteki ML
└── external_api/
    └── google_sheets_adapter.py
```

```python
# infrastructure/adapters/persistence/django_meeting_repo.py
from domain.entities.meeting import Meeting
from application.ports.meeting_repository import MeetingRepositoryPort
from infrastructure.models import MeetingModel  # Django ORM model


class DjangoMeetingRepository:
    """Implementuje MeetingRepositoryPort przez Django ORM."""

    def save(self, meeting: Meeting) -> Meeting:
        obj, _ = MeetingModel.objects.update_or_create(
            id=meeting.id,
            defaults={
                "title": meeting.title,
                "duration_minutes": meeting.duration_minutes,
            },
        )
        return _to_domain(obj)

    def get_by_id(self, meeting_id: str) -> Meeting | None:
        try:
            return _to_domain(MeetingModel.objects.get(id=meeting_id))
        except MeetingModel.DoesNotExist:
            return None
```

**Konwencja nazewnictwa adapterów:**

| Port | Adapter |
|------|---------|
| `ClockPort` | `SystemClock`, `FakeClock` |
| `MeetingRepositoryPort` | `DjangoMeetingRepository`, `FileRepository` |
| `NotificationPort` | `EmailNotificationAdapter`, `SlackAdapter` |

Adapter jest zawsze implementacją konkretnej technologii — nazwa powinna to odzwierciedlać.

---

## DTO — gdzie i przez kogo

**Zasada:** DTO to granica między warstwami. Każda granica ma swój DTO.

```
application/dto/
├── meeting_dtos.py     # MeetingInputDTO, MeetingOutputDTO
├── report_dtos.py
└── user_dtos.py
```

### Wzorzec: Input DTO → Encja → Output DTO

```python
# application/dto/meeting_dtos.py
from pydantic import BaseModel, field_validator
from datetime import datetime
from domain.entities.meeting import Meeting


class MeetingInputDTO(BaseModel):
    """Waliduje dane wejściowe use case'u. Wejście: zewnętrzne (HTTP, CLI, kolejka)."""

    title: str
    duration_minutes: int

    @field_validator("duration_minutes")
    @classmethod
    def must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Duration must be positive")
        return v

    def to_domain(self, id: str, created_at: datetime) -> Meeting:
        """Fabryka: walidowane dane zewnętrzne → encja domenowa.

        id i created_at są generowane przez porty (IdGeneratorPort, ClockPort)
        w use case'ie i przekazywane tu jako argumenty — zgodnie z
        17-determinism-contract.md. DTO nigdy nie generuje ID ani czasu samodzielnie.
        """
        return Meeting(
            id=id,
            title=self.title,
            created_at=created_at,
            duration_minutes=self.duration_minutes,
        )


class MeetingOutputDTO(BaseModel):
    """Serializuje wynik use case'u. Wyjście: HTTP response, kolejka, plik."""

    id: str
    title: str
    is_long: bool

    @classmethod
    def from_domain(cls, entity: Meeting) -> "MeetingOutputDTO":
        """Fabryka: encja domenowa → DTO wyjściowe."""
        return cls(
            id=entity.id,
            title=entity.title,
            is_long=entity.is_long(),
        )
```

### Reguła kierunku zależności dla DTO

```
MeetingInputDTO  → może importować Meeting (DTO zna encję)
Meeting          → nie może importować MeetingInputDTO (encja nie zna DTO)
```

DTO może importować encję domenową żeby ją skonstruować. Encja domenowa nigdy nie wie że istnieje DTO. Naruszenie tej reguły jest wykrywane przez `import-linter`.

---

## Gdzie wolno używać Pydantic — mapa

| Warstwa | Pydantic | Forma | Uzasadnienie |
|---------|----------|-------|--------------|
| `domain/` | ❌ zakaz | — | Domena zależy tylko od stdlib |
| `application/dto/` | ✅ zalecane | `BaseModel` | Walidacja wejścia/wyjścia use case'ów |
| `infrastructure/` | ✅ dozwolone | `BaseModel`, `BaseSettings` | Adaptery zewnętrznych API, konfiguracja |
| `apps/` (widoki) | ✅ dozwolone | `BaseModel` | Request/response warstwy webowej |
| `tests/` | ✅ dozwolone | dowolnie | Fixtures, factory |

**Zakaz:** `dataclass` z `domain/` nie dziedziczy z `BaseModel`. To byłoby wprowadzenie zależności od Pydantic do domeny przez dziedziczenie.

---

## Gdzie wolno używać dataclasses — mapa

| Warstwa | dataclasses | Forma |
|---------|-------------|-------|
| `domain/` | ✅ podstawowy budulec | `@dataclass`, `@dataclass(frozen=True)` |
| `application/` | ⚠️ rzadko | tylko jeśli DTO nie wymaga walidacji |
| `infrastructure/` | ❌ nie zalecane | zamiast tego: Pydantic lub ORM model |

```python
# domain/entities/meeting.py — dataclass jest właściwy
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Meeting:
    id: str
    title: str
    created_at: datetime
    duration_minutes: int

    def is_long(self) -> bool:
        return self.duration_minutes > 60


# domain/value_objects/duration.py — frozen dataclass dla value objects
@dataclass(frozen=True)
class Duration:
    minutes: int

    def __post_init__(self) -> None:
        if self.minutes <= 0:
            raise ValueError(f"Duration must be positive, got {self.minutes}")

    def is_long(self) -> bool:
        return self.minutes > 60
```

---

## Granica API (projekty webowe)

W projektach z HTTP (FastAPI, Django REST, Flask) istnieje dodatkowa granica między widokiem a use case'em.

```
HTTP Request
    ↓
RequestSchema (Pydantic — apps/ lub views/)
    ↓
InputDTO (application/dto/) ← tu walidacja biznesowa
    ↓
Use Case
    ↓
OutputDTO (application/dto/)
    ↓
ResponseSchema (Pydantic — apps/ lub views/)
    ↓
HTTP Response
```

**Zasada:** `RequestSchema` i `ResponseSchema` to schematy HTTP — dotyczą formatu, nagłówków, kodów statusu. `InputDTO` i `OutputDTO` to kontrakty use case'u — dotyczą logiki biznesowej. To są różne obiekty z różnymi odpowiedzialnościami.

```python
# apps/views/meetings.py (Django) — warstwa HTTP
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from application.dto.meeting_dtos import MeetingInputDTO
from application.use_cases.create_meeting import CreateMeeting


@api_view(["POST"])
def create_meeting_view(request: Request) -> Response:
    # 1. Walidacja HTTP (format requestu)
    dto = MeetingInputDTO.model_validate(request.data)  # Pydantic raises → 422
    # 2. Wywołanie use case'u
    result = container["create_meeting"].execute(dto)
    # 3. Serializacja odpowiedzi HTTP
    return Response(result.model_dump(), status=201)
```

**Zakaz:** Widok nie operuje bezpośrednio na encjach domenowych. `Meeting` nigdy nie trafia do `Response` — zawsze przez `OutputDTO`.

---

## Egzekwowanie

| Narzędzie | Co weryfikuje |
|-----------|--------------|
| `import-linter` | Kierunek zależności: DTO → encja (dozwolone), encja → DTO (zakaz) |
| `ruff TID251` | Pydantic zakazany w `domain/` |
| `mypy strict` | Typy portów i adapterów — niezgodność sygnatury wykryta statycznie |
| `audit_contracts.py` | Pydantic w `domain/` przez whitelist stdlib |

---

## Powiązanie z innymi kontraktami

| Kontrakt | Powiązanie |
|----------|-----------|
| Domain Purity | Porty należą do `application/`, nie `domain/` — domena nie zna infrastruktury |
| Transaction Contract | `UnitOfWorkPort` to port — wzorzec identyczny jak `MeetingRepositoryPort` |
| DataFrame Contract | DataFrame jest tłumaczony na DTO w `application/` przed wejściem do use case'u |
| Configuration Contract | `AppSettings` wstrzykuje konkretne adaptery przez bootstrap — nie przez importy w use case'ach |
