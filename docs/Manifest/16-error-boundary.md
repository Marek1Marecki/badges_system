# Error Boundary Contract

**Status:** Architektoniczny  
**Zakres:** Wszystkie projekty w architekturze heksagonalnej

---

## Filozofia

Wyjątek jest kontraktem. Każda warstwa ma prawo rzucać tylko swoje wyjątki i jest odpowiedzialna za tłumaczenie wyjątków z warstw niższych.

**Zasada:** Wyjątki domenowe nie wychodzą poza `application/`. Warstwa prezentacji (UI, CLI, HTTP) nigdy nie widzi `DomainException`.

---

## Hierarchia wyjątków

```
BaseException
└── Exception
    ├── DomainException          # domain/exceptions.py
    │   ├── ValidationError      # reguły biznesowe
    │   ├── NotFoundError        # brak encji
    │   └── ConflictError        # naruszenie niezmiennika
    ├── ApplicationException     # application/exceptions.py
    │   ├── UseCaseError         # błąd orkiestracji
    │   └── MappingError         # błąd mapowania DTO↔encja
    └── InfrastructureException  # infrastructure/exceptions.py
        ├── AdapterError         # błąd adaptera zewnętrznego
        ├── PersistenceError     # błąd zapisu/odczytu
        └── NetworkError         # błąd komunikacji sieciowej
```

---

## Zasady per warstwa

### `domain/`

Rzuca tylko `DomainException` i podklasy. Nigdy nie łapie wyjątków infrastrukturalnych. Nigdy nie rzuca `ValueError`, `TypeError`, `KeyError` bezpośrednio — zawsze własna podklasa.

```python
# domain/exceptions.py
class DomainException(Exception):
    """Bazowy wyjątek domenowy."""


class ValidationError(DomainException):
    """Naruszenie reguły biznesowej."""


class NotFoundError(DomainException):
    """Encja nie istnieje."""


class ConflictError(DomainException):
    """Naruszenie niezmiennika domenowego."""
```

```python
# domain/entities/meeting.py
class Meeting:
    def set_duration(self, minutes: int) -> None:
        if minutes <= 0:
            raise ValidationError(f"Duration must be positive, got {minutes}")
```

### `application/`

Łapie `DomainException` i tłumaczy na `ApplicationException` jeśli potrzeba. Łapie `InfrastructureException` z portów i tłumaczy na `ApplicationException`. **Nigdy** nie przepuszcza `DomainException` do warstwy prezentacji.

```python
# application/use_cases/process_meeting.py
class ProcessMeeting:
    def execute(self, dto: MeetingInputDTO) -> MeetingOutputDTO:
        try:
            meeting = dto.to_domain(
                id=self.id_generator.generate(),
                created_at=self.clock.now(),
            )
            result = self.repository.save(meeting)
            return MeetingOutputDTO.from_domain(result)
        except DomainException as e:
            raise UseCaseError(f"Business rule violation: {e}") from e
        except InfrastructureException as e:
            raise UseCaseError(f"Storage failure: {e}") from e
```

### `infrastructure/`

Nigdy nie rzuca `ValueError`, `KeyError`, `requests.HTTPError` bezpośrednio. Zawsze opakowuje wyjątki zewnętrzne we własne podklasy `InfrastructureException`.

```python
# infrastructure/adapters/persistence/file_repository.py
class FileRepository:
    def save(self, meeting: Meeting) -> Meeting:
        try:
            self._write_to_disk(meeting)
            return meeting
        except OSError as e:
            raise PersistenceError(f"Failed to save meeting {meeting.id}") from e
        except json.JSONDecodeError as e:
            raise PersistenceError(f"Corrupted data for meeting {meeting.id}") from e
```

### Warstwa prezentacji (CLI / Streamlit / Django views)

Łapie `ApplicationException` i mapuje na komunikat użytkownika lub kod HTTP. Nigdy nie łapie `Exception` bez re-raise lub logowania.

```python
# app.py (Streamlit)
try:
    result = use_case.execute(dto)
except UseCaseError as e:
    st.error(f"Nie można przetworzyć: {e}")
except ApplicationException as e:
    st.error(f"Błąd aplikacji: {e}")
    logger.error(f"Unhandled application error: {e}")
```

---

## Zakaz `except Exception`

```python
# Zakaz — łapie wszystko, maskuje błędy
try:
    result = use_case.execute(dto)
except Exception:
    pass  # silent fail — najgorszy możliwy wzorzec

# Zakaz — zbyt szeroki catch bez re-raise
try:
    result = repository.save(entity)
except Exception as e:
    logger.error(e)  # log i kontynuacja — maskuje błąd

# Nakaz — precyzyjny catch z re-raise lub transformacją
try:
    result = repository.save(entity)
except OSError as e:
    raise PersistenceError("Save failed") from e
```

**Wyjątek:** `except Exception` jest dozwolony wyłącznie na najwyższym poziomie aplikacji (główna pętla, entry point) jako ostatnia linia obrony — z obowiązkowym logowaniem i re-raise lub graceful shutdown.

### Wzorzec: globalny handler w bootstrap

Każdy entry point musi posiadać globalny handler który przechwytuje nieoczekiwane wyjątki, loguje je w formacie JSON (widoczne w CI i monitoringu) i kończy proces z kodem ≠ 0.

```python
# app.py (Streamlit) — globalny handler na najwyższym poziomie
import sys
from loguru import logger
from infrastructure.logging import configure_logging
from bootstrap import build_container


def main() -> None:
    configure_logging(json_mode=True)
    container = build_container()

    try:
        # Właściwa logika startowa aplikacji
        _run_app(container)
    except Exception:
        # Jedyne dozwolone miejsce dla bare except Exception
        # Obowiązkowe: logger.exception (nie logger.error) — zachowuje pełny traceback
        logger.exception("Unhandled exception — application shutting down")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

```python
# manage.py (Django CLI) — globalny handler dla komend
import sys
from loguru import logger

if __name__ == "__main__":
    try:
        from django.core.management import execute_from_command_line

        execute_from_command_line(sys.argv)
    except Exception:
        logger.exception("Unhandled exception in management command")
        sys.exit(1)
```

**Kluczowe zasady globalnego handlera:**
- `logger.exception(...)` zamiast `logger.error(...)` — automatycznie dołącza pełny traceback
- `sys.exit(1)` — proces kończy się z kodem błędu, CI to wykryje
- Bez re-raise — to jest ostatnia linia obrony, nie ma dokąd propagować
- Logowanie przed `sys.exit` — gwarantuje że log dotrze do stdout zanim proces się zakończy
- **Dlaczego `except Exception:` a nie puste `except:`?** Samo `except:` przechwytuje klasę bazową `BaseException`, do której należą `KeyboardInterrupt` (Ctrl+C) i `SystemExit`. Użycie `except Exception:` w globalnym handlerze to jedyny sposób, aby zalogować błąd działania kodu, jednocześnie nie blokując systemowych sygnałów wymuszających poprawne zatrzymanie aplikacji.

---

## Łańcuch wyjątków (`from e`)

Zawsze używaj `raise NewException(...) from e` — zachowuje oryginalny traceback i umożliwia debugowanie:

```python
# Nakaz:
raise PersistenceError("Save failed") from original_error

# Zakaz:
raise PersistenceError("Save failed")  # traci oryginalny kontekst
```

---

## Egzekwowanie

Ruff wykrywa zbyt szerokie wyjątki:

```toml
[tool.ruff.lint]
select = ["E", "F", "B"]
# B001: Do not use bare `except`
```

Mypy weryfikuje typy wyjątków w sygnaturach — jeśli metoda deklaruje `raises`, mypy sprawdzi że jest to podklasa właściwej hierarchii.


---

## Powiązanie z innymi kontraktami

| Kontrakt | Powiązanie |
|----------|-----------|
| Domain Purity | `DomainException` nie wychodzi poza `application/` — wynika z kierunku zależności |
| Logging & Monitoring | Globalny handler używa `logger.exception` z `infrastructure/logging.py` |
| Configuration Contract | `build_container()` w bootstrapie to jedyne miejsce gdzie wyjątki startowe są przechwytywane przez globalny handler |
| Determinism Contract | Wyjątki domenowe nie zawierają niedeterministycznych danych (czasu, UUID) — te są wstrzykiwane przez porty |
