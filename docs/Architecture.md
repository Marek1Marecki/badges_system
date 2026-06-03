# Architecture

> **Wersja:** 1.2  
> **Data:** 2026-05-30  
> **Właściciel:** Dominik / AI Architect  
> **Status:** `approved`

---

## 1. Przegląd systemu

System Odznak Turystycznych PTTK to aplikacja webowa służąca do kompleksowego katalogowania obiektów geograficznych, definiowania regulaminów oraz weryfikacji postępów turystów. Zbudowana w rygorystycznej **Architekturze Heksagonalnej (Ports & Adapters)**, wykorzystuje framework **Django** wyłącznie jako mechanizm dostarczania (Delivery Mechanism) i zarządzania interfejsem administracyjnym. Warstwę infrastrukturalną i analitykę przestrzenną napędza **PostgreSQL z rozszerzeniem PostGIS**, zasilany asynchronicznie przez **Celery**.

---

## 2. Tech stack

| Warstwa | Technologia | Wersja             | Powód wyboru |
|---------|-------------|--------------------|--------------|
| **Frontend** | HTMX + MapLibre GL JS | `1.9.11` / `3.6.2` | Rezygnacja z React.js na rzecz Server-Side Renderingu. MapLibre zapewnia płynne renderowanie kafelków wektorowych (MVT) przy użyciu WebGL bez ciężkiego stacku JS. |
| **Backend** | Python + Django | `3.14` / `6.0.x`   | Django dostarcza wbudowany panel Admina z obsługą GIS (`django-leaflet`), co skraca czas wdrożenia narzędzi kuratorskich. Logika biznesowa izolowana w czystym Pythonie. |
| **Baza danych** | PostgreSQL + PostGIS | `15.x` / `3.x`     | Absolutny standard dla analityki przestrzennej. Niezbędny do buforowania granic i operacji na poligonach (`ST_Union`, `ST_DWithin`). |
| **Kolejka / Cache** | Redis | `7.x`              | Lekki i niezawodny broker komunikatów dla zadań asynchronicznych oraz magazyn wyników. |
| **Zadania w tle** | Celery + Celery Beat | `>=5.6.x`          | Zarządzanie długotrwałymi zadaniami (masowy import z OSM) oraz uruchamianie "Nocnego Stróża" z użyciem ponawiania (Linear Backoff). |
| **Zasilanie Danych**| Overpass API | —                  | Darmowe, potężne źródło surowych danych topograficznych z OpenStreetMap. |

---

## 3. Diagram komponentów

```text
┌─────────────────────────────────────────────────────────────────┐
│                             KLIENCI                             │
│  ┌─────────────────┐ ┌────────────────┐ ┌────────────────────┐  │
│  │ Administrator   │ │  Turysta (Web) │ │ Aplikacja Mobile   │  │
│  │ (Django Admin)  │ │ (HTMX + Map)   │ │ [Planowane-Faza D] │  │
│  └───────┬─────────┘ └──────┬─────────┘ └─────────┬──────────┘  │
└──────────┼──────────────────┼─────────────────────┼─────────────┘
           │                  │                     │
┌──────────▼──────────────────▼─────────────────────▼─────────────┐
│                    WARSTWA INFRASTRUKTURY                       │
│ ┌──────────────┐   ┌─────────────────┐   ┌──────────────────┐   │
│ │ Django Views │   │ Taski Celery    │   │  Adaptery OSM    │   │
│ │ & Admin Forms│   │ (Workers)       │   │  (Overpass HTTP) │   │
│ └──────┬───────┘   └───────┬─────────┘   └──────────────────┘   │
│        │                   │                                    │
│ ┌──────▼───────────────────▼──────────────────────────────────┐ │
│ │                  WARSTWA APLIKACJI (Use Cases)              │ │
│ │  - fetch_osm_data.py                                        │ │
│ │  - calculate_object_regions.py                              │ │
│ │  - verify_badge.py                                          │ │
│ └──────┬──────────────────────────────────────────┬───────────┘ │
│        │ (Implementuje Porty)                     │ (Używa)     │
│ ┌──────▼─────────────────────┐           ┌────────▼─────────┐   │
│ │  Adaptery Bazy Danych      │           │  CZYSTA DOMENA   │   │
│ │  (Django ORM + PostGIS)    │──────────►│  - Entities      │   │
│ └──────┬─────────────────────┘ (Mapuje do)  - JSON Rules    │   │
│        │                                 │  - Set Math      │   │
└────────┼─────────────────────────────────┴──────────────────┘   │
         │
┌────────▼──────────────────────────────────────────────┐
│                    MAGAZYN DANYCH                     │
│  [PostgreSQL + PostGIS]         [Redis]               │
│  (Write Models, Read Models)    (Celery Broker)       │
└───────────────────────────────────────────────────────┘
```

---

## 4. Granice systemu — co jest w scope, co nie

**W scope (Odpowiedzialność systemu):**
- Autorytatywne katalogowanie fizycznych obiektów z ich cyklem życia (Bitemporalność).
- Płaskie modelowanie przynależności terytorialnej (CQRS) dla optymalizacji filtrowania.
- Dynamiczne renderowanie kafelków wektorowych (MVT) na podstawie bazy danych.
- Bezstanowa weryfikacja logów turysty względem elastycznych reguł (Wzorzec Strategii).

**Poza scope (Celowo ignorowane):**
- **Nawigacja i Routing:** System nie służy do wyznaczania tras (turn-by-turn) ani liczenia odległości przejścia szlakiem między punktem A i B.
- **Data Hoarding:** System nie replikuje całego OpenStreetMap. Pobiera i aktualizuje tylko obiekty jawnie zażądane przez administratora (Curated Catalog).
- **Automatyczna weryfikacja GPS:** Aplikacja nie weryfikuje turysty śladem GPX. Dowodzenie obecności (np. zdjęcia, pieczątki) jest sprawdzane przez człowieka w procesie logistycznym. Domena ufa danym wprowadzonym przez autoryzowany log.

---

## 5. Kluczowe decyzje architektoniczne (ADR)

| ADR | Decyzja | Implikacje dla kodu |
|-----|---------|---------------------|
| [ADR-001] | Django + Celery + PostGIS | Architektura musi izolować Django ORM od Czystej Domeny. Zależność od GDAL. |
| [ADR-002] | Geometria jako transport | Obiekty PostGIS (Point, MultiPolygon) nigdy nie wchodzą do warstwy `domain/`. |
| [ADR-003] | Wzorzec Strategii i JSONB | Konfiguracja reguł trzymana jako `JSONB` i obsługiwana dynamicznym panelem (`oneOf`). |
| [ADR-004] | Dwuwarstwowy import OSM | Baza posiada ukryty Data Lake (`osm_raw_tags`) oraz Twarde Kolumny (Data Override). |
| [ADR-005] | Płaski Model Odczytu CQRS | Weryfikacja regionalna i filtrowanie oparte na asynchronicznej, płaskiej tabeli `ObjectRegionCache`. |
| [ADR-006] | Klastrowanie bliskości (Radar) | Zastosowanie pola `parent_object` zarządzanego przez asynchroniczną Skrzynkę Odbiorczą (Inbox). |
| [ADR-007] | Hierarchia Odznak (Wersje) | Gwarancja "Praw Nabytych" poprzez powiązanie postępu z niezmienną Wersją regulaminu. |
| [ADR-008] | Bitemporalność Obiektów | Ochrona historii wejść poprzez `existence_start` i `existence_end` (puste daty = brak limitu). |
| [ADR-009] | Pool-based Set Verification | Weryfikacja to szybkie przecięcia zbiorów (`frozenset`) w RAM, odcięte od zapytań GIS. |
| [ADR-010] | Dynamiczne kolorowanie mapy | `BadgeEligibilityService` redukuje stany na backendzie do 1 koloru; agresywny cache w Redis. |
| [ADR-011] | Hybrydowy BBox na żądanie | Zapytania mapowe (Pan/Zoom) odpytują pre-filtr CQRS, a następnie docinają wynik przez `ST_Within`. |
| [ADR-012] | Wildcard Geographic Rules | Reguły "terytorialne" bazują na `region_ids` wstrzykniętych w zhydrowanym DTO (Obejście R-01). |
| [ADR-013] | Vector Tiles & Client-Side Styling | MVT tylko dla statycznej geometrii (anonimowe). GeoJSON z BBox tylko dla dynamicznych stanów (`peak_color`). |
| [ADR-014] | Separacja Postępu od Logistyki | Domena wydaje wyrok `COMPLETED`, a proces śledzenia blachy to niezależny Kanban Turysty. |
| [ADR-015] | Ranking Potencjału (100/n) | Asynchroniczny silnik liczący opłacalność celów z systemem Event-Driven Cache Invalidation. |
*(Pełna dokumentacja decyzji dostępna w folderze `/docs/adr/`)*.

---

## 6. Observability — logi i metryki

### Poziomy logowania (Loguru)

| Poziom | Kiedy używać | Przykład |
|--------|-------------|---------|
| `DEBUG` | Detale zapytań HTTP do OSM, szczegóły transformacji GEOS. | `Pobieranie OSM ID: node/123 (Attempt 1/3)` |
| `INFO` | Intencje biznesowe i zmiany stanu obiektów (Taski Celery). | `Sukces: Przeliczono obiekt 'Rysy'. Znaleziono 3 regiony.` |
| `WARNING` | Odrzucenia zapytań przez zaporę, brakujące tagi, ciche pominięcia. | `Błąd przy masowym pobieraniu OSM: HTTP 406 Not Acceptable` |
| `ERROR` | Wyjątki domenowe wymuszające przerwanie Use Case'a. | `Błąd hydracji reguły 'MinAgeRule': brak klucza 'min_age'` |
| `CRITICAL`| Ostateczne awarie uniemożliwiające start aplikacji lub weryfikację. | `Database connection lost during atomic transaction` |

**Zasady dla agentów LLM:**
- Logowanie odbywa się **wyłącznie** w warstwie `infrastructure/` (np. Taski Celery, Adaptery).
- `domain/` oraz `application/use_cases/` są całkowicie wolne od loggera. Zgłaszają problemy wyłącznie poprzez rzucanie wyjątków (np. `UseCaseError`).
- W produkcji logger działa w trybie JSON (`serialize=True`).

### Metryki
*Metryki systemowe (Prometheus/Datadog) oraz integracja z systemem powiadomień błędów zostaną zdefiniowane i zaimplementowane w **Fazie C** (przy wejściu ruchu od użytkowników).*

---

## Historia zmian

| Wersja | Data | Autor | Opis zmiany |
|--------|------|-------|-------------|
| 1.0 | 2026-05-27 | Dominik / AI Architect | Pierwsza wersja (Inicjalizacja po zamknięciu Fazy B) |
| 1.1 | 2026-05-27 | AI Architect | Doprecyzowano wersje tech stacku, poprawiono diagram (izolacja Domeny od adaptera), zaktualizowano macierz ADR i dodano placeholder na Metryki. |
| 1.2 | 2026-05-30 | | Poprawiono wersję Celery w tabeli technologii.|
