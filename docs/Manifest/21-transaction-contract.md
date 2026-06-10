# Transaction Contract

**Status:** Architektoniczny
**Zakres:** Wszystkie projekty backendowe z bazą danych

---

## Filozofia

Transakcja to granica spójności — nie szczegół implementacyjny ORM. Decyzja o tym *co* jest jedną transakcją należy do `application/`. Decyzja o tym *jak* ją wykonać należy do `infrastructure/`.

**Zasada:** `application/` definiuje granicę atomowości przez port. `infrastructure/` dostarcza implementację.

---

## Wzorzec: Unit of Work Port

Use case nie wie czy używa Django ORM, SQLAlchemy czy pliku na dysku. Wie tylko że operacje wewnątrz `UnitOfWork` są atomowe.

```python
# application/ports/unit_of_work.py
from typing import Protocol, Self
from types import TracebackType

class UnitOfWorkPort(Protocol):
    def __enter__(self) -> Self: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
```

```python
# application/use_cases/process_meeting.py
class ProcessMeeting:
    def __init__(
        self,
        uow: UnitOfWorkPort,
        clock: ClockPort,
        id_generator: IdGeneratorPort,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    def execute(self, dto: MeetingInputDTO) -> MeetingOutputDTO:
        with self._uow:
            try:
                meeting = dto.to_domain(
                    id=self._id_generator.generate(),
                    created_at=self._clock.now(),
                )
                saved = self._uow.meetings.save(meeting)
                self._uow.commit()
                return MeetingOutputDTO.from_domain(saved)
            except DomainException as e:
                self._uow.rollback()
                raise UseCaseError(f"Business rule violation: {e}") from e
```

### Implementacje w infrastructure/

```python
# infrastructure/adapters/persistence/django_uow.py
from django.db import transaction as django_transaction
from application.ports.unit_of_work import UnitOfWorkPort
from infrastructure.adapters.persistence.meeting_repository import MeetingRepository

class DjangoUnitOfWork:
    def __init__(self) -> None:
        self.meetings: MeetingRepository | None = None
        self._transaction: django_transaction.Atomic | None = None

    def __enter__(self) -> "DjangoUnitOfWork":
        self._transaction = django_transaction.atomic()
        self._transaction.__enter__()
        self.meetings = MeetingRepository()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._transaction:
            self._transaction.__exit__(exc_type, exc_val, exc_tb)

    def commit(self) -> None:
        pass  # Django atomic() commituje przy wyjściu z bloku bez wyjątku

    def rollback(self) -> None:
        if self._transaction:
            django_transaction.set_rollback(True)
```

```python
# infrastructure/adapters/persistence/sqlalchemy_uow.py
from sqlalchemy.orm import Session
from application.ports.unit_of_work import UnitOfWorkPort

class SQLAlchemyUnitOfWork:
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory
        self.session: Session | None = None

    def __enter__(self) -> "SQLAlchemyUnitOfWork":
        self.session = self._session_factory()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.session:
            self.session.close()

    def commit(self) -> None:
        if self.session:
            self.session.commit()

    def rollback(self) -> None:
        if self.session:
            self.session.rollback()
```

### Implementacja testowa

```python
# tests/fakes/unit_of_work.py
from collections import defaultdict
from application.ports.unit_of_work import UnitOfWorkPort
from tests.fakes.meeting_repository import FakeMeetingRepository

class FakeUnitOfWork:
    def __init__(self) -> None:
        self.meetings = FakeMeetingRepository()
        self.committed = False

    def __enter__(self) -> "FakeUnitOfWork":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        pass

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.committed = False


# tests/unit/application/test_process_meeting.py
def test_commit_called_on_success() -> None:
    uow = FakeUnitOfWork()
    use_case = ProcessMeeting(uow=uow, clock=FakeClock(), id_generator=SequentialIdGenerator())
    use_case.execute(MeetingInputDTO(title="Standup", duration_minutes=15))
    assert uow.committed is True

def test_rollback_called_on_domain_error() -> None:
    uow = FakeUnitOfWork()
    use_case = ProcessMeeting(uow=uow, clock=FakeClock(), id_generator=SequentialIdGenerator())
    with pytest.raises(UseCaseError):
        use_case.execute(MeetingInputDTO(title="", duration_minutes=15))  # pusty tytuł → ValidationError
    assert uow.committed is False
```

**Wariant async (FastAPI + SQLAlchemy Async):** Przy asynchronicznym ORM protokół zmienia się na `AsyncUnitOfWorkPort` z metodami `__aenter__` i `__aexit__`. Wzorzec jest identyczny — zmienia się tylko sygnatura i użycie `async with self._uow:` w use case'ach.

