# Schemathesis — Experimental Baseline

Data: 2026-08-27

## Kontekst

Schemathesis uruchamiany jako `make experimental-schemathesis` przeciwko
ręcznie utrzymywanemu `config/openapi.json`. Narzędzie pozostaje w tierze
**Experimental** — nie bierze udziału w `make check`, nie blokuje release'ów,
wynik interpretowany jest diagnostycznie, a nie jako binary pass/fail.

## Wynik baseline

| Metryka | Wartość |
|---------|---------|
| Operations | 13 |
| Server errors (5xx) | 0 |
| Invalid authentication | 0 |
| Known auth limitations | 10 operacji wymaga session cookie |
| Known method limitations | Schemathesis wysyła `QUERY`, Django zwraca 403 |
| Undocumented responses | 10 |
| Unsupported methods | 4 |
| Stateful scenarios | 108 passed / 1 failed (auth limitation) |

## Klasyfikacja pozostałych niepowodzeń

### Oczekiwane / Znane (nie są findingami)

- **Authentication limitations** — 10 operacji zwraca 401/403, bo Schemathesis
  nie ma `sessionid` cookie. To nie jest bug API.
- **Unsupported methods** — Schemathesis testuje metodę `QUERY`, której
  OpenAPI nie deklaruje. Django/middleware zwraca 403 zamiast 405.
- **Undocumented HTTP status codes** — częściowo spowodowane powyższymi
  limitationami, częściowo niepełną specyfikacją OpenAPI.

### Nieoczekiwane (realne findingi) — wszystkie naprawione

- `GET /api/v1/objects/22236/nearby/` → **HTTP 500**
  - Przyczyna: `Http404` był przechwytywany przez middleware
    `RFC7807ErrorMiddleware.process_exception` i zamieniany w 500
  - Naprawa: `infrastructure/middleware/error_handling.py:71` —
    `Http404` i `PermissionDenied` nie są już traktowane jako awarie serwera

## Wnioski

1. **Schemathesis znalazł realny defect** — bug w middleware, który nie został
   wykryty przez istniejące testy. To potwierdza wartość eksperymentu.
2. **Ręcznie utrzymywany OpenAPI jest wystarczający** — nie potrzeba DRF ani
   generatora OpenAPI, żeby uzyskać użyteczne wyniki.
3. **Kontrakt API się ustabilizował** — `test_api_contract_consistency.py`
   pilnuje synchronizacji między `urls.py` a `openapi.json`.
4. **Nie ma potrzeby dążenia do 13/13 passed** — artefaktowe "zielone" uruchomienie
   nie jest celem. Ważniejsze jest, czy liczba nieoczekiwanych zachowań
   rośnie.

## Kryterium awansu do tieru Diagnostic (propozycja)

Schemathesis może być awansowany, gdy spełnione zostaną:

- [ ] OpenAPI obejmuje 100% endpointów API
- [ ] Security schemes są w pełni zdefiniowane dla wszystkich endpointów
- [ ] Wszystkie realne response codes są udokumentowane
- [ ] Znaleziono sposób na deterministyczne uruchomienie z auth context
- [ ] Nie ma nieoczekiwanych findingów przez co najmniej 3 uruchomienia

## Pliki powiązane

- `config/openapi.json` — ręcznie utrzymywany kontrakt API
- `config/urls.py` — endpoint `api/openapi.json` serwujący schemat
- `tests/architecture/test_api_contract_consistency.py` — test synchronizacji
- `infrastructure/middleware/error_handling.py` — naprawiony middleware
