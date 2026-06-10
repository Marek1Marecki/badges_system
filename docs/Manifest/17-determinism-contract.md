# Determinism Contract

**Status:** Architektoniczny  
**Zakres:** Wszystkie projekty w architekturze heksagonalnej

---

## Filozofia

Kod który zależy od czasu, losowości lub środowiska jest kodem który nie jest deterministyczny — i nie jest w pełni testowalny.

**Zasada:** Czas, losowość i zależności środowiskowe są wstrzykiwane — nie wywoływane bezpośrednio w `domain/` i `application/`.

---

## Źródła niedeterminizmu

| Źródło | Przykład | Problem |
|--------|----------|---------| 
| Czas systemowy | `datetime.now()` | Różny wynik przy każdym wywołaniu |
| Losowość | `random.random()`, `uuid.uuid4()` | Nieprzewidywalny wynik |
| Zmienne środowiskowe | `os.getenv("ENV")` | Zależy od środowiska uruchomienia |
| System plików | `Path.cwd()` | Różny na różnych maszynach |
| Sieć | `requests.get(url)` | Zależy od zewnętrznego serwisu |

---

## Zasady per warstwa

### `domain/` — zakaz bezpośrednich wywołań

```python
# Zakaz w domain/:
class Meeting:
    def __init__(self) -> None:
        self.created_at = datetime.now()  # niedeterministyczne
        self.id = str(uuid.uuid4())       # niedeterministyczne

# Nakaz — wstrzykiwanie przez konstruktor:
@dataclass
class Meeting:
    id: str
    created_at: datetime
    title: str
    duration_minutes: int
    # Czas i ID są przekazywane z zewnątrz — domena jest czysta
```

### `application/` — porty dla czasu i ID

Use case otrzymuje dostawcę czasu i generatora ID przez dependency injection:

```python
# application/ports/clock_port.py
from typing import Protocol
from datetime import datetime

class ClockPort(Protocol):
    def now(self) -> datetime: ...

class IdGeneratorPort(Protocol):
    def generate(self) -> str: ...


# application/use_cases/create_meeting.py
class CreateMeeting:
    def __init__(
        self,
        repository: MeetingRepositoryPort,
        clock: ClockPort,
        id_generator: IdGeneratorPort,
    ) -> None:
        self.repository = repository
        self.clock = clock
        self.id_generator = id_generator

    def execute(self, dto: MeetingInputDTO) -> MeetingOutputDTO:
        meeting = Meeting(
            id=self.id_generator.generate(),   # wstrzykiwane
            created_at=self.clock.now(),       # wstrzykiwane
            title=dto.title,
            duration_minutes=dto.duration_minutes,
        )
        return MeetingOutputDTO.from_domain(self.repository.save(meeting))
```

### `infrastructure/` — rzeczywiste implementacje

```python
# infrastructure/adapters/clock.py
from datetime import datetime, timezone

class SystemClock:
    def now(self) -> datetime:
        return datetime.now(tz=timezone.utc)

class UuidGenerator:
    def generate(self) -> str:
        import uuid
        return str(uuid.uuid4())
```

### `tests/` — kontrolowane implementacje

```python
# tests/fakes/clock.py
from datetime import datetime, timezone

class FakeClock:
    def __init__(self, fixed_time: datetime | None = None) -> None:
        self._time = fixed_time or datetime(2026, 1, 1, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._time

class SequentialIdGenerator:
    def __init__(self) -> None:
        self._counter = 0

    def generate(self) -> str:
        self._counter += 1
        return f"test-id-{self._counter:04d}"


# tests/unit/domain/test_meeting.py
def test_meeting_creation_uses_injected_time() -> None:
    clock = FakeClock(datetime(2026, 1, 15, tzinfo=timezone.utc))
    id_gen = SequentialIdGenerator()
    use_case = CreateMeeting(
        repository=FakeMeetingRepository(),
        clock=clock,
        id_generator=id_gen,
    )
    result = use_case.execute(MeetingInputDTO(title="Standup", duration_minutes=15))

    assert result.created_at == datetime(2026, 1, 15, tzinfo=timezone.utc)
    assert result.id == "test-id-0001"
    # Test jest 100% deterministyczny — zero zależności od systemu
```

---

## Zmienne środowiskowe

Zmienne środowiskowe są czytane **wyłącznie** w warstwie bootstrapu przez `AppSettings` — nie w domenie ani use case'ach. Szczegółowy wzorzec: `20-configuration-contract.md`.

```python
# Zakaz w domain/ i application/:
class MeetingService:
    def __init__(self) -> None:
        self.max_duration = int(os.getenv("MAX_MEETING_DURATION", "120"))

# Nakaz — AppSettings w bootstrap, wstrzykiwanie konkretnych wartości:
# bootstrap.py
from infrastructure.config import AppSettings

def build_container() -> dict:
    settings = AppSettings()   # jedyne miejsce odczytu env
    return {
        "create_meeting": CreateMeeting(
            repository=MeetingRepositoryAdapter(),
            clock=SystemClock(),
            id_generator=UuidGenerator(),
            max_duration=settings.max_meeting_duration,  # wstrzykiwana wartość, nie getenv
        ),
    }
```

---

## Hypothesis i determinizm

Hypothesis automatycznie wykrywa niedeterministyczne testy i zgłasza błąd jeśli test daje różne wyniki dla tych samych danych wejściowych. `FakeClock` + `SequentialIdGenerator` gwarantują że testy Hypothesis są w pełni powtarzalne.

---

## Egzekwowanie

### audit_contracts.py (automatyczne — część `make check`)

`audit_contracts.py` wykrywa niedeterministyczne wywołania w `domain/` i `application/` przez analizę AST:

- `datetime.now()`, `datetime.utcnow()` — z prefiksem i bez
- `uuid.uuid4()`, `uuid4()` — w tym `from uuid import uuid4; uuid4()`
- `random.random()`, `random.randint()`, `random.choice()`, `time.time()`

Każde naruszenie jest zgłaszane z numerem linii. Brak manualnego sprawdzenia przy code review dla tych przypadków.

### Ruff banned-api (automatyczne)

```toml
[[tool.ruff.lint.flake8-tidy-imports.banned-api]]
module = "datetime.datetime.now"
msg = "Use injected ClockPort instead of datetime.now() in domain/application."
```

### Manualny grep (pomocniczo, przy onboardingu)

```bash
grep -r "datetime\.now\(\)\|uuid\.uuid4\(\)\|random\.\|os\.getenv" domain/ application/
```

Patrz: `20-configuration-contract.md` w kwestii zmiennych środowiskowych — zasada bootstrapu dotyczy też konfiguracji.

---

## Powiązanie z innymi kontraktami

| Kontrakt | Powiązanie |
|----------|-----------|
| Configuration Contract | `os.getenv` poza bootstrapem = naruszenie obu kontraktów jednocześnie; `AppSettings` jest jedynym miejscem odczytu env |
| Domain Purity | `random` i `os` są zakazane w `domain/` — egzekwowane przez `audit_contracts.py` i tabelę zakazanych bibliotek |
| Test Coverage & Quality | `FakeClock` i `SequentialIdGenerator` gwarantują deterministyczność testów jednostkowych i Hypothesis |
| Error Boundary Contract | Wyjątki domenowe nie zawierają wyników niedeterministycznych wywołań — czas i ID są wstrzykiwane przed ich powstaniem |
