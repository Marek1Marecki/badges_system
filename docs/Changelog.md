# Changelog

> Format bazuje na [Keep a Changelog](https://keepachangelog.com/pl/1.0.0/).  
> Wersjonowanie według [Semantic Versioning](https://semver.org/lang/pl/).
>
> **Zasada:** Każda zmiana ma kontekst biznesowy — nie tylko "co", ale "po co".  
> Dotyczy to szczególnie breaking changes i refaktoryzacji.

---

## [Unreleased]

---

## [0.6.0] - 2026-07-02

### Kontekst wydania
**Faza C (Finał) — Model Rodzinny, Smart GPX i Interaktywny Atlas.** Całkowita transformacja architektury tożsamości na "Jeden Użytkownik = Wiele Profili". Wdrożenie interaktywnych widoków mapowych z dynamicznym przełączaniem warstw i inteligentnym asystentem importu tras.

### Dodano
- **Konta Rodzinne (Family Model):** Wdrożenie `TouristProfile` jako głównego nośnika tożsamości. Możliwość posiadania wielu profili pod jednym kontem Google z płynnym przełączaniem kontekstu w UI (HTMX).
- **Smart Logger GPX (US-C17):** Bezpieczny (chroniony przed XML Bomb) analizator śladów GPX. Automatycznie wyszukuje obiekty PTTK w promieniu 200m od trasy i wykonuje masowy, idempotentny zapis (Bulk Upsert).
- **UI Mapy (MapLibre):** Dodano pływające kontrolki do dynamicznej zmiany siatki (Województwa, Makro, Mezo, Auto-Zoom) oraz podkładów mapowych (Carto, OSM, Mapy.cz).
- **Zabezpieczenie Paywall:** Podkłady premium (Mapy.cz) są zablokowane dla kont FREE. Ustawienie jest zapisywane w profilu za pomocą REST API i pamiętane między urządzeniami.
- **Alert Logistyczny:** Osobisty Kanban podświetla na czerwono odznaki, których status pocztowy nie zmienił się od ponad 30 dni.

### Zmieniono
- **Wydajność GIS (Pre-kalkulacja):** Zrezygnowano z obliczania sąsiadów regionów w locie (`ST_Touches`). Wprowadzono relację M2M i skrypt `calculate_neighbors` (tolerancja `ST_DWithin` 50m) odciążający procesor na lata.
- **UX Rezygnacji:** Dodano możliwość porzucenia zdobywania odznaki, co natychmiast zwalnia slot w pakiecie Freemium, ale wiąże się z utratą Praw Nabytych.

### Naprawiono
- Błędy ładowania kafelków MVT na froncie rozwiązano wymuszając rzutowanie ID z bazy danych na typ tekstowy (`t.id::text AS db_id_str`).
- Zabezpieczono system przed IDOR w nowym modelu rodzinnym (każdy request API waliduje uprawnienia właściciela do `profile_id`).

---

## [0.5.0] - 2026-06-16

### Kontekst wydania
**Faza C (Frontend & GIS Explorer) — Interfejs Turysty.** Zbudowano w pełni funkcjonalny, serwerowo renderowany interfejs webowy (Django Templates + HTMX) połączony z interaktywnymi mapami wektorowymi (MapLibre GL JS). Przejście od surowego API do grywalizacyjnego portalu mapowego.

### Dodano
- **Silnik Nawigacji Przestrzennej:** Widoki detali dla Obiektów, Regionów, Odznak i Organizatorów połączone gęstą siecią linków krzyżowych.
- **Nawigacja Sąsiedzka:** Wykorzystanie PostGIS (`ST_Touches`) do dynamicznego znajdowania i przechodzenia między sąsiadującymi regionami geograficznymi bez sztywnych relacji w bazie.
- **Radar 2 km:** Wdrożenie mini-map wykorzystujących `ST_DWithin` do znajdowania obiektów w promieniu 2000 m od celu.
- **Wielowarstwowa Mapa Główna (MapLibre):**
  - Warstwa MVT (Tło) dla granic regionów.
  - Warstwa Heatmap (Oddalenie) bazująca na potencjale `100/n`.
  - Warstwa Symboli (Przybliżenie) dla klikalnych pinezek z popupami zasilanymi HTMX.
- **Rozbudowane Rankingi:** Wdrożenie widoków tabelarycznych dla "Rankingu Szczytów" z grupowaniem klastrów w rodziny (Rodzic-Dzieci) oraz zagregowanego "Rankingu Regionów".

### Naprawiono
- **Puste statusy Redis:** Błąd szarych pinezek na mapie spowodowany niezgodnością typów kluczy w Redis (`int` vs `str` serializacji) wyeliminowano przez *Double Lookup* w Use Case'ie [EC-035].
- **Błędy renderingu MapLibre:** Wyeliminowano awarie rysowania mapy poprzez rozbicie warstw MVT z uwagi na brak wsparcia dla dynamicznego *Data-Driven Styling* na atrybucie `line-dasharray` [EC-036].
- **Błąd 500 dla starych użytkowników:** Zabezpieczono profil turysty (OneToOneField) mechanizmem *Lazy Initialization* (`get_or_create`), co chroni logowanie kont utworzonych przed wpięciem sygnałów autoryzacji [EC-037].

## [0.4.0] - 2026-06-12

### Kontekst wydania
**Faza C (Backend API) — Kafelki, REST i Cache.** Zwieńczenie prac backendowych. Wystawiono Czystą Domenę na zewnątrz przez zwalidowane, bezpieczne endpointy API. Zaimplementowano natywny serwer kafelków i mechanizm rekomendacji celów.

### Dodano
- **REST API (Faza C):** Endpointy dla logowania wejść (`/ascents`), subskrypcji odznak (`/subscribe`) i śledzenia Osobistego Kanbanu (`/logistics`).
- **Natywny Serwer MVT:** Zbudowano dedykowany adapter wykonujący zapytania `ST_AsMVT` z w locie generowanym rzutowaniem na EPSG:3857, zasilający mapę w obrysy państw i regionów.
- **POI Scoring Engine (100/n):** Wdrożono usługę aplikacyjną wyliczającą atrakcyjność szczytów i przydzielającą kolory na bazie postępów turysty (ADR-010 i ADR-015).
- **Buforowanie w Redis:** Pełna integracja z Redisem z użyciem `gzip` dla kafelków wektorowych oraz kompresji scoringu.
- **Globalny Error Handler:** Opracowano i wdrożono `RFC7807ErrorMiddleware` wymuszający uniwersalny standard zwracania błędów przez API wraz ze śledzeniem `request_id`.

### Naprawiono
- Błąd walidacji cykli `parent_object` (C-01) zabezpieczono wymuszając model płaskiej gwiazdy w metodzie `clean()` modelu `TouristObject` (Rozwiązanie EC-022).
- Usunięto zjawisko urywania testów integracyjnych w Django poprzez przeniesienie łapania wyjątków aplikacyjnych bezpośrednio do widoków, chroniąc system przed limitami `RequestFactory` (EC-032).

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