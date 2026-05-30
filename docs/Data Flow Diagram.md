# Data Flow Diagram

> **Wersja:** 1.1  
> **Data:** 2026-05-28  
> **Właściciel:** Dominik / AI Architect  
> **Uwaga dla agentów LLM:** Ten dokument opisuje, jak dane PORUSZAJĄ SIĘ przez system w ujęciu asynchronicznym i architektonicznym. Architektura komponentów jest w ARCHITECTURE.md.

---

## Notacja

- `→` dane przepływają synchronicznie (request/response, zapytanie do zewnętrznego API)
- `⇢` dane przepływają asynchronicznie (publikacja zadania do kolejki, event)
- `[X]` komponent / serwis / aktor
- `{Y}` format / typ danych
- `(Z)` magazyn danych (baza SQL, cache w RAM, Redis)

---

## Przepływ 1: Katalogowanie Obiektów (OSM Ingestion Pipeline)

### Opis
Administrator PTTK definiuje nowy szczyt w panelu, używając wyłącznie `osm_id`. System asynchronicznie dociąga wszystkie metadane i lokalizacje.

### Diagram

```text
[Administrator]
    │ {TouristObjectAdminForm: osm_id}
    ▼
[Django Admin]
    │ walidacja (unikalność)
    ├──► (DB: TouristObject) — Zapis ze statusem FETCHING_OSM
    └──► [Redis Broker] ⇢ {fetch_osm_data_task}
             │
        [Celery Worker 1]
             ├──► [Overpass API] → {OsmNodeDTO (JSON)}
             ├──► [OsmDataExtractor] — Wyciągnięcie Złotego Standardu (Curated)
             │
             ├──► (DB: TouristObject) — Zapis wys., nazwy, JSONB i geom
             └──► [Redis Broker] ⇢ {calculate_object_regions_task}
                      │
                 [Celery Worker 2]
                      ├──► [PostGIS] — ST_DWithin na EPSG:3857 (CQRS)
                      ├──► (DB: ObjectRegionCache) — Aktualizacja relacji M2M
                      └──► (DB: TouristObject) — Zapis statusu READY
```

### Transformacje (The Smart Extractor)
1. `osm_raw_tags` — pełny dump z Overpass bezstratnie ląduje w JSONB.
2. `name` — wyciągana priorytetowo z `name:pl`, faworyzując polskie nazwy.
3. `geom` — dla wielokątów z OSM (Schroniska / Zamki) przeprowadzana jest transformacja `out center meta;` na centroid, ignorując setki punktów łamanych.
4. `local_names` — ekstrakcja opóźniona w Worker 2; na podstawie `ST_DWithin` wyciągane są nazwy dla państw ościennych (np. węgierskie i czeskie tylko tam, gdzie to fizycznie sensowne przestrzennie).

---

## Przepływ 2: Nocny Stróż i Konflikty (Night Watchman Sync)

### Opis
Automatyczne, cykliczne odświeżanie najstarszych obiektów z OSM bez nadpisywania ręcznych edycji Administratora, ze wsparciem dla wykrywania usuniętych węzłów (Ghost Nodes).

### Diagram

```text
[Celery Beat] (np. 3:00 rano)
    │ ⇢ {run_osm_night_watchman_task}
    ▼
[Celery Worker]
    ├──► (DB: TouristObject) — Pobranie 100 najstarszych po last_sync_check
    ├──► [Overpass API] → {Zbiorczy słownik 100 JSON}
    │
    ├──► (DB: TouristObject) — Cichy update osm_raw_tags i last_sync_check
    │
    ├──► Konflikt Wysokości / Wiki?
    │        │ {OsmSyncConflict}
    │        ▼
    │   (DB: OsmSyncConflict) 
    │
    └──► Obiekt zniknął z OSM? (Ghost Node)
             │ {OsmSyncConflict: is_active=False}
             ▼
        (DB: OsmSyncConflict)
             │
      [Administrator] — Poranny przegląd Inboxu i Akceptacja/Odrzucenie w Panelu
```

---

## Przepływ 3: Budowanie Geometrii Regionów Turystycznych (CQRS Aggregation)

### Opis
Administrator definiuje Region Turystyczny (np. "Sudety") jako kompozycję mniejszych prowincji i makroregionów. System scala geometrie i dziedziczy obiekty.

### Diagram

```text
[Administrator]
    │ {Zaznaczenie mezoregionów/prowincji w panelu M2M}
    ▼
[Django Admin]
    ├──► (DB: TouristRegionModel) — Zapis relacji M2M składowych
    └──► [Redis Broker] ⇢ {build_tourist_region_geometry_task}
             │
        [Celery Worker]
             ├──► [PostGIS] — ST_UnaryUnion na geometriach składowych
             ├──► (DB: TouristRegionModel) — Zapis scalonego 'shape'
             └──► (DB: ObjectRegionCache) — Aktualizacja CQRS (Logiczne Dziedziczenie)
```

---

## Przepływ 4: Radar Bliskości i Klastrowanie (Proximity Scanner)

### Opis
Skaner przestrzenny szuka niepowiązanych obiektów leżących obok siebie, by zaproponować administratorowi utworzenie klastrów (relacja Parent-Child).

### Diagram

```text
[Administrator] (lub Harmonogram Celery Beat)
    │
    └──► [Redis Broker] ⇢ {scan_proximity_candidates_task}
             │
        [Celery Worker]
             ├──► [PostGIS] — ST_DWithin(150m) szuka par bez 'parent_object'
             │ {ProximityCandidate}
             ▼
        (DB: ProximityCandidate) — Skrzynka Odbiorcza
             │
[Administrator]
    │ Przegląd Inboxu i decyzja (np. "A jest rodzicem B" / "Ignoruj")
    ▼
[Django Admin]
    ├──► (DB: TouristObject) — Zapis relacji 'parent_object'
    └──► (DB: ProximityCandidate) — Status RESOLVED / IGNORED
```

---

## Przepływ 5: Weryfikacja Logów Turysty (Verification Bounded Context)
*Uwaga: Przepływ projektowany z myślą o pełnej implementacji w Fazie C.*

### Opis
Turysta wysyła wniosek o weryfikację. Silnik Domenowy sprawdza jego matematyczny postęp.

### Diagram

```text
[Turysta]
    │ {VerifyBadgeRequestDTO: ascents[]}
    ▼
[API Gateway]
    │
    ▼
[VerifyBadgeUseCase]
    ├──► [DjangoBadgeRepository]
    │        ├──► (DB: BadgeVersionModel) — Pobranie Puli i Reguł
    │        └──► (DB: BadgeTierModel) — Pobranie progów stopni
    │        │ {BadgeVersionDomain (Aggregate)}
    │        ▼
    ├──► [Czysta Domena]
    │        ├── [Set Math] — climbed_peak_ids.intersection(pool_peaks)
    │        ├── [Strategy Pattern] — ewaluacja MinAgeRule, TimeLimitRule
    │        │ {ValidationResult / DomainException}
    │        ▼
    ├──► Zapis do (DB: UserBadgeProgress)
    └──► Zwrócenie odpowiedzi do Turysty
```

### Dane chronione (Invarianty)
1. `VerifyBadgeUseCase` nigdy nie wykonuje zapytań GIS (`ST_DWithin`). Pracuje na zamkniętych zbiorach `frozenset[int]` *(Invariant R-01)*.
2. Odrzucenie reguły (np. brak wieku, zły termin) przerywa weryfikację całego stopnia (Fail-Fast).

---

## Magazyny danych

| Magazyn | Technologia | Co przechowuje | Retencja |
|---------|-------------|----------------|----------|
| Główna baza | PostgreSQL + PostGIS | Złoty Standard: modele domenowe, regulaminy, geometria, Data Lake OSM | Bezterminowo |
| CQRS Cache | PostgreSQL (Tabela: `ObjectRegionCache`) | Zmaterializowane i przeliczone relacje przestrzenne obiektów | Odświeżane (Do przeliczenia przy zmianach) |
| Inbox Konfliktów | PostgreSQL (Tabela: `OsmSyncConflict`) | Propozycje zmian z Nocnego Stróża OSM (Różnice tagów, Duchy) | Do decyzji / akceptacji Administratora |
| Skrzynka Bliskości | PostgreSQL (Tabela: `ProximityCandidate`)| Pary znalezionych obiektów dla Radaru Klastrowania 150m | Do decyzji / zignorowania przez Administratora |
| Kolejka zadań | Redis | Payload zadań Celery, wyniki operacji asynchronicznych | Krótkoterminowa (Backend Cleanup) |

---

## Historia zmian
| Wersja | Data | Autor | Opis zmiany |
|--------|------|-------|-------------|
| 1.0 | 2026-05-28 | Dominik / AI Architect | Pierwsza wersja opisująca zasilanie OSM, Nocnego Stróża i konceptualny zarys Weryfikacji Domenowej. |
| 1.1 | 2026-05-28 | AI Architect | Dodano Przepływ 3 (Budowa Geometrii Regionów), Przepływ 4 (Radar Bliskości), gałąź Ghost Node oraz pełną tabelę Magazynów Danych. |
