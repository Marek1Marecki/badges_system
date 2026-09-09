# ADR-030 — Distributed Tracing via ContextVar and Celery Headers

> **Status:** `accepted`  
> **Date:** 2026-09-09  
> **Author:** AI Architect (AUT-117)  
> **Implements:** AUDYT-117 (Log Correlation: HTTP ↔ Celery)  
> **Replaces:** [Brak]  

---

## Kontekst

Nasze środowisko opiera się na architekturze Hexagonal / Clean Django z trzema warstwami: Domena, Use Cases (aplikacja), i Adaptery (infrastruktura HTTP + Celery).

Każde przychodzące żądanie HTTP otrzymuje unikalne `request_id` przydzielane w `RFC7807ErrorMiddleware`, które jest logowane w Gunicornie.

Wielu widoków przekazuje pracę do Celery (np. `recalculate_poi_scores_task`). Logi Celery **nie zawierały** `request_id`, uniemożliwiając korelację asynchronicznych błędów z konkretnym requestem HTTP ani turystą.

**Pytanie decyzyjne:**  
Jak przenieść `request_id` ze wątku HTTP do wątku Celery bez naruszania czystości Domeny i bez przepchania `request_id` przez warstwę Use Cases jako parametr DTO?

---

## Opcje rozważane

### Opcja A: Parametr `request_id` w DTO i Use Case'ach

**Opis:** Przekazywanie `request_id` jako parametru do `UseCase.execute(profile_id, dto)` i `DomainEvent`.
**Plusy:** Proste, widoczne w sygnaturze.
**Minusy:** Narusza Clean Architecture — Domena i Use Cases stają się świadome kontekstu HTTP/observability, co jest leaky abstraction. `UserProgressStateChanged` przestaje być "czystym faktem biznesowym" i staje się eventem zależnym od infrastruktury.

### Opcja B: `contextvars.ContextVar` + Celery Headers + `task_prerun` hook (WYBRANA)

**Opis:** `request_id` jest przechowywany w `ContextVar` (`infrastructure/request_context.py`), propagowany przez Celery `headers={"request_id": ...}`, odczytywany w `task_prerun` hooku i ponownie ustawiany w ContextVar wewnątrz workera Celery.
**Plusy:** Zero naruszenia warstw Domeny i Use Cases. `UserProgressStateChanged` wraca do stania się obiektywnym faktem biznesowym. Pełna kompatybilność z Celery. Działa jak ubogi OpenTelemetry na poziomie aplikacji.
**Minusy:** `contextvars` nie propaguje się automatycznie przez granice procesów — wymaga ręcznej propagacji przez `headers`. Wymaga modyfikacji `config/celery.py`, `CeleryEventPublisher`, i middleware.

---

## Decyzja

Wybrana **Opcja B: ContextVar + Celery Headers + `task_prerun`**.

Zasady wdrożenia:

1. **`infrastructure/request_context.py`** — nowy moduł z `ContextVar[str]` o nazwie `request_id`, zapewniający `set_request_id()` / `get_request_id()`.
2. **`infrastructure/middleware/error_handling.py`** — `set_request_id()` wywoływane w kontekście HTTP, propagowane do Loguru via `logger.contextualize`.
3. **`config/celery.py`** — `@task_prerun.connect` hook odczytuje `sender.request.headers["request_id"]` i ustawia go w ContextVar.
4. **`infrastructure/adapters/celery_event_publisher.py`** — `CeleryEventPublisher.send_task()` przekazuje `headers={"request_id": get_request_id()}` do Celery.
5. **`apps/badges/tasks.py`** — `recalculate_poi_scores_task` (bind=True) odczytuje `get_request_id()` z ContextVar (już ustawionego przez hook) i loguje przez `logger.contextualize`.
6. **`domain/events.py`** — `UserProgressStateChanged` **nie posiada** `request_id` — jest czystym faktem biznesowym.
7. **`application/use_cases/log_ascent.py`** — `execute(profile_id, dto)` bez `request_id`.

---

## Konsekwencje

### Pozytywne
- Domena jest całkowicie odizolowana od kontekstu HTTP/observability.
- Logi Celery i Gunicorn są idealnie skorelowane — możliwe jest prześledzenie całego łańcucha żądania od HTTP → Use Case → DomainEvent → Celery Task.
- `UserProgressStateChanged` wraca do bycia obiektywnym faktem biznesowym (bez zależności od `request_id`), co wymuszał AUDYT-117.
- Nie wymaga zewnętrznych zależności (OpenTelemetry), działa na czystym Pythonie 3.10+.

### Negatywne / Działania wymagane
- `contextvars` nie propaguje się przez granice procesów w Celery — wymaga ręcznego przekazywania przez `headers`, co musimo pamiętać przy każdym nowym Tasku.
- `.importlinter` — dodano EXC-002: `apps.badges.tasks -> infrastructure.request_context` (celowy zależność jednokierunkowa).
- Testy jednostkowe Taska muszą używać `__wrapped__(profile_id=N)` + `patch("bootstrap.get_container")`, aby uniknąć Celery `bind=True` w `self`.

---

## Warunek rewizji

Zrewidować, gdy:
- Migracja na OpenTelemetry nastąpi (ADR-020 Deployment & SRE) — wtedy ContextVar może zostać zastąpiony przez natywny OTel context propagation.
- Uzyskamy potrzebę propagacji nie tylko `request_id`, ale też `trace_id` i `span_id` — może warto od razu wprowadzić OTel.

---

## Relacje (Related)
- **Backlog:** AUDYT-117 — formalne zamknięcie
- **Kontrakty:** `.importlinter:86` — EXC-002 ignore dla `apps.badges.tasks -> infrastructure.request_context`
- **Dług (Debt):** Brak. Dług techniczny został spłacony — `UserProgressStateChanged` nie jest już zanieczyszczony `request_id`.
