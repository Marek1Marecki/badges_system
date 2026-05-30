# Error Handling — standard obsługi błędów REST API

> **Wersja:** 1.1  
> **Data:** 2026-05-29  
> **Właściciel:** Dominik / AI Architect  
> **Zasada naczelna dla agentów LLM:** W całym projekcie (szczególnie w API z Fazy C) obowiązuje bezwzględny standard `RFC 7807 Problem Details`. 

---

## Globalny format błędu (RFC 7807 Problem Details)

Każda odpowiedź błędna z API (np. dla aplikacji mobilnej turysty) musi mieć następującą strukturę JSON:

```json
{
  "type": "https://api.pttk-badges.pl/errors/validation-failed",
  "title": "Błąd Walidacji Reguł Biznesowych",
  "status": 422,
  "detail": "Twoje wejście nie spełnia warunków odznaki.",
  "instance": "/api/v1/ascents/1234/verify",
  "request_id": "req_01HXZ92P..."
}
```

### Pola rozszerzone (tylko dla statusu 422)

Dla błędów walidacji (i **wyłącznie** dla nich, czyli np. po odrzuceniu przez Czystą Domenę), payload może zawierać tablicę `errors` z odwołaniem do kodów Invariantów z `INVARIANTS.md`:

```json
{
  "type": "https://api.pttk-badges.pl/errors/validation-failed",
  "title": "Validation failed",
  "status": 422,
  "detail": "Odrzucono próbę wejścia.",
  "instance": "/api/v1/ascents",
  "request_id": "req_01HXZ92P...",
  "errors": [
    { "code": "T-01", "message": "Obiekt nie istniał fizycznie w dacie wejścia (2014-05-01)." },
    { "code": "R-02", "message": "Minimalny wiek zdobywającego nie został osiągnięty." }
  ]
}
```

---

## Hierarchia klas błędów w Pythonie

Twarda zależność dziedziczenia w projekcie. Wyjątki rzucane z warstwy `domain/` oraz `application/` muszą dziedziczyć z `AppError`.

```text
AppError (bazowa)
├── DomainError (4xx — naruszenie reguł biznesowych z domain/)
│   ├── ValidationError (422 — Odrzucenie przez regułę)
│   ├── BitemporalTimeError (422 — Odrzucenie przez Invariant T-01)
│   └── ConflictError (409 — Konflikt logiki, powtórne zapisanie)
│       └── IllegalStateTransitionError (409 — Błędna zmiana w Kanban)
├── ApplicationError (400 — błędy orkiestracji i przepływu z application/)
│   └── UseCaseError (400 — Odrzucenie wykonania zadania, np. błędny stan wejściowy)
├── ResourceError (404)
│   ├── BadgeNotFoundException
│   └── TouristObjectNotFoundException
├── AuthError (401/403)
│   └── PermissionDeniedError
└── InfrastructureError (5xx — błędy z adapterów)
    └── OsmAdapterError (502 — Awaria API zewnętrznego)
```

---

## Mapowanie Wyjątków: Domena → Kod HTTP

| Wyjątek w Kodzie Python | Kod HTTP | `type` (URL)                      | Przyczyna |
|-----------------------|----------|-----------------------------------|-----------|
| `UseCaseError` | `400 Bad Request` | `/errors/use-case-aborted`         | Błąd orkiestracji, np. brak autoryzacji do podjęcia cyklu, niespełnienie warunku przedwstępnego wymaganego przez Port. |
| `ValidationError` | `422 Unprocessable` | `/errors/validation-failed`       | Silnik w Czystej Domenie odrzucił log wejścia (Set Math). |
| `BitemporalTimeError` | `422 Unprocessable` | `/errors/bitemporal-error`        | Wejście poza oknem `existence_start / end` (Invariant T-01). |
| `IllegalStateTransitionError` | `409 Conflict` | `/errors/invalid-state-transition` | Próba niedozwolonej zmiany statusu logistyki (Kanban). |
| `BadgeNotFoundException` | `404 Not Found` | `/errors/resource-not-found`      | Odznaka lub Obiekt Turystyczny o podanym ID nie istnieje w bazie. |
| `PermissionDeniedError` | `403 Forbidden` | `/errors/permission-denied`       | Turysta próbuje modyfikować logi innego użytkownika. |
| `OsmAdapterError` | `502 Bad Gateway` | `/errors/upstream-api-error`      | Awaria pobierania z OSM API (Występuje **tylko** u Admina). |
| `[Unexpected Exception]`| `500 Internal Error` | `/errors/internal-error`          | Błąd serwera. Zero stacktrace na froncie. Zawsze stały komunikat. |

