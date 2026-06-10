# Changelog

> Format bazuje na [Keep a Changelog](https://keepachangelog.com/pl/1.0.0/).  
> Wersjonowanie według [Semantic Versioning](https://semver.org/lang/pl/).
>
> **Zasada:** Każda zmiana ma kontekst biznesowy — nie tylko "co", ale "po co".  
> Dotyczy to szczególnie breaking changes i refaktoryzacji.

---

## [Unreleased]

---

## [0.3.0] - 2026-06-10

### Kontekst wydania
**Faza C (Core) — Kontekst Użytkownika, Prawa Nabyte i Osobisty Kanban.** 
Zakończono budowę bezstanowego silnika Czystej Domeny oraz warstwy orkiestracji (Use Cases) dla logiki turysty, całkowicie izolując ją od frameworka webowego.

### Dodano
- **Modele B2C:** Wdrożono `TouristProfile`, `AscentLog` oraz `UserBadgeProgress` z całkowitym odseparowaniem od administracyjnej bazy PTTK.
- **Prawa Nabyte (Lazy Binding):** Wdrożono `StartBadgeProgressUseCase`, który dynamicznie zakotwicza regulamin w dacie najstarszego wejścia (US-C05).
- **Personal Kanban:** Logistyka książeczek odseparowana od Domeny Matematycznej w myśl Invariantu S-03 (`AdvanceLogisticStatusUseCase`).
- **System Freemium:** Wdrożono autoryzację limitów (Quotas) dla kont w `LogAscentUseCase`.
- **Modern UI:** Zastąpiono domyślny wygląd Django Admina biblioteką `django-unfold` (Tailwind CSS) przy zachowaniu integracji z `django-leaflet`.

### Zmieniono
- Czysta Domena została wzbogacona o wstrzykiwany `VerificationContext` (wiek, kluby, czas ewaluacji), całkowicie usuwając dług techniczny `TD-02` (zahardkodowane daty w regułach).
- Domena ocenia teraz postęp na poziomie Stopni (`BadgeTierDomain`), co zlikwidowało błąd weryfikacji odznak wielostopniowych (usunięto dług `TD-03`).
- Całkowicie wycięto `ActivityType` (Pieszo/Rower) w ramach redukcji długu UX (YAGNI).

### Naprawiono
- Ochrona Bitemporalna (Invariant T-01) oraz blokada "logowania przyszłości" (T-03) twardo egzekwowane przed zapisem logu.
- Ochrona przed duplikatami wejść (Idempotentny Upsert) w adapterze PostGIS.
- Błąd "UnboundLocalError" i 406 Not Acceptable u Nocnego Stróża OSM wyeliminowany przez wymuszenie zapytań `GET` i fałszowanie nagłówków Chrome.
## [0.2.0] - 2026-05-29

### Kontekst wydania
**Faza B — Geografia, CQRS i Zasilanie Zewnętrzne.** Stabilizacja architektury heksagonalnej i wprowadzenie zautomatyzowanego pobierania danych przestrzennych, odciążającego główne procesy.

### Dodano
- **CQRS & GIS:** Płaska tabela odczytu `ObjectRegionCache` wyliczana w tle przez Celery (PostGIS `ST_DWithin`).
- **Smart Extractor & Data Lake:** Asynchroniczne pobieranie danych z OSM. Surowe tagi archiwizowane w `JSONB`, przydatne dane (w tym lokalne nazwy graniczne, wysokość, start_date) ekstrahowane do kolumn Złotego Standardu.
- **Bitemporalność Obiektów:** Pola `existence_start` i `existence_end` chroniące historię wejść na zniszczone obiekty.
- **Radar Bliskości:** Asynchroniczny skaner wykrywający obiekty w promieniu 150m, wystawiający pary do akceptacji w Skrzynce Odbiorczej w celu budowy relacji Rodzic-Dziecko (Klastry).
- **Test Doubles (Fakes):** `FakeBadgeRepository` oraz `FakeClock` dla błyskawicznych, bezbłędnych testów jednostkowych Czystej Domeny.

### Zmieniono
- **Architektura Celery:** Skrypty przeniesione z `tasks.py` do dedykowanych `Use Cases` (`application/`) oraz `Adapters` (`infrastructure/`), by zachować czystość warstw. [TD-Spłacony]
- **Zależności HTTP:** Porzucono bibliotekę `httpx` na rzecz wbudowanego `urllib.request` w adapterze OSM, by zyskać pełną kontrolę nad nagłówkami omijającymi zapory WAF.

### Naprawiono
- Zablokowanie zapytań przez OSM API (Błąd 406 Not Acceptable i 504 Timeout) poprzez wdrożenie udawania przeglądarki Chrome, wymuszenie metody `GET` z parametrami w URL oraz system Linear Backoff Retry [EC-001].
- Pętle "Nocnego Stróża" zablokowane na martwych węzłach z OSM, rozwiązane poprzez aktualizację daty sprawdzania niezależnie od zmian w zewnętrznym tagu timestamp [EC-002].
- Błąd aplikacji `admin.E013` usunięty poprzez rezygnację z pośredniej tabeli `through` w relacji `pool_peaks`, odblokowując natywny widżet `filter_horizontal` [EC-021].
- Maskowanie błędów geometrii (Silent Fail) w GEOS poprzez usunięcie pustych bloków `except Exception: pass` [EC-011].

---

## [0.1.0] - 2026-05-20

### Kontekst wydania
**Faza A — Fundament Domenowy i Setup.** Inicjalna wersja deweloperska. Definicja Czystej Architektury i silnika reguł biznesowych dla PTTK. 

### Dodano
- Inicjalna struktura projektu (podział na `domain/`, `application/`, `infrastructure/`, `apps/`).
- Konfiguracja zabezpieczeń CI/CD (kontrakty architektoniczne, `audit_contracts.py`, `import-linter`).
- Podstawowy model danych (Badge, BadgeVersion, BadgeTier).
- **Czysta Domena:** Silnik weryfikacyjny odznak oparty na operacjach na zbiorach (Set Math) ignorujący GIS.
- **Wzorzec Strategii (Reguły JSON):** Implementacja reguł takich jak `MinAgeRule`, `TimeLimitRule`, `RequiresClubJoinDateRule`, `MandatoryObjectsRule`, `GroupedAlternativesRule` zarządzanych przez dynamiczny schemat `django-jsonform` z klauzulą `oneOf`.

### Naprawiono
- Znikające stopnie odznak w Django Adminie poprzez wyeliminowanie wartości `default` z modelu, co wymusza jawną intencję (`has_changed=True`) przy tworzeniu nowego stopnia [EC-020].

### Techniczne
- Wdrożenie pierwszych 9 dokumentów ADR definiujących kluczowe decyzje.
- `make check` zabezpieczony rygorystycznymi regułami: `ruff` (TID251) i `mypy --strict` dla domeny.