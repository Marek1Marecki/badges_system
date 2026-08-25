# Architecture Debt Register

> **Wersja:** 1.0  
> **Data:** 2026-08-25  
> **Właściciel:** Dominik / AI Architect  
> **Zasada:** Każdy wpis w rejestrze odnosi się do konkretnego ADR i ma ślad do remediacji.

---

## Format wpisu

| Pole | Opis |
|------|------|
| **ID** | Unikalny identyfikator: `DŁUG-NNN` |
| **Tytuł** | Krótki opis długu |
| **Kategoria** | `domain` / `infrastructure` / `data` / `security` / `performance` / `testing` / `operational` |
| **Powiązany ADR** | Decyzja, z której wynika dług |
| **Wpływ** | Co się stanie, jeśli dług nie zostanie spłacony |
| **Remediacja** | Jak długo spłacić |
| **Status** | `open` / `mitigated` / `resolved` |

---

## Rejestr długów

### DŁUG-001: Testy infrastruktury persistence mają niskie pokrycie

| Pole | Wartość |
|------|---------|
| **Tytuł** | Niskie pokrycie testami adapterów persistence |
| **Kategoria** | testing |
| **Powiązany ADR** | ADR-001 (Hexagonal Architecture) |
| **Wpływ** | Błędy w adapterach mogą zniszczyć dane użytkowników bez wykrycia w CI |
| **Remediacja** | Dodać testy integracyjne dla `django_tourist_repo.py`, `django_region_cache_repo.py`, `django_region_geometry_repo.py` |
| **Status** | open |

**Szczegóły:**
- `django_tourist_repo.py` — 22% coverage (116 statements, 90 missing)
- `django_region_cache_repo.py` — 20% coverage (71 statements, 57 missing)
- `django_region_geometry_repo.py` — 22% coverage (27 statements, 21 missing)

---

### DŁUG-002: Zależność `apps` od `infrastructure` w niektórych miejscach

| Pole | Wartość |
|------|---------|
| **Tytuł** | Delivery layer importuje z infrastructure |
| **Kategoria** | domain |
| **Powiązany ADR** | ADR-001 (Hexagonal Architecture), ADR-016 (Model Rodzinny) |
| **Wpływ** | Naruszenie czystości architektury, trudności z testowaniem |
| **Remediacja** | Przenieść logikę z `apps/badges/models.py` i `apps/tourists/views.py` do `application/` |
| **Status** | open |

**Szczegóły:**
- Import Linter wykrywa violations, ale nie blokuje merge'ów
- `apps/badges/models.py` zawiera logikę biznesową (`clean()`, walidacje)
- `apps/tourists/views.py` zawiera logikę przekazywania między warstwami

---

### DŁUG-003: Hardcoded URL-e Overpass API

| Pole | Wartość |
|------|---------|
| **Tytuł** | Hardcoded endpointy zewnętrznych API |
| **Kategoria** | infrastructure |
| **Powiązany ADR** | ADR-004 (Dwuwarstwowy model zasilania danych z OSM) |
| **Wpływ** | Brak możliwości zmiany endpointu bez zmiany kodu, trudności w testach |
| **Remediacja** | Przenieść URL-e do `infrastructure/config/` lub zmiennych środowiskowych |
| **Status** | open |

**Szczegóły:**
- `infrastructure/adapters/osm_adapter.py:63-67` — hardcoded lista URL-i Overpass
- `infrastructure/adapters/news_scraper.py` — prawdopodobnie podobny problem

---

### DŁUG-004: Brak abstrakcji na zewnętrzne API OSM

| Pole | Wartość |
|------|---------|
| **Tytuł** | Bezpośrednie użycie `requests` w adapterze OSM |
| **Kategoria** | infrastructure |
| **Powiązany ADR** | ADR-004 (Dwuwarstwowy model zasilania danych z OSM) |
| **Wpływ** | Trudności z testowaniem, brak możliwości podmiany implementacji HTTP |
| **Remediacja** | Wprowadzić `HttpClientPort` i `RequestsHttpClientAdapter` |
| **Status** | open |

**Szczegóły:**
- `infrastructure/adapters/osm_adapter.py` używa `urllib.request` i `requests` bezpośrednio
- Brak portu dla HTTP clienta w `application/ports/`

---

### DŁUG-005: Brak walidacji schematu JSONB w runtime

| Pole | Wartość |
|------|---------|
| **Tytuł** | Reguły biznesowe przechowywane jako JSONB bez walidacji w bazie |
| **Kategoria** | data |
| **Powiązany ADR** | ADR-003 (Silnik Reguł Biznesowych) |
| **Wpływ** | Nieprawidłowe reguły mogą trafić do bazy i spowodować błąd podczas weryfikacji |
| **Remediacja** | Dodać constraint lub trigger PostgreSQL weryfikujący strukturę JSONB |
| **Status** | open |

**Szczegóły:**
- Walidacja odbywa się tylko na poziomie aplikacji (JSON Schema w adminie)
- Brak ochrony na poziomie bazy danych

---

### DŁUG-006: Brak indeksów na często filtrowanych kolumnach

| Pole | Wartość |
|------|---------|
| **Tytuł** | Brak indeksów na kolumnach używanych w filtrach |
| **Kategoria** | performance |
| **Powiązany ADR** | ADR-001 (Wybór stosu technologicznego) |
| **Wpływ** | Spowolnienie zapytań przy rosnącej liczbie rekordów |
| **Remediacja** | Dodać indeksy na `is_active`, `status`, `existence_end` w `TouristObject` |
| **Status** | open |

**Szczegóły:**
- Zapytania typu `filter(is_active=True, status="READY")` na dużych tabelach
- Brak indeksów złożonych na często używane kombinacje

---

### DŁUG-007: Brak testów E2E dla kluczowych ścieżek użytkownika

| Pole | Wartość |
|------|---------|
| **Tytuł** | Niskie pokrycie E2E dla ścieżek użytkownika |
| **Kategoria** | testing |
| **Powiązany ADR** | ADR-001 (Wybór stosu technologicznego) |
| **Wpływ** | Nie wykrycie błędów integracyjnych przed wdrożeniem na produkcję |
| **Remediacja** | Rozszerzyć testy E2E w `tests/e2e/` o scenariusze: subskrypcja odznaki, logowanie wejścia, zmiana profilu |
| **Status** | open |

**Szczegóły:**
- Obecne testy E2E: 18% coverage (116 statements, 93 missing)
- Brak testów dla: płatności, rejestracji, wielokrotnych profili

---

### DŁUG-008: Brak rate limiting na API

| Pole | Wartość |
|------|---------|
| **Tytuł** | Brak rate limiting na endpointach API |
| **Kategoria** | security |
| **Powiązany ADR** | ADR-016 (Rozdzielenie tożsamości od autoryzacji) |
| **Wpływ** | Ryzyko ataku DoS na API, nadużycie zasobów |
| **Remediacja** | Dodać rate limiting na poziomie middleware lub użyć Django Ratelimit |
| **Status** | open |

**Szczegóły:**
- Endpointy API nie mają limitów zapytań
- Ryzyko szczególnie przy publicznych endpointach (np. `/api/v1/map/objects/`)

---

### DŁUG-009: Brak monitoringu i alertów w produkcji

| Pole | Wartość |
|------|---------|
| **Tytuł** | Brak systemu monitorowania i alertów |
| **Kategoria** | operational |
| **Powiązany ADR** | ADR-020 (Architektura Wdrożeń) |
| **Wpływ** | Nie wykrycie awarii, spadku wydajności lub błędów biznesowych |
| **Remediacja** | Wdrożyć Sentry/Datadog dla błędów, Prometheus + Grafana dla metryk |
| **Status** | open |

**Szczegóły:**
- ADR-020 wspomina o monitoringu, ale nie ma implementacji
- Brak alertów na: błędy Celery, błędy API, zużycie bazy

---

### DŁUG-010: Brak strategii archive dla starych danych

| Pole | Wartość |
|------|---------|
| **Tytuł** | Brak strategii archiwizacji starych logów i postępów |
| **Kategoria** | data |
| **Powiązany ADR** | ADR-008 (Bitemporalność Obiektów Turystycznych) |
| **Wpływ** | Wzrost rozmiaru bazy, spowolnienie zapytań, koszty przechowywania |
| **Remediacja** | Zdefiniować politykę archiwizacji: po X latach przenieść dane do cold storage |
| **Status** | open |

**Szczegóły:**
- `AscentLog` rośnie liniowo z każdym nowym użytkownikiem
- Brak partycjonowania tabeli w czasie

---

## Podsumowanie

| Kategoria | Liczba długów | Status |
|-----------|---------------|--------|
| testing | 2 | open |
| domain | 1 | open |
| infrastructure | 2 | open |
| data | 2 | open |
| performance | 1 | open |
| security | 1 | open |
| operational | 1 | open |

**Rekomendacja priorytetów:**
1. **Wysoki:** DŁUG-001 (testy persistence), DŁUG-008 (rate limiting), DŁUG-009 (monitoring)
2. **Średni:** DŁUG-002 (architektura), DŁUG-004 (HTTP client), DŁUG-006 (indeksy)
3. **Niski:** DŁUG-003 (hardcoded URLs), DŁUG-005 (walidacja JSONB), DŁUG-007 (E2E), DŁUG-010 (archiwizacja)

---

## Historia zmian

| Wersja | Data | Autor | Opis zmiany |
|--------|------|-------|-------------|
| 1.0 | 2026-08-25 | Dominik / AI Architect | Utworzenie rejestru długów architektonicznych |
