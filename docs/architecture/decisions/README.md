# Architecture Decisions

> **Wersja:** 1.0  
> **Data:** 2026-08-25  
> **Właściciel:** Dominik / AI Architect  
> **Zasada:** Każda istotna decyzja architektoniczna pozostawia trwały, wersjonowany ślad w postaci ADR.

---

## Katalog ADR-ów

| Numer | Nazwa | Status | Data | Obszar |
|-------|-------|--------|------|--------|
| [ADR-001](adrs/ADR-001%20%E2%80%94%20Wyb%C3%B3r%20g%C5%82%C3%B3wnego%20stosu%20technologicznego%20(Django%2C%20Celery%2C%20PostGIS).md) | Wybór głównego stosu technologicznego | accepted | 2026-05-30 | Technology |
| [ADR-002](adrs/ADR-002%20%E2%80%94%20Typy%20geometryczne%20PostGIS%20jako%20transport%20infrastrukturalny%2C%20nie%20value%20objects%20domeny.md) | Typy geometryczne PostGIS jako transport infrastrukturalny | accepted | 2025-05-26 | Domain |
| [ADR-003](adrs/ADR-003%20%E2%80%94%20Silnik%20Regu%C5%82%20Biznesowych%20(Wzorzec%20Strategii%20%2B%20JSONB).md) | Silnik Reguł Biznesowych (Wzorzec Strategii + JSONB) | accepted | 2026-05-26 | Domain |
| [ADR-004](adrs/ADR-004%20%E2%80%94%20Dwuwarstwowy%20model%20zasilania%20danych%20z%20OSM%20(Curated%20Catalog%20%26%20Data%20Lake).md) | Dwuwarstwowy model zasilania danych z OSM | accepted | 2026-05-30 | Data |
| [ADR-005](adrs/ADR-005%20%E2%80%94%20P%C5%82aski%20Model%20Odczytu%20CQRS%20dla%20Relacji%20Geograficznych.md) | Płaski Model Odczytu CQRS dla Relacji Geograficznych | accepted | 2026-05-30 | Performance |
| [ADR-006](adrs/ADR-006%20%E2%80%94%20Klastrowanie%20blisko%C5%9Bci%20i%20poj%C4%99cie%20Rodzica%20(Radar%20150m%20i%20Skrzynka%20Odbiorcza).md) | Klastrowanie bliskości i pojęcie Rodzica | accepted | 2026-05-30 | Algorithm |
| [ADR-007](adrs/ADR-007%20%E2%80%94%20Hierarchia%20i%20Wersjonowanie%20Odznak%20(Temporal%20Modeling%20i%20Prawa%20Nabyte).md) | Hierarchia i Wersjonowanie Odznak | accepted | 2026-05-26 | Domain |
| [ADR-008](adrs/ADR-008%20%E2%80%94%20Bitemporalno%C5%9B%C4%87%20Obiekt%C3%B3w%20Turystycznych%20(Cykl%20%C5%BCycia%20i%20Soft%20Delete).md) | Bitemporalność Obiektów Turystycznych | accepted | 2026-05-26 | Data |
| [ADR-009](adrs/ADR-009%20%E2%80%94%20Weryfikacja%20wej%C5%9B%C4%87%20jako%20operacje%20na%20zbiorach%20(Pool-based%20Set%20Verification).md) | Weryfikacja wejść jako operacje na zbiorach | accepted | 2026-05-26 | Algorithm |
| [ADR-010](adrs/ADR-010%20%E2%80%94%20Dynamiczne%20kolorowanie%20mapy%20i%20priorytetyzacja%20stan%C3%B3w%20odznak.md) | Dynamiczne kolorowanie mapy i priorytetyzacja stanów odznak | accepted | 2026-05-30 | UX |
| [ADR-011](adrs/ADR-011%20%E2%80%94%20Filtrowanie%20przestrzenne%20na%20%C5%BC%C4%85danie%20(BBox%20%26%20Hybrydowe%20Leniwe%20Wartostowanie).md) | Filtrowanie przestrzenne na żądanie | accepted | 2026-05-30 | Performance |
| [ADR-012](adrs/ADR-012%20%E2%80%94%20Weryfikacja%20cel%C3%B3w%20otwartych%20geograficznie%20(Wildcard%20JSON%20Rules).md) | Weryfikacja celów otwartych geograficznie | accepted | 2026-05-30 | Algorithm |
| [ADR-013](adrs/ADR-013%20%E2%80%94%20Architektura%20Renderowania%20Map%20(Vector%20Tiles%20%26%20Client-Side%20Styling)%20.md) | Architektura Renderowania Map | accepted | 2026-05-30 | Frontend |
| [ADR-014](adrs/ADR-014%20%E2%80%94%20Separacja%20matematycznego%20post%C4%99pu%20od%20weryfikacji%20logistycznej%20(Kanban).md) | Separacja matematycznego postępu od weryfikacji logistycznej | accepted | 2026-06-01 | UX |
| [ADR-015](adrs/ADR-015%20%E2%80%94%20Algorytm%20i%20buforowanie%20Rankingu%20Potencja%C5%82u%20Obiekt%C3%B3w%20(POI%20Scoring).md) | Algorytm i buforowanie Rankingu Potencjału Obiektów | accepted | 2026-06-01 | Algorithm |
| [ADR-016](adrs/ADR-016%20%E2%80%94%20Rozdzielenie%20to%C5%BCsamo%C5%9Bci%20od%20autoryzacji%20(Model%20Rodzinny).md) | Rozdzielenie tożsamości od autoryzacji | accepted | 2026-06-16 | Security |
| [ADR-020](adrs/ADR-020%20%E2%80%94%20Architektura%20Wdro%C5%BCe%C5%84%20(Deployment%20%26%20SRE).md) | Architektura Wdrożeń (Deployment & SRE) | accepted | 2026-07-09 | Operations |
| [ADR-021](adrs/ADR-021%20%E2%80%94%20Strategia%20Backupow%20i%20Disaster%20Recovery.md) | Strategia Backupów i Disaster Recovery | accepted | 2026-07-09 | Operations |
| [ADR-022](adrs/ADR-022%20%E2%80%94%20Rejestr%20Wdro%C5%BCen%20(Release%20Registry).md) | Rejestr Wdrożeń (Release Registry) | accepted | 2026-07-09 | Operations |
| [ADR-023](adrs/ADR-023%20%E2%80%94%20Cykl%20Zycia%20Danych%20Referencyjnych.md) | Cykl Życia Danych Referencyjnych | accepted | 2026-07-22 | Data |
| [ADR-024](adrs/ADR-024%20%E2%80%94%20Strategia%20Migracji%20(Expand%20and%20Contract).md) | Strategia Migracji (Expand and Contract) | accepted | 2026-07-23 | Database |
| [ADR-025](adrs/ADR-025%20-%20%C5%9Arodowisko%20TEST%20aplikacji%20Badges%20System.md) | Środowisko TEST aplikacji Badges System | accepted | 2026-07-19 | Operations |
| [ADR-026](adrs/ADR-026%20-%20PostgreSQL%20Volume%20Layout%20(PostgreSQL%2018%2B).md) | PostgreSQL Volume Layout | accepted | 2026-08-25 | Infrastructure |

---

## Obszary decyzyjne

| Obszar | Liczba ADR-ów | ADR-y |
|--------|---------------|-------|
| Domain | 5 | ADR-002, ADR-003, ADR-007, ADR-008, ADR-009 |
| Algorithm | 4 | ADR-006, ADR-009, ADR-012, ADR-015 |
| Data | 4 | ADR-004, ADR-008, ADR-011, ADR-023 |
| Technology | 1 | ADR-001 |
| Performance | 2 | ADR-005, ADR-011 |
| UX | 2 | ADR-010, ADR-014 |
| Frontend | 1 | ADR-013 |
| Security | 1 | ADR-016 |
| Operations | 5 | ADR-020, ADR-021, ADR-022, ADR-025, ADR-026 |
| Database | 1 | ADR-024 |

---

## Statusy ADR-ów

| Status | Znaczenie |
|--------|-----------|
| `accepted` | Decyzja została podjęta i wdrożona |
| `proposed` | Decyzja jest w trakcie rozważania |
| `superseded` | Decyzja została zastąpiona przez nowszą |
| `deprecated` | Decyzja nie jest już stosowana |

---

## Środowisko pracy z ADR-ami

### Tworzenie nowego ADR

1. Skopiuj szablon: `docs/adrs/ADR-TEMPLATE.md`
2. Uzupełnij wszystkie sekcje: Kontekst, Opcje rozważane, Decyzja, Konsekwencje, Warunek rewizji, Relacje
3. Numeruj sekwencyjnie: ADR-027, ADR-028, ...
4. Umieść w `docs/adrs/`
5. Zaktualizuj indeks w tym pliku

### Aktualizacja ADR

- Zmiana statusu: `accepted` → `superseded` + wypełnij pole `Zastąpiony przez`
- Dodaj wpis w `## Historia zmian` na dole dokumentu
- Zaktualizuj sekcję `## Relacje` jeśli powiązania się zmieniły

### Relacje

- **Import Linter** — weryfikuje reguły wynikające z ADR-ów (np. ADR-001 → `domain-purity`)
- **C4 Diagrams** — wizualizują architekturę wynikającą z ADR-ów (np. ADR-001 → `docs/architecture/`)
- **Architecture Debt Register** — rejestruje świadome odstępstwa od decyzji (np. ADR-016 → `DŁUG-001`)

---

## Historia zmian

| Wersja | Data | Autor | Opis zmiany |
|--------|------|-------|-------------|
| 1.0 | 2026-08-25 | Dominik / AI Architect | Utworzenie indeksu ADR-ów |
