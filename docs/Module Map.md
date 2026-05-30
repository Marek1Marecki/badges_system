# Module Map — mapa modułów

> **Wersja:** 1.1  
> **Data:** 2026-05-28  
> **Właściciel:** Dominik / AI Architect  
> **Zasada:** Każdy moduł (katalog) ma jedną, ściśle określoną odpowiedzialność. Zależności mogą kierować się wyłącznie do wewnątrz (w stronę `domain/`).

---

## Struktura katalogów

```text
/
├── domain/                 # Czyste reguły biznesowe i byty PTTK (100% niezależności)
├── application/            # Przypadki użycia (Use Cases), DTO i definicje Portów
├── infrastructure/         # Technologia, adaptery baz danych, zewnętrzne API, konfiguracja
├── apps/                   # Warstwa dostarczania (Django Apps) - interfejs użytkownika i modele ORM
├── bootstrap/              # Kontener Dependency Injection (DI) i inicjalizacja aplikacji
├── scripts/                # Niezależne skrypty diagnostyczne i audytorskie
├── tests/                  # Testy jednostkowe i integracyjne
│   └── fakes/              # Izolowane, in-memory implementacje Portów do testów
└── config/                 # Główne ustawienia frameworka Django i Celery
```

---

## Moduły — szczegółowy opis

### `domain/` — Czysta Domena Biznesowa
**Odpowiedzialność:** Zbiór pojęć, reguł matematycznych i polityk odznak PTTK. Nie wie nic o bazie danych, sieci ani frameworku.  
**Zarządza encjami:** `BadgeVersionDomain` (Agregat), `BadgeRule` (Wzorzec Strategii), `Ascent` (Value Object).  
**Eksportuje:** Encje, Reguły (np. `MinAgeRule`), Wyjątki domenowe (`ValidationError`).  
**Zależy od:** Wyłącznie `stdlib` (biblioteki standardowej Pythona).  
**NIE zależy od:** Czegokolwiek spoza `stdlib`. Bezwzględny zakaz importu `django`, `pydantic`, `infrastructure` czy `application`.

---

### `application/` — Warstwa Aplikacji (Use Cases)
**Odpowiedzialność:** Orkiestracja przepływu danych. Pobiera dane z zewnątrz (przez DTO), wywołuje usługi infrastrukturalne (przez Porty) i deleguje ewaluację do Domeny.  
**Zarządza encjami:** Nie posiada własnych encji. Wymusza przepływ danych przez DTO.  
**Eksportuje:** `Use Cases` (wywoływane przez Django/Celery), `Ports` (kontrakty dla infrastruktury), `DTO` (Pydantic Models dla walidacji wejść/wyjść).  
**Zależy od:** `domain/`, `stdlib` oraz zewnętrznej biblioteki `pydantic` (wyłącznie w obrębie podkatalogu `application/dto/`).  
**NIE zależy od:** `infrastructure/` ani `apps/` (Zależność odwrócona przez interfejsy / Porty).

---

### `infrastructure/` — Warstwa Infrastruktury (Adaptery)
**Odpowiedzialność:** Implementacja technicznych szczegółów systemu. Gadanie z bazą danych (PostGIS), wysyłanie zapytań HTTP do OSM, obsługa logów i wczytywanie zmiennych środowiskowych.  
**Zarządza encjami:** Mapuje modele bazodanowe Django na czyste obiekty domenowe.  
**Eksportuje:** `Adapters` (implementacje Portów), `AppSettings` (Centralna konfiguracja), `configure_logging()`. Eksportuje również `RULES_SCHEMA` jako techniczny detal implementacyjny, dostarczany wyłącznie na użytek renderowania UI w `apps/badges/admin.py`.  
**Zależy od:** `application/` (by implementować jej Porty), `domain/` (by budować jej agregaty) oraz bibliotek (`httpx`, `django`, `pydantic-settings`, `loguru`).

---

### `apps/badges/` — Warstwa Dostarczania (Django Monolith)
**Odpowiedzialność:** Interfejs użytkownika (Django Admin), schemat relacyjny bazy danych (Modele ORM) oraz punkty wejścia dla operacji asynchronicznych (Taski Celery).  
**Uwaga architektoniczna:** Koncepcyjnie `apps/` jest przedłużeniem warstwy infrastruktury, jednak dla narzędzia `import-linter` traktowane jest jako osobna warstwa w celu najwyższej precyzji egzekwowania kontraktów.  
**Eksportuje:** Widoki, panele administracyjne i cienkie wrappery zadań (`tasks.py`), które jedynie delegują pracę do Use Case'ów.  
**Zależy od:** `bootstrap/` (by pobrać wstrzyknięte Use Case'y) oraz własnych modeli (ORM).

---

### `bootstrap/` — Kompozycja Systemu (Dependency Injection)
**Odpowiedzialność:** Inicjalizacja całej aplikacji. "Drutuje" (wires up) adaptery z infrastruktury z przypadkami użycia z warstwy aplikacji. To JEDYNE miejsce w systemie produkcyjnym, które wie o istnieniu obu tych warstw równocześnie.  
**Eksportuje:** `get_container()` (zwraca słownik zainstancjonowanych Use Case'ów), `configure_app()`.  
**Zależy od:** `application/` oraz `infrastructure/`.

---

### `tests/fakes/` — Test Doubles
**Odpowiedzialność:** In-memory, szybkie i deterministyczne implementacje Portów do testów jednostkowych (np. `FakeBadgeRepository`, `FakeClock`).  
**Zasada:** Implementują interfejsy z `application/ports/`.  
**NIE zależy od:** Nigdy nie importują z `infrastructure/` ani `apps/`.

---

### `scripts/` — Niezależne narzędzia diagnostyczne
**Odpowiedzialność:** Jednorazowe skrypty audytorskie i raportujące (np. `check_badge_pools.py`, `audit_contracts.py`). NIE są częścią cyklu życia aplikacji produkcyjnej.  
**Zależy od:** Mogą importować z dowolnej warstwy w systemie – to narzędzia inspekcyjne, których nie obowiązują zasady czystości domeny.

---

### `config/` — Konfiguracja frameworka
**Odpowiedzialność:** `settings.py`, `urls.py`, `celery.py` — pliki wymagane do uruchomienia procesów bazowych Django i Celery.  
**Zasada:** Wyłącznie konfiguracja. Kategoryczny zakaz umieszczania tu jakiejkolwiek logiki biznesowej.

---

## Zasady importowania (Import Strictness)

Ten projekt korzysta z rygorystycznych linterów (`import-linter`, `ruff TID251`), aby zapobiec powstawaniu tzw. kodu spaghetti. Agenci LLM **muszą** przestrzegać poniższych reguł pod groźbą złamania pipeline'u CI:

1. **Bezwzględne aliasy:** Zawsze używaj pełnych ścieżek od korzenia projektu (np. `from application.dto.ascent_dto import ...`). Zakaz używania relatywnych ścieżek (`from ...domain import`).
2. **Kierunek zależności (Złota Reguła):** Importy mogą wskazywać tylko "w dół" architektury:
   - `domain/` importuje **tylko** ze standardowej biblioteki Pythona (`stdlib`).
   - `application/` importuje z `domain/`, `stdlib` oraz `pydantic` (ten ostatni **wyłącznie** w `application/dto/`).
   - `infrastructure/` importuje z `application/`, `domain/` i zewnętrznych bibliotek.
3. **Taski to tylko wrappery:** Pliki w `apps/badges/tasks.py` nie mogą wewnątrz logiki wywoływać zapytań ORM z `apps/badges/models.py`. Muszą pobrać przygotowany Use Case z `bootstrap.get_container()` i jemu delegować polecenie.

---

## Mapa zależności architektonicznych

```text
apps/ (UI/Tasks) ─────► bootstrap/ (DI Container) ◄───── infrastructure/ (Adapters)
                               │                                │
                               │                                │
                               ▼                                ▼
                       application/ (Use Cases & Ports) ────────┘
                               │
                               │
                               ▼
                       domain/ (Pure Business Logic)
```

*(Strzałki oznaczają "Zależy od / Importuje z")*

---

## Historia zmian

| Wersja | Data | Autor | Opis zmiany |
|--------|------|-------|-------------|
| 1.0 | 2026-05-28 | Dominik / AI Architect | Pierwsza wersja, stabilizująca strukturę heksagonalną po refaktoryzacji. |
| 1.1 | 2026-05-28 | AI Architect | Doprecyzowano zasady importu Pydantic, dwoistość `apps/`, status `RULES_SCHEMA` oraz zdefiniowano role katalogów `scripts/`, `config/` i `tests/fakes/`. |
