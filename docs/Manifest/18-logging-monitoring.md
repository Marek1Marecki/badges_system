# Logging & Monitoring

**Status:** Referencyjny  
**Zakres:** Wszystkie projekty

---

## Egzekwowalne zasady

Te zasady można sprawdzić w CI lub runtime:

| Zasada | Egzekwowanie |
|--------|--------------|
| Logi na stdout/stderr | Testy kontenerów |
| Brak sekretów w logach | Testy jednostkowe |
| Endpoint `/health` | Runtime Integrity Tests |

**Zakaz:** pisania logów do plików w kontenerze produkcyjnym — Docker zbiera stdout/stderr, plik w read-only FS spowoduje błąd.

---

## Zalecana implementacja: Loguru

Standardowy moduł `logging` jest topory w konfiguracji JSON. Loguru jest zalecaną biblioteką warstwy infrastrukturalnej logowania.

**Warstwa:** wyłącznie `infrastructure/` — logowanie to szczegół implementacyjny, nie logika domenowa.  
**Zakaz:** `domain/` i `application/` nie importują Loguru bezpośrednio. (Patrz: Layer Dependency Matrix w `14-domain-purity.md`)

```python
# infrastructure/logging.py
import sys
from loguru import logger

def configure_logging(json_mode: bool = False) -> None:
    logger.remove()
    if json_mode:
        logger.add(sys.stdout, serialize=True)   # JSON dla produkcji
    else:
        logger.add(sys.stdout, colorize=True)    # Czytelny dla dev

# Wywołanie w bootstrap aplikacji (json_mode pochodzi z AppSettings — nie z os.getenv):
# configure_logging(json_mode=settings.app_env == "production")
```

Jeden JSON log w produkcji (`serialize=True`) — gotowy pod ElasticSearch/Loki bez dodatkowej konfiguracji.

```toml
# pyproject.toml — zależność produkcyjna, nie dev
dependencies = ["loguru>=0.7.0"]
```

---

## Format logu (obowiązkowy w produkcji)

```json
{
  "timestamp": "2026-02-19T12:34:56Z",
  "level": "INFO",
  "module": "app.module",
  "message": "Opis zdarzenia"
}
```

Loguru z `serialize=True` generuje ten format automatycznie.

---

## Poziomy logowania

| Poziom | Kiedy |
|--------|-------|
| `DEBUG` | Tylko lokalny development — wyłączony w produkcji |
| `INFO` | Operacje biznesowe, zdarzenia użytkowników |
| `WARNING` | Nietypowe, niekrytyczne sytuacje |
| `ERROR` | Błędy wymagające uwagi |
| `CRITICAL` | Awarie mogące zatrzymać proces |

---

## Zalecane dla projektów webowych: Correlation ID

Gdy wiele żądań jest obsługiwanych równolegle, logi JSON przeplatają się — bez unikalnego identyfikatora nie wiadomo które wpisy z `application/` i `infrastructure/` należą do tego samego żądania. Correlation ID rozwiązuje ten problem strukturalnie.

**Zakres:** Django / FastAPI — nie dotyczy projektów CLI, skryptów ML ani Streamlit.  
**Status:** Rekomendacja, nie kontrakt — nieegzekwowalne bez frameworka webowego.

Loguru implementuje to przez `logger.contextualize()` opartego o `contextvars` — thread-safe i asyncio-safe. Middleware wstrzykuje `request_id` raz, wszystkie logi w tym kontekście dziedziczą go automatycznie bez przekazywania przez warstwy.

```python
# infrastructure/middleware/correlation.py
import uuid
from loguru import logger

# Django middleware
class CorrelationIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = f"req_{uuid.uuid4().hex[:8]}"
        with logger.contextualize(request_id=request_id):
            response = self.get_response(request)
            response["X-Request-ID"] = request_id
            return response

# FastAPI middleware
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = f"req_{uuid.uuid4().hex[:8]}"
        with logger.contextualize(request_id=request_id):
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
```

Format logu z `request_id` (automatycznie dołączany przez Loguru):

```json
{
  "timestamp": "2026-02-19T12:34:56Z",
  "level": "INFO",
  "request_id": "req_5f8a9b2",
  "message": "Opis zdarzenia"
}
```

`request_id` w nagłówku odpowiedzi (`X-Request-ID`) pozwala skorelować błąd zgłoszony przez użytkownika z konkretnym wpisem w logach — debugowanie spada z godzin do minut.

---

## Aspiracyjne praktyki (przyszła infrastruktura)

Dobre praktyki dla większej skali — nieegzekwowalne bez dedykowanej infrastruktury:

| Praktyka | Uwaga |
|----------|-------|
| Prometheus metrics | Wymaga Prometheus |
| Grafana / Alertmanager | Wymaga osobnej infrastruktury |
| ELK / Loki / CloudWatch | Wymaga dedykowanej infrastruktury |
| Distributed tracing | Wymaga systemu śledzenia |
| Log rotation | Zależy od infrastruktury hosta |

---

## Filozofia

**Oddziel egzekwowalne od aspiracyjnych** — tylko to co można zweryfikować w CI jest kontraktem. Logi w produkcji muszą być na stdout/stderr i bez sekretów — reszta jest "nice to have" do momentu gdy infrastruktura monitoring jest gotowa.
