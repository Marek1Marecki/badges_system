# Architecture Debt Register

> **Wersja:** 1.1  
> **Data:** 2026-08-26  
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

### DŁUG-001: Zadania Celery wywołują OSMAdapter bezpośrednio

| Pole | Wartość |
|------|---------|
| **Tytuł** | `apps.badges.tasks` importuje `infrastructure.adapters.osm_adapter` |
| **Kategoria** | domain |
| **Powiązany ADR** | ADR-001 (Hexagonal Architecture), ADR-004 (Dwuwarstwowy model OSM) |
| **Wpływ** | Naruszenie czystości architektury; zadania Celery nie mogą korzystać z Application Service |
| **Remediacja** | Przenieść retry logic do Application Service; task pozostaje cienkim wrapperem |
| **Status** | open |

**Szczegóły:**
- `.importlinter` wyjątek: `apps.badges.tasks -> infrastructure.adapters.osm_adapter`
- Zadanie `fetch_osm_data` wywołuje `OsmAdapter` bezpośrednio, aby łapać `OsmAdapterError` i uruchamiać retry logic

---

### DŁUG-002: Model Django importuje schemat JSONB

| Pole | Wartość |
|------|---------|
| **Tytuł** | `apps.badges.models` importuje `infrastructure.schemas.badge_rules_schema` |
| **Kategoria** | domain |
| **Powiązany ADR** | ADR-001 (Hexagonal Architecture), ADR-003 (Silnik Reguł Biznesowych) |
| **Wpływ** | Naruszenie czystości architektury; logika walidacji w modelu Django |
| **Remediacja** | Przenieść walidację schematu do `admin.py` lub Application Service |
| **Status** | open |

**Szczegóły:**
- `.importlinter` wyjątek: `apps.badges.models -> infrastructure.schemas.badge_rules_schema`
- `TouristObject.clean()` importuje schemat JSONB do walidacji

---

### DŁUG-003: Context Processor importuje config map layers

| Pole | Wartość |
|------|---------|
| **Tytuł** | `apps.tourists.context_processors` importuje `infrastructure.config.map_layers` |
| **Kategoria** | infrastructure |
| **Powiązany ADR** | ADR-001 (Hexagonal Architecture), ADR-010 (Dynamiczne kolorowanie mapy) |
| **Wpływ** | Context Processor w Django wstrzykuje warstwy map bezpośrednio do kontekstu szablonów |
| **Remediacja** | Wydzielić serwis konfiguracyjny zwracający DTO map dla interfejsów (Faza D) |
| **Status** | open |

**Szczegóły:**
- `.importlinter` wyjątek: `apps.tourists.context_processors -> infrastructure.config.map_layers`
- `tourist_profiles()` wczytuje `MapLayersConfig` bezpośrednio z infrastructure

---

### DŁUG-004: Adapter zdarzeń importuje nazwy zadań Celery

| Pole | Wartość |
|------|---------|
| **Tytuł** | `infrastructure.adapters.celery_event_publisher` importuje `apps.badges.tasks` |
| **Kategoria** | infrastructure |
| **Powiązany ADR** | ADR-001 (Hexagonal Architecture), ADR-003 (Silnik Reguł Biznesowych) |
| **Wpływ** | Infrastructure importuje z Delivery layer; brak abstrakcji na rejestrację zdarzeń |
| **Remediacja** | Zastąpić bezpośredni import rejestracją opartą na nazwie ciągu znaków (string-based registry) |
| **Status** | open |

**Szczegóły:**
- `.importlinter` wyjątek: `infrastructure.adapters.celery_event_publisher -> apps.badges.tasks`
- `CeleryEventPublisher` importuje nazwy zadań Celery do rejestracji w endpointie wiadomości

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

### DŁUG-011: Niskie pokrycie testami adapterów persistence

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

### DŁUG-012: Zależność `apps` od `infrastructure` w modelach i widokach

| Pole | Wartość |
|------|---------|
| **Tytuł** | Delivery layer importuje z infrastructure w modelach i widokach |
| **Kategoria** | domain |
| **Powiązany ADR** | ADR-001 (Hexagonal Architecture), ADR-016 (Model Rodzinny) |
| **Wpływ** | Naruszenie czystości architektury, trudności z testowaniem |
| **Remediacja** | Przenieść logikę z `apps/badges/models.py` i `apps/tourists/views.py` do `application/` |
| **Status** | open |

**Szczegóły:**
- `apps/badges/models.py` zawiera logikę biznesową (`clean()`, walidacje)
- `apps/tourists/views.py` zawiera logikę przekazywania między warstwami

---

### DŁUG-013: Hardcoded URL-e Overpass API

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

### DŁUG-014: Brak abstrakcji na zewnętrzne API OSM

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

## Podsumowanie

| Kategoria | Liczba długów | Status |
|-----------|---------------|--------|
| domain | 3 | open |
| infrastructure | 3 | open |
| data | 2 | open |
| testing | 2 | open |
| operational | 1 | open |
| security | 1 | open |
| performance | 1 | open |

**Rekomendacja priorytetów:**
1. **Wysoki:** DŁUG-001 (tasks→osm_adapter), DŁUG-008 (rate limiting), DŁUG-009 (monitoring)
2. **Średni:** DŁUG-002 (models→schema), DŁUG-004 (event publisher→tasks), DŁUG-006 (indeksy)
3. **Niski:** DŁUG-003 (context→map_layers), DŁUG-005 (walidacja JSONB), DŁUG-007 (E2E), DŁUG-010 (archiwizacja), DŁUG-011..014 (pokrycie testów, architektura, hardcoded URLs, HTTP client)

---

## Historia zmian

| Wersja | Data | Autor | Opis zmiany |
|--------|------|-------|-------------|
| 1.1 | 2026-08-26 | Dominik / AI Architect | Zsynchronizowano numerację DŁUG-001..004 z `.importlinter`; przeniesiono poprzednie wpisy na DŁUG-011..014 |
| 1.0 | 2026-08-25 | Dominik / AI Architect | Utworzenie rejestru długów architektonicznych |