---

## Idempotentność operacji

Operacje zapisu muszą być bezpieczne przy wielokrotnym wywołaniu z tymi samymi danymi. Jest to kluczowe dla retry i systemów kolejkowych.

**Zasada:** Operacja jest idempotentna gdy wywołanie jej N razy daje ten sam efekt co wywołanie raz.

```python
# Zakaz — nie-idempotentna operacja zapisu
def create_meeting(self, dto: MeetingInputDTO) -> Meeting:
    return Meeting.objects.create(...)  # każde wywołanie tworzy nowy rekord

# Nakaz — idempotentna operacja przez get_or_create lub upsert
def save_meeting(self, meeting: Meeting) -> Meeting:
    obj, created = Meeting.objects.update_or_create(
        id=meeting.id,                  # klucz idempotentności: ID wstrzyknięte przez use case
        defaults={
            "title": meeting.title,
            "duration_minutes": meeting.duration_minutes,
        },
    )
    return _to_domain(obj)
```

**Dlaczego ID jest kluczem idempotentności:** `IdGeneratorPort` w use case generuje ID *przed* zapisem. Przy retry ten sam `dto` trafia do use case z tym samym ID — `update_or_create` nie tworzy duplikatu.

---

## Retry z backoff

Transjentne błędy infrastruktury (timeout bazy, chwilowy brak sieci) powinny być obsługiwane przez retry — nie propagowane jako błąd biznesowy.

**Zakres:** wyłącznie `infrastructure/` — logika retry jest szczegółem implementacyjnym adaptera.

```python
# infrastructure/adapters/persistence/resilient_repository.py
import time
from infrastructure.exceptions import PersistenceError

def with_retry(max_attempts: int = 3, backoff_seconds: float = 0.5):
    """Dekorator retry z eksponencjalnym backoff dla operacji infrastrukturalnych."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_error: Exception | None = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except PersistenceError as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        time.sleep(backoff_seconds * (2 ** attempt))
            raise PersistenceError(
                f"Operation failed after {max_attempts} attempts"
            ) from last_error
        return wrapper
    return decorator


class ResilientMeetingRepository:
    @with_retry(max_attempts=3, backoff_seconds=0.5)
    def save(self, meeting: Meeting) -> Meeting:
        return self._do_save(meeting)
```

**Zasady retry:**
- Tylko dla błędów transjentnych (`PersistenceError`, `NetworkError`) — nie dla `DomainException`
- Maksymalnie 3 próby z eksponencjalnym backoff — nie nieskończona pętla
- Każda próba logowana na poziomie `WARNING` — widoczne w monitoringu
- Ostateczna porażka propagowana jako `PersistenceError` z łańcuchem `from e`

---

## Zakaz transakcji w domain/

```python
# Zakaz — domena nie zna transakcji
class MeetingService:
    def create_and_notify(self, title: str) -> None:
        with django.db.transaction.atomic():  # ❌ domena nie zna Django
            meeting = Meeting.objects.create(title=title)
            Notification.objects.create(meeting=meeting)

# Nakaz — use case orkiestruje przez UoW Port
class CreateMeetingAndNotify:
    def execute(self, dto: MeetingInputDTO) -> MeetingOutputDTO:
        with self._uow:
            meeting = dto.to_domain(...)
            self._uow.meetings.save(meeting)
            self._uow.notifications.schedule(meeting.id)
            self._uow.commit()
```

---

## Warstwowanie

| Warstwa | Odpowiedzialność |
|---------|-----------------|
| `domain/` | Definiuje reguły biznesowe — nie zna transakcji |
| `application/` | Definiuje granicę atomowości przez `UnitOfWorkPort` |
| `infrastructure/` | Implementuje `UnitOfWork` dla konkretnej bazy danych |
| `bootstrap/` | Wstrzykuje konkretną implementację `UnitOfWork` do use case'ów |
| `tests/` | Używa `FakeUnitOfWork` — weryfikuje commit/rollback bez bazy |

---

## Powiązanie z innymi kontraktami

| Kontrakt | Powiązanie |
|----------|-----------|
| Domain Purity | `domain/` nie importuje ORM — transakcje są wstrzykiwane przez port |
| Error Boundary | `UnitOfWork.rollback()` wywoływany przy `DomainException` przed re-raise |
| Determinism Contract | `IdGeneratorPort` dostarcza ID przed zapisem — klucz idempotentności |
| Configuration Contract | Połączenie z bazą danych pochodzi z `AppSettings` wstrzykiwanego przez bootstrap |