---

## Wzorzec Globalnego Handlera (Django Middleware)

W architekturze opartej na Django, unifikacja błędów jest rozwiązywana poprzez napisanie centralnego Middleware, który wyłapuje wszystkie nieobsłużone w widokach instancje `AppError` (oraz ucieczki `Exception`). Dzięki temu poszczególne widoki API w `apps/` nie dublują kodu blokami `try/except`.

```python
# infrastructure/middleware/error_handling.py
import uuid
import traceback
from django.http import JsonResponse
from loguru import logger
from application.exceptions import AppError

class RFC7807ErrorMiddleware:
    """Middleware formatujący wyjątki do standardu RFC 7807 Problem Details."""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Wstrzyknięcie unikalnego request_id do kontekstu każdego zapytania
        request.request_id = f"req_{uuid.uuid4().hex[:8]}"
        
        # Pchamy request_id do globalnego kontekstu Loguru
        with logger.contextualize(request_id=request.request_id):
            try:
                return self.get_response(request)
            except AppError as exc:
                # 2. Obsługa znanych błędów domenowych (4xx)
                payload = {
                    "type": f"https://api.pttk-badges.pl/errors/{exc.error_type}",
                    "title": exc.title,
                    "status": exc.status_code,
                    "detail": str(exc),
                    "instance": request.path,
                    "request_id": request.request_id,
                }
                
                # Opcjonalne dołączenie listy błędów walidacyjnych, jeśli istnieją i status to 422
                if exc.status_code == 422 and getattr(exc, "errors", None):
                    payload["errors"] = exc.errors
                    
                return JsonResponse(payload, status=exc.status_code)
                
            except Exception as exc:
                # 3. ZASADA 500: Nieoczekiwane błędy serwera (Zabezpieczenie przed wyciekiem)
                logger.error("Nieobsłużony błąd serwera", exc_info=True)
                
                payload = {
                    "type": "https://api.pttk-badges.pl/errors/internal-error",
                    "title": "Wewnętrzny Błąd Serwera",
                    "status": 500,
                    "detail": "Wystąpił nieoczekiwany problem z przetworzeniem zapytania.",
                    "instance": request.path,
                    "request_id": request.request_id,
                }
                return JsonResponse(payload, status=500)
```

*(Middleware należy dodać do `settings.py` na początku listy `MIDDLEWARE`).*

---

## Zasady dla agentów LLM (Strict Guidelines)

### ❌ Zakazane
- Rzucanie gołego `Exception` w Use Case'ach i Domenie — zawsze używaj klasy z hierarchii powyżej.
- Zwracanie z widoku API płaskiego `{"error": "message"}` lub `{"detail": "..."}` zamiast pełnego słownika RFC 7807.
- Zwracanie `status: 200 OK` z payloadem zawierającym pole `error` (tzw. GraphQL Error Pattern nie obowiązuje w REST API).
- Zwracanie tablicy rozszerzonej `errors[]` dla kodów innych niż `422 Unprocessable Entity` (np. dla 404 lub 409 tablica `errors` jest niedozwolona).
- Logowanie całego `stacktrace` na poziomie innym niż `ERROR` / `CRITICAL`.
- Ukrywanie błędu w Use Case za pomocą pustego bloku `except Exception: pass`. (Wyjątek musi być wyrzucony ponownie (Re-raise) za pomocą `from e`, np. `raise DomainValidationError(...) from e`).

### ✅ Wymagane
- Każdy błąd 500 (np. zerwanie połączenia z bazą, bug w kodzie) logowany jest z pełnym rzutem stosu po stronie serwera (`exc_info=True`) i absolutnie "sterylną" odpowiedzią dla użytkownika końcowego.
- Każdy konstruowany ręcznie `JsonResponse` błędu musi obligatoryjnie posiadać pole `request_id`, by zapewnić traceability pomiędzy aplikacją mobilną a logami na serwerze (Kibana/Loki).

---

## Historia zmian

| Wersja | Data | Autor | Opis zmiany |
|--------|------|-------|-------------|
| 1.0 | 2026-05-29 | Dominik / AI Architect | Pierwsza wersja (Przed startem Fazy C). |
| 1.1 | 2026-05-29 | AI Architect | Usunięto odniesienia do FastAPI na rzecz wzorca Django Middleware. Uporządkowano listę zakazanych operacji dla agentów oraz zablokowano pole `errors[]` dla błędów o statusie innym niż 422. |