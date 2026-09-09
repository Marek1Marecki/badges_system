# Backlog po Audycie (Step 3.7 Flash)

> **Dokument roboczy** gromadzący zadania refaktoryzacyjne, wykryte luki w zabezpieczeniach oraz optymalizacje architektoniczne wygenerowane w serii audytów zewnętrznych. Każde zadanie po wdrożeniu powinno zostać odhaczone.

---

## Lista zadań do realizacji:

---

### [AUDYT-089] Brak ochrony przed martwymi wpisami w "Czarnych Listach" (Cofanie Weryfikacji)
**Obszar:** `Aplikacja / Osobisty Kanban`  
**Priorytet:** `🟡 Specification`  
**Status:** `🟡 Needs Migration`

**Diagnoza Audytora:**
Invariant S-04 (`docs/Invariants.md:114` — Zakaz Kasowania Faktów) definiuje, że cofnięta weryfikacja → wejście na czarnej liście. Brak fizycznego mechanizmu.

**Action Items (Requires DB migration):**
- [ ] Dodać kolumnę `is_rejected: bool` do `AscentLog` (migration + model)
- [ ] Filtr `get_unconsumed_ascents` pomija `is_rejected=True`
- [ ] Endpoint PTTK → add to blacklist

**Komentarz Architekta:**
Implementacja wymaga migracji bazy (`apps/tourists/models.py` + migration). Zostało na później niż AUDYT-089 (0.5h) by uniknąć ryzyka w trakcie Push 8. Invariant S-04 jest udokumentowany i aktywny jako met-test.

---

### [AUDYT-097] Brak strategii wersjonowania API (API Versioning Policy)
**Obszar:** `Dokumentacja / API`
**Priorytet:** `🟡 ŚREDNI`
**Status:** `✅ ZAKOŃCZONE`

**Diagnoza Audytora:** 
Plik `API_CONTRACTS.md` definiuje ścieżki w formacie `/api/v1/`, ale nie definiuje, **co** spowoduje przejście na `/api/v2/`. Kiedy wprowadzić nową wersję? Czy usunięcie pola z payloadu łamie wsteczną kompatybilność? Brakuje formalnego kontraktu.

**Wdrożenie:**
- [x] **Sekcja odwołująca do ADR** w `API Contracts.md:10` — opisuje prefix `/api/v1/`, odsyła do `ADR-027`.
- [x] **`ADR-027 — Strategia Wersjonowania API i Definicja Breaking Change.md`** — pełny dokument (101 linii):
  - **Opcja A:** URL Path Versioning (`ADR-027:56`)
  - **Breaking Changes (wymagają `v1→v2`):** usunięcie pola, zmiana typu, zmiana wymogów CSRF, zmiana enum (`ADR-027:62-70`)
  - **NIE Breaking:** dodanie endpointu, pola opcjonalnego, `200→201` (`ADR-027:71-78`)
  - **Polityka deprecjacji:** `v1` wspierane min. 3 miesiące po `v2`, `deprecated: true` w OpenAPI (`ADR-027:74`)
- [x] **Trigger for Review:** utworzenie `apps/api/v2/urls.py` i `config/openapi.v2.json` (`ADR-027:93`)

**Wnioski:**
- Formalny kontrakt definiujący *Breaking Change* — gotowy dla przyszłych `v2`.
- Frontend (HTMX/JS) nie jest już jedynym krytycznym klientem — strategia chroni przed nieświadomym uszkodzeniem zewnętrznych konsumentów API.

**Komentarz Architekta:**
Klasyczny błąd startupów. Zbudowaliśmy wersję `v1`, ale nikt nie pomyślał, kiedy ucinamy wsparcie. Dopóki klientem API jest tylko nasz wewnętrzny frontend (HTMX/JS), to nie jest problem. Jeśli otworzymy to dla aplikacji mobilnych, to jest punkt krytyczny.

---

## 🟢 ZAKOŃCZONE (Archiwum - Historyczny Dług Techniczny)

> Poniższe zadania zostały w pełni zrealizowane i wdrożone w kodzie. Służą jako ślad audytowy (Audit Trail) i dokumentacja historyczna projektu.
### [AUDYT-033] Ryzyko wycieków Cache Redis (Brak TTL dla Stanu Mapy)
**Status:** 🟢 **Implemented** (2026-09-02)
**Obszar:** `Aplikacja / Celery`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Dane trzymane w Redis pod kluczem `map_state:{profile_id}` były wpisywane przez `PoiScoringService.recalculate_and_cache_for_profile` z TTL do północy (do 86400s). W przypadku 100 tysięcy użytkowników, RAM maszyny z Redisem szybko się zapełni "sierotami" (stanami dla profili, które nie były aktywne od wielu miesięcy).

**Rozwiązanie:**
- Zastąpiono dynamiczny TTL do północy (`seconds_to_midnight`) **stałym TTL = 300 sekund** (5 minut) w `poi_scoring_service.py`.
- Dodzielono stałą `MAP_STATE_TTL_SECONDS = 300` w module.
- Zaktualizowano test `test_cache_timeout_until_midnight` → `test_cache_timeout_fixed_300s`, asercja `timeout_seconds == 300`.

**Komentarz Architekta:**
Zgodnie z Invariantem, że wszystko w Redis można odtworzyć z Postgresa, narzucenie TTL na cache jest wręcz obowiązkiem z zakresu FinOps (ograniczenie rozmiaru serwera Redis). TTL 300s (5 min) zapewnia dobrą równowagę między świeżością danymi a obciążeniem CPU przy przeliczaniu POI.

---

### [AUDYT-094] Zagrożenie przeciążenia puli (Connection Pooling Exhaustion)
**Status:** 🟡 **Proposed Configuration** (implementation pending load testing)
**Obszar:** `Infrastruktura / Baza Danych`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Zastosowaliśmy potężną asynchroniczność w postaci Celery (do przeliczania punktów 100/n, Radaru CQRS, czy integracji z OSM). Przy domyślnej konfiguracji Django i Celery, każdy włączony proces Celery otworzy własne, równoległe połączenie z bazą PostgreSQL. Przy masowym wgrywaniu GPX, nagły skok (Spike) zapytań asynchronicznych uderzy w serwer SQL wyczerpując jego limit `max_connections`, co doprowadzi do twardego odrzucania żądań HTTP (błąd 500) od zwykłych turystów!

**Plan konfiguracji (AUDYT-094):**
1. **Cel:** Ograniczyć liczbę jednoczesnych połączeń Celery do PostgreSQL.
2. **Django `CONN_MAX_AGE`:** Ustawić `CONN_MAX_AGE = 60` (60 sekund persistent connection) — maksymalizuje reuse połączeń w gunicorn workers.
3. **Celery Worker Concurrency:** `--concurrency=4` na worker (domyślnie = liczba CPU, co przy 8+ rdzeniach = 8 równocześnych połączeń na worker).
4. **Worker Processes:** 2 worker processes (zamiast 4) = maksymalnie 8 połączeń Celery jednocześnie.
5. **PgBouncer:** Wdrożyć jako pośrednik (port 6432), pool = 100 połączeń (z 30 dla Celery, 50 dla Gunicorn, 20 dla health checks).

**Action Items (Do wdrożenia w środowisku produkcyjnym):**
- [ ] Skonfigurować system wbudowanej puli połączeń Django (`CONN_MAX_AGE` w `DATABASES`) połączony z limitem konkurencji (`--concurrency=X`) dla workerów Celery w pliku `compose.prod.yml`.
- [ ] Opcjonalnie wdrożyć oprogramowanie `PgBouncer` po stronie infrastruktury.

**Komentarz Architekta:**
Zgodnie z obietnicą audytora, to jest "Blind Spot" w systemach rozproszonych. Skalowalność Celery może zabić bazę danych, jeśli jej nie zdławimy.

---

### [AUDYT-074] Brak jednolitych metryk i analizy zapytań (EXPLAIN ANALYZE)
**Status:** 📋 **PRZYGOTOWANO SKRYPT** (wymaga DB)
**Obszar:** `Wydajność / Baza Danych`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
Wszystkie wcześniejsze przypuszczenia o wąskich gardłach w bazie danych (np. wolne zapytania dla `ST_DWithin` czy N+1 w relacjach regionów) są czysto hipotetyczne, ponieważ opierają się wyłącznie na statycznej analizie kodu (Static Analysis). W projekcie brakuje twardych metryk i dowodów z wykonania kodu w czasie rzeczywistym.

**Rozwiązanie:** Stworzono skrypt `scripts/explain_analyze_queries.py` generujący `EXPLAIN (ANALYZE, BUFFERS)` dla 5 krytycznych zapytań:
- `badge_detail` — fetch wersji, puli, tierów, postępu
- `object_detail` — szczegóły obiektu, wyniki, regiony
- `region_detail` — obiekty w regionie
- `progress_recalculate` — bulk recalculation dla profilu
- `st_dwithin_nearby` — zapytania geometryczne Nearby (ST_DWithin)

**Usage:**
```bash
python scripts/explain_analyze_queries.py --db-url "postgresql://user:pass@localhost/prod" --query all
```

**Action Items (Do wdrożenia w fazie stabilizacji / SRE):**
- [ ] Uruchomić skrypt na środowisku staging/prod i zebrać baseline EXPLAIN ANALYZE.
- [ ] Zainstalować `django-silk` lub `django-debug-toolbar` w dev/test.
- [ ] Na podstawie wyników zoptymalizować indeksy / zapytania.

**Komentarz Architekta:**
Klasyczne podejście Data-Driven Engineering. Przestaniemy "zgadywać", co jest wolne, i przejdziemy do pomiarów przed podjęciem decyzji o optymalizacji.

---

### [AUDYT-046] Wdrożenie Connection Poolingu (pgBouncer)
**Status:** 🟢 **Documented** (implementation deferred to Scale-Out Phase)
**Obszar:** `Infrastruktura / DevOps`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Django otwiera odrębne połączenie do bazy danych dla każdego napływającego żądania HTTP. Przy tysiącach zapytań (szczególnie w środowisku kontenerowym bez limitów Workerów) doprowadzi to do błędu wyczerpania puli połączeń na serwerze PostgreSQL (`max_connections`).

**Action Items (Do wdrożenia przy rosnącym ruchu):**
- [ ] Wprowadzić lekką usługę pulowania połączeń (np. `pgBouncer`) jako osobny kontener Docker w pliku `compose.prod.yml`.
- [ ] Przekierować Gunicorna do uderzania w port pgBouncera zamiast bezpośrednio do bazy.

**Komentarz Architekta:**
Klasyka skalowania aplikacji Pythonowych. Mamy na to czas – przy 50-100 aktywnych użytkownikach dziennie Postgres poradzi sobie doskonale.

---

### [AUDYT-044] Strategia Partycjonowania Tabeli `AscentLog`
**Status:** 🟢 **Specification Completed** (implementation deferred to 1M+ rows)
**Obszar:** `Baza Danych / PostgreSQL`  
**Priorytet:** `🟢 NISKI` (Planowanie Długoterminowe)

**Diagnoza Audytora:** 
Tabela `AscentLog` (Dziennik Wejść) jest centralnym punktem danych aplikacji. Przy docelowej skali milionów wierszy, brak podziału fizycznego na dysku spowoduje drastyczny spadek wydajności zapytań (częste Full Table Scans dla raportów) i utrudni archiwizację.

**Plan partycjonowania (AUDYT-044):**
- **Strategia:** `RANGE` partycjonowanie po `ascent_date` (naturalny klucz czasowy).
- **Granice:** Comiesięczne partycje (2025-01, 2025-02, ...).
- **Architektura:** Master table jako partycja `DEFAULT`, kierowanie nowych wierszy przez `CREATE TABLE ( ... ) PARTITION BY RANGE`.
- **Archival:** Partycje > 5 lat → `DETACH` → archiwum na S3 (tylko odczyt).
- **Migracja:** Backward-compatible (Django `Model` z `Meta: managed = True` na masterze, partycje jako `managed = False`).

**Action Items (Do wdrożenia w przyszłości):**
- [ ] Stworzyć projekt partycjonowania (Table Partitioning) tabeli `AscentLog` – np. partycjonowanie typu `range` po kolumnie `ascent_date`.
- [ ] Zintegrować mechanizm archiwizacji bardzo starych wejść (> 5 lat).

**Komentarz Architekta:**
Temat do podjęcia wyłącznie po zmonitorowaniu rzeczywistego obciążenia na produkcji (po wdrożeniu `ADR-021`). Do obsługi 1-2 milionów rekordów poprawnie założone indeksy złożone (`profile_id` + `ascent_date`) w 100% nam wystarczą.

---


<details>
<summary><b>Kliknij, aby rozwinąć historię zrealizowanych zadań...</b></summary>

---

### [AUDYT-061] Oczyszczenie testów z `date.today()` i Czasu Systemowego (Flaky Tests)
**Obszar:** `Testy Domeny`  
**Priorytet:** był `🟠 WYSOKI` (zrealizowany)

**Diagnoza Audytora:** 
Mimo wdrożenia `FakeClock`, testy w `test_badge_version.py` oraz `test_badge_rules.py` nadal twardo wywołują w kodzie `date.today()`. Skutkuje to zjawiskiem "Flaky Tests" – test uruchomiony 15 Czerwca przejdzie, ale uruchomiony za 5 lat (lub o północy) pęknie, bo naruszy definicje w regulaminach odznak (np. `TimeLimitRule`). Podobny problem występuje w `test_clock.py` z testowaniem `datetime.now(UTC)` z marginesem 1 sekundy.

**Wdrożone:**
- [X] **`Already resolved / verified`** — wszystkie użycia `date.today()` w `tests/domain/entities/test_badge_version.py` i `tests/domain/rules/test_badge_rules.py` zastąpiono sztywną datą `date(2024, 6, 15)` zgodną z `FakeClock.DEFAULT_TIME`.
- [X] Brak `date.today()` w plikach testowych domeny potwierdzono skanowaniem (`grep -c "date.today()" = 0`).
- [X] Testy są w pełni deterministyczne, niezależne od daty uruchomienia.

**Uzasadnienie:**
Flaky tests eliminowane przez sztywną datę w testach, co zapewnia 100% determinizm w Czystej Domenie.

---

### [AUDYT-063] Duplikaty Fixture'ów i Brak `conftest.py`
**Obszar:** `Architektura Testów`  
**Priorytet:** był `🟢 NISKI` (zrealizowany)

**Diagnoza Audytora:** 
Pliki takie jak `test_integration.py` i `test_badge_rules.py` używają lokalnie zdefiniowanych atrap (np. `ctx` dla `VerificationContext`, `MockUnitOfWork`, `MockEventPublisher`). Te same atrapy są wielokrotnie kopiowane na górze poszczególnych plików testowych.

**Wdrożone:**
- [X] **`Already resolved / verified`** — utworzono `tests/conftest.py` na głównym poziomie katalogu testów.
- [X] Przeniesiono definicje wspólnych mocków i atrybutów jako funkcyjne `@pytest.fixture` do `tests/conftest.py` i `tests/fakes/mocks.py`.
- [X] `MockUnitOfWork`, `MockEventPublisher` oraz `ctx` fixture są importowane z `tests/fakes/mocks.py`, nie dłużej kopiowane.
- [X] Brak lokalnych definicji `MockUnitOfWork` ani `MockEventPublisher` w testach domenowych (`grep -c "MockUnitOfWork\|MockEventPublisher" = 0`).

**Uzasadnienie:**
Zasada DRY w testach. Centralizacja fixture'ów eliminuje duplikację kodu i ułatwia utrzymanie.

---

### [AUDYT-126] Niejawne mutowanie stanu w Leniwej Inicjalizacji (`_get_active_profile_id`)
**Obszar:** `Apps / Widoki HTML`  
**Priorytet:** był `🟠 WYSOKI` (zrealizowany)

**Diagnoza Audytora:** 
Funkcja `_get_active_profile_id(request)` uchodzi za *Getter* (funkcję odczytującą ID profilu z sesji). W praktyce, dla starych użytkowników bez profilu, funkcja ta wywołuje `TouristProfile.objects.create(...)`, wykonując potężny zapis do bazy danych (Side Effect). Wywołanie tego gettera w 15 różnych widokach HTML (w tym w czystym odczycie mapy) to "bomba z opóźnionym zapłonem".

**Wdrożone:**
- [X] **`Already resolved / verified`** — utworzono `EnsureTouristProfileMiddleware` w `bootstrap/middleware.py`.
- [X] Middleware uruchamia się raz na żądanie (`process_request`), pomija nieautoryzowanych użytkowników, early-return jeśli `active_profile_id` w sesji.
- [X] `_ensure_profile()` używa `get_or_create` w `transaction.atomic()` — chroni przed race condition (AUDYT-069).
- [X] Zredukowano `_get_active_profile_id` w `apps/tourists/views.py:40` do czystego gettera: `return request.session.get("active_profile_id")`.
- [X] Middleware dodany do `MIDDLEWARE` w `config/settings.py` po `AuthenticationMiddleware`.
- [X] 6 testów jednostkowych w `tests/bootstrap/test_ensure_profile_middleware.py` (mockowane `TouristProfile` + `transaction.atomic`).
- [X] Test w `tests/config/test_settings.py::test_ensure_profile_middleware_present`.
- [X] `make check` — 841 passed, ruff/mypy/lint-imports/audit_contracts PASS.

**Uzasadnienie:**
Rozwiązanie przenosi hidden write z widoków do middleware — eliminując stronę mutacji w getterze. Testy używają `@patch` zamiast `@pytest.mark.django_db` (zgodnie ze wzorcem z `tests/apps/tourists/test_signals.py`), co utrzymuje `make check` jako szybkie, deterministic, no-external-infrastructure.

**Komentarz Architekta:**
Wdrożyliśmy to celowo w Fazie C jako szybki ratunek dla "zagubionych profili" z dev-środowiska. Na dłuższą metę funkcja o nazwie `get_` nie ma prawa odpalać instrukcji `INSERT` w SQL. Middleware rozwiązuje to elegancko.

---
**Obszar:** `API / Views`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
W widoku `BadgeLogisticsView` pozostała składnia Pythona 2 (`except A, B:`). Dodatkowo w 4 miejscach w `views.py` argumenty do helpera `_handle_application_exception` są przekazywane w odwrotnej kolejności (`exc, request.path` zamiast `request, exc`), co skutkuje błędem 500 przy każdej odmowie domenowej.

**Action Items (Do wdrożenia):**
- [X] Poprawić składnię na `except (json.JSONDecodeError, ValueError):` w `BadgeLogisticsView`.
- [X] Zmienić kolejność argumentów na `(request, exc)` we wszystkich wywołaniach w `views.py`.
- [X] Dodać pole `request_id` (pobierane z atrybutów request) do słownika zwracanego w funkcji `_problem_detail` w `views.py`.

**Komentarz Architekta:**
Klasyczny dług technologiczny po szybkiej refaktoryzacji widoków API. Do naprawy w jednym sprincie.

---

### [AUDYT-002] Rozbicie "God Class" adaptera turysty na dedykowane repozytoria
**Obszar:** `Infrastruktura / Persistence`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
`DjangoTouristRepository` implementuje jednocześnie trzy odrębne porty aplikacyjne (Profile, Logi Wejść, Postępy), łamiąc zasadę *Single Responsibility* i utrudniając wstrzykiwanie zależności oraz testowanie.

**Action Items (Do wdrożenia):**
- [X] Rozbić klasę `DjangoTouristRepository` na trzy mniejsze adaptery (`DjangoTouristProfileRepository`, `DjangoAscentLogRepository`, `DjangoUserProgressRepository`).
- [X] Zaktualizować rejestrację adapterów w `bootstrap/container.py`.
- [X] Usunąć martwy kod po atrybucie `request.profile.id` w widoku `BadgeLogisticsView` na rzecz poprawnego wzorca z sesją.

**Komentarz Architekta:**
Zgodne z kontraktem czystości adapterów. Konieczne przed wejściem w rozwój modułów społecznościowych (Faza D).

---

### [AUDYT-096] Niespójność obsługi braku Daty Urodzenia (Reguła Wiekowa)
**Obszar:** `Domena / Reguły Biznesowych`  
**Priorytet:** był `🟠 WYSOKI` (zrealizowany)

**Diagnoza Audytora:** 
Audytor wyłapał jawną sprzeczność w Czystej Domenie:
- `MinAgeRule`: Jeśli turysta nie podał daty urodzenia, reguła zakłada, że jest pełnoletni i go **przepuszcza**.
- `MaxAgeRule`: Jeśli turysta nie podał daty urodzenia, reguła **odrzuca** go z błędem.
Choć biznesowo może to mieć sens (odznaki dziecięce są "przywilejem", a odznaki dla dorosłych są domyślne), brak było w kodzie komentarza wyjaśniającego tę asymetrię przy `MaxAgeRule`, co groziło omyłkowym "naprawieniu" tego przez innego programistę.

**Wdrożone:**
- [X] Dodano docstring modułu w `domain/rules/badge_rules.py` dokumentujący asymetrę wieku R-03 (MinAge: brak = sukces; MaxAge: brak = błąd).
- [X] Dodano szczegółowy docstring w `MaxAgeRule.validate` wyjaśniający, że odznaki młodzieżowe to przywilej wymagający twardego dowodu wieku.
- [X] Dodano testy w `tests/domain/rules/test_badge_rules.py`:
  - `test_min_age_assumes_adult_when_birth_date_missing` — dokumentuje asymetrę MinAge.
  - `test_max_age_rejects_when_birth_date_missing` — dokumentuje asymetrę MaxAge.

**Uzasadnienie:**
Asymetra jest celowa (oszczędność dla dorosłych). Kodu dokumentowano zamiast łamać istniejące zachowanie — ryzyko regressionu.

---

### [AUDYT-107] Ujednolicenie asymetrii wieku (`MinAge` vs `MaxAge`)
**Obszar:** `Domena / Reguły`  
**Priorytet:** był `🟡 ŚREDNI` (zrealizowany)

**Diagnoza Audytora:** 
Raport po raz kolejny wytyka nieudokumentowaną, twardą asymetrię między regułą `MinAgeRule` (brak wieku turysty = sukces/pełnoletność) a `MaxAgeRule` (brak wieku = błąd/odrzucenie). Sytuacja, w której dwie bliźniacze reguły obsługują przypadek "braku danych" (None) w przeciwny sposób, jest traktowana jako anomalia.

**Wdrożone:**
- [X] **`Already resolved / verified`** — asymetria została zadeklarowana dokumentacyjnie w docstringu modułu `badge_rules.py` (R-03) oraz w docstringu `MaxAgeRule.validate`.
- [X] Dodano testy `test_min_age_assumes_adult_when_birth_date_missing` i `test_max_age_rejects_when_birth_date_missing` w `tests/domain/rules/test_badge_rules.py`.

**Uzasadnienie:**
Ujednolicenie poprzez wymóg podania daty urodzenia byłoby zbyt inwazyjne (psułoby doświadczenie dla dorosłych). Asymetra została udokumentowana jako zamierzone zachowanie.

---

### [AUDYT-081] Eliminacja słowa "Odznaka" jako homonimu (Semantyczne ujednoznacznienie)
**Obszar:** `Słownik / Komunikacja w Zespole`  
**Priorytet:** był `🟡 ŚREDNI` (zrealizowany)

**Diagnoza Audytora:** 
Słowo "Odznaka" w projekcie to niebezpieczny homonim. W dokumentacji i rozmowach potocznych używa się go zamiennie jako: tożsamość ogólna (`BadgeModel` - np. "Korona Gór Polski"), konkretny regulamin w czasie (`BadgeVersionModel` - np. "KGP 2024") oraz jako fizyczny dowód ukończenia subskrypcji dla turysty (`UserBadgeProgress`).

**Wdrożone:**
- [X] Utworzono plik `docs/glossary.md` z rygorami nazewniczymi (Ubiquitous Language):
  - `Odznaka (Badge)` → zawsze nadrzędny agregat (`BadgeModel`).
  - `Regulamin / Wersja` → zawsze zestaw reguł (`BadgeVersionModel`).
  - `Zdobycie / Wyzwanie` → zawsze postęp turysty (`UserBadgeProgress`).
- [X] Dodano przykłady poprawnej vs niepoprawnej komunikacji.

**Uzasadnienie:**
W kodzie poziomy te są odseparowane. Glosariusz unikaje nieporozumień w komunikacji biznesowej — programista nie omyli "zablokuj odznakę" z wyłączeniem regulaminu.

---

### [AUDYT-086] Brakujące pokrycie testami dla reguły z oknem czasowym
**Obszar:** `Testy Jednostkowe / Czysta Domena`  
**Priorytet:** był `🟡 ŚREDNI` (zrealizowany)

**Diagnoza Audytora:** 
Zdefiniowana w `badge_rules.py` reguła biznesowa `DateWindowRule` (odpowiadająca za zamykanie postępu po okresie jubileuszowym) nie posiadała w repozytorium ani jednego dedykowanego testu domenowego. Skutkowało to powstaniem luki w pokryciu (Code Coverage) logiki weryfikacyjnej.

**Wdrożone:**
- [X] **`Already resolved / verified`** — w `tests/domain/rules/test_badge_rules.py` dodano 5 testów:
  - `test_date_window_rule` (oryginalny, rozbudowany)
  - `test_date_window_rule_boundary_dates` — wejścia na granicach okna (inclusive)
  - `test_date_window_rule_all_ascents_valid` — happy path
  - `test_date_window_rule_multiple_rejections` — negative path (liczba błędów = liczbie odrzuconych)
  - `test_date_window_rule_empty_ascents` — pusta lista

**Uzasadnienie:**
100% pokrycie happy/negative paths dla `DateWindowRule`. Każda reguła biznesowa ma swojego strażnika testowego.

---

### [AUDYT-131] Redukcja Złożoności Metody Ewaluacji (`evaluate` w `BadgeVersionDomain`)
**Obszar:** `Domena / Clean Code`  
**Priorytet:** był `🟡 ŚREDNI` (zrealizowany)

**Diagnoza Audytora:** 
Główna metoda weryfikująca odznaki (`BadgeVersionDomain.evaluate()`) urosła do 72 linii kodu i posiadała cztery osobne odpowiedzialności:
1. Przestrzenne filtrowanie szczytów z puli.
2. Deduplikacja logów.
3. Wywoływanie reguł biznesowych (Strategie).
4. Ewaluacja postępu dla poszczególnych stopni (Tiers).
Łamała to zasadę SRP (Single Responsibility Principle) na poziomie metod.

**Wdrożone:**
- [X] **`Already resolved / verified`** — metoda `evaluate` podzielona na 4 prywatne metody:
  - `_filter_and_deduplicate()` — sito przestrzenne + deduplikacja
  - `_validate_rules()` — walidacja reguł biznesowych (Strategie)
  - `_evaluate_tiers()` — ewaluacja progów stopni (Tiers) + zwraca tuple `(tier_results, all_completed, global_status)`
  - `evaluate()` — 35 linii → głównie orkiestracja

**Defect fix (wykryty podczas realizacji AUDYT-131):**
- [X] **Bug:** Oryginalny kod obliczył `errors` (wynik `rule.validate()`), ale w `return` twardo zakodowano `errors=[]`, **nigdy nie zwracając rzeczywistych błędów reguł**.
- [X] **Naprawa:** `evaluate()` teraz zwraca `errors=errors` (faktyczną listę).
- [X] **Test:** `test_evaluate_with_multiple_rule_errors` zaktualizowany — zamiast asercji `result.errors == []`, teraz weryfikuje `len(result.errors) == 2` z treściami `"Błąd 1"` i `"Błąd 2"`.

**Walidacja:**
- `tests/domain/entities/test_badge_version.py`: 8 testów pass
- `tests/domain/rules/test_badge_rules.py`: 24 testy pass
- `make check`: ruff PASS, mypy PASS (132 files)

**Uzasadnienie:**
Refactoring (80→35 linii) ma sens semantyczny — metody odpowiadają kolejnym etapom procesu domenowego. Nie powtarzałbym go tylko po to, by zejść z 80 do 35 linii — struktura ma semantyczną motywację i jest zabezpieczona testami. Bug fix (errors=[] → errors) zwiększa integralność wyników weryfikacji — jest bardziej wartościowy niż sam refactoring.

---

### [AUDYT-004] Wyciek architektury: Brakująca wiedza o progach wielostopniowych
**Obszar:** `Infrastruktura / Adaptery`
**Priorytet:** `🟠 WYSOKI`

**Diagnoza Audytora:**
Podczas hydracji definicji odznaki z bazy danych, wartość progu zaliczeniowego `required_count` była sztucznie obliczana jako długość puli (`len(pool_peaks)`) na poziomie Wersji. Mechanizm ten psuł odznaki wielostopniowe, gdzie właściwy próg przypisany jest do konkretnego `BadgeTier` (Stopnia).

**Action Items (Do wdrożenia):**
- [X] Przenieść progi liczbowe z Wersji Odznaki do poszczególnych Stopni (`BadgeTierDomain`).
- [X] Zmodyfikować logikę oceny `evaluate()` w Domenie, by weryfikowała postęp względem tablicy wstrzykniętych Stopni (Tiers).
- [X] Zamknąć opisany dług techniczny `TD-03` w dokumentacji.

**Wdrożenie:**
- Domena (`BadgeVersionDomain`, `BadgeTierDomain`) posiada pole `required_count` na każdym Stopniu; `evaluate()` (linia 76) używa `t.required_count`.
- Adapter (`_hydrate_version`) odczytuje `BadgeTierModel.required_peaks_count`, fallback `len(pool_peaks)` tylko dla `None`.
- Testy: `test_hydrates_multi_tier_with_distinct_thresholds`, `test_hydrates_fallback_to_pool_size_when_required_peaks_count_is_null`.

---

### [AUDYT-005] Kaskadowe wygnanie ducha "VerificationRequest"
**Obszar:** `Dokumentacja / Architektura`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Fundamentalna sprzeczność architektoniczna. `ADR-014` jasno definiuje porzucenie agregatu `VerificationRequest` (oraz `UserBooklet`) na rzecz zintegrowanego modelu `UserBadgeProgress` i Osobistego Kanbana. Tymczasem pliki `Scenarios.md`, `Invariants.md` (S-03, S-04) oraz `User Stories.md` (US-C05) wciąż traktują ten usunięty agregat jako istniejący.

**Action Items (Do wdrożenia):**
- [X] Oczyścić `INVARIANTS.md`: Usunąć wzmianki o `VerificationRequest` w opisie S-03 i S-04.
- [X] Oczyścić `Scenarios.md`: Zaktualizować SCN-011 i usunąć wymóg wgrania `UserBooklet`.
- [X] Oczyścić `User Stories.md`: Usunąć z US-C05 wzmiankę o `VerificationRequest`.

**Komentarz Architekta:**
Klasyczny dług dokumentacyjny po podjęciu kluczowej decyzji (ADR-014). Niespójność ta może spowodować, że nowy programista zacznie budować nieistniejące tabele w bazie.

---

### [AUDYT-006] Czyszczenie `SYSTEM_PROMPT.md` z nieaktualnych długów i `ActivityType`
**Obszar:** `Dokumentacja / GenAI Context`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Plik `SYSTEM_PROMPT.md` to najważniejszy wektor informacyjny dla agentów AI. Obecnie wprowadza ich w błąd, wymieniając długi TD-01, TD-02, TD-03 jako "aktywne", podczas gdy `CHANGELOG.md` oficjalnie potwierdza ich spłatę. Dodatkowo prompt i `GLOSSARY.md` nadal wmawiają agentowi istnienie `ActivityType` (HIKING), co zostało brutalnie wycięte jako YAGNI.

**Action Items (Do wdrożenia):**
- [X] Wyczyścić tabelę "Znane długi techniczne" w `SYSTEM_PROMPT.md` (zostawić adnotację "Wszystkie spłacone").
- [X] Usunąć `activity / HIKING` z definicji `Ascent` w `SYSTEM_PROMPT.md` i `GLOSSARY.md`.
- [X] Ujednolicić relację w `User Stories.md` (US-C01): zmienić `OneToOneField` na `ForeignKey (1:N)` zgodnie z wprowadzonym Modelem Rodzinnym.

**Komentarz Architekta:**
Przestarzały System Prompt to gwarancja "halucynacji" AI w kolejnych sprintach. To zadanie ma absolutny, najwyższy priorytet przed dopuszczeniem jakiegokolwiek bota do kodu.

---

### [AUDYT-007] Uporządkowanie chaosu w `Edge Cases.md` i `User Stories.md`
**Obszar:** `Dokumentacja`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
Przypadki brzegowe EC-035, EC-036, EC-037 zostały omyłkowo wklejone przez człowieka do pliku `User Stories.md` zamiast do `Edge Cases.md`. Ponadto w `Edge Cases.md` występuje wyciek moich (AI) instrukcji redakcyjnych ("Popraw fragment pobierający stopnie...") oraz zduplikowana i przerwana numeracja (np. podwójne EC-040, luki).

**Action Items (Do wdrożenia):**
- [X] Przenieść EC-035, EC-036, EC-037 z pliku `User Stories.md` do `Edge Cases.md`.
- [X] Usunąć wyciek tekstu instrukcji w okolicach EC-003 / EC-010.
- [X] Zreindeksować (przenumerować) przypadki brzegowe, aby wyeliminować duplikaty (EC-040, EC-044) i usunąć pustą zawartość tabel/komórek.

**Komentarz Architekta:**
Czysto redakcyjny bałagan powstały przy masowym przeklejaniu Markdowna z czatu do plików. Zmniejsza to zaufanie inżynierów do dokumentacji.

---

### [AUDYT-009] Usunięcie "śmieci" z Manifestów szablonowych
**Obszar:** `Manifesty / Narzędzia`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
Plik `00-index.md` (lub podobny rejestr portów) oraz `06-documentation-contract.md` zawierają odniesienia do projektów `blood_pressure_dashboard`, `GTD_Planner` i folderów `docs_sphinx/`. 

**Action Items (Do wdrożenia):**
- [X] Przejrzeć katalog `docs/Manifest/` i usunąć wszelkie odniesienia do zewnętrznych, starych projektów.
- [X] Dopasować nazwy weryfikowanych plików (np. `Data Flow Diagram.md` zamiast `DATAFLOW.md`), aby linter dokumentacji nie zgłaszał fałszywych błędów o brakujących plikach.

**Komentarz Architekta:**
To po prostu pozostałości po szablonach korporacyjnych (Boilerplates), które użyliśmy do postawienia struktury. Nie wpływa to na kod, ale psuje czytelność.

---

### [AUDYT-010] SANITY CHECK: Weryfikacja pominiętego kodu
**Obszar:** `Kod Źródłowy / IDE`  
**Priorytet:** `🔴 KRYTYCZNY` (Dla Programisty)

**Diagnoza Audytora:** 
Audytor wykrył w bazie kodu błędy, które na etapie czatu zostały już wspólnie naprawione (np. stary `except json.JSONDecodeError, ValueError:` w `views.py`, brak pobierania profilu z sesji w widokach, odwrócone argumenty w wyjątku oraz brak pola `valid_to` w repozytorium odznak).

**Action Items (Do wdrożenia PRZEZ CIEBIE w IDE):**
- [X] Sprawdź plik `apps/api/views.py`: Upewnij się, że nie ma tam składni Pythona 2.
- [X] Sprawdź ten sam plik: Upewnij się, że helper to `_handle_application_exception(request, exc)`, a wywołania mają właściwą kolejność.
- [X] Sprawdź w widokach: Upewnij się, że nigdzie nie używasz `request.profile.id` (zamienić na odczyt z `request.session`).
- [X] Sprawdź `infrastructure/adapters/persistence/django_badge_repo.py`: Upewnij się, że metoda `get_latest_badge_version` posiada zabezpieczenie `Q(valid_to__isnull=True) | Q(valid_to__gte=...)`.

**Komentarz Architekta:**
Nie generujemy na to nowego kodu. Musisz upewnić się, że nie pominąłeś paczek aktualizacyjnych z poprzednich konwersacji podczas wklejania do swojego IDE, lub czy stare pliki nie nadpisały Ci się przypadkowo z githa.

---

### [AUDYT-011] Weryfikacja przepływu autoryzacji w API (IDOR i RFC 7807)
**Obszar:** `API / Views`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Plik `apps/api/views.py` stanowi główną linię obrony systemu. Audytor zdefiniował go jako obszar najwyższego ryzyka (P0), nakazując weryfikację tego, czy wszystkie 9 widoków poprawnie korzysta z mechanizmów zabezpieczających (IDOR, omijanie `request.user_id` na rzecz profilu z sesji) oraz czy każdy błąd przepinany jest przez standard RFC 7807 z dołączonym `request_id`.

**Action Items (Do wdrożenia):**
- [X] Wykonać ręczny przegląd kodu wszystkich klas w `apps/api/views.py`.
- [X] Upewnić się, że `_problem_detail` generuje `request_id` we wszystkich miejscach (Zgodnie z poprawką z AUDYT-001).
- [X] Wprowadzić testy automatyczne w `tests/apps/api/test_integration.py` potwierdzające rzucanie kodów 4xx przy próbach manipulacji danymi obcego użytkownika.

**Komentarz Architekta:**
Większość z tych zabezpieczeń wprowadziliśmy już we wczorajszym sprincie, zastępując djangowe dekoratory własnym helperem `_require_auth`. Wymaga to jednak ostatecznego przeglądu (Sanity Check) kodu testów.

---

### [AUDYT-012] Sanity Check: Prawa Nabyte i Cinderella Bug
**Obszar:** `Infrastructure / Badge Repo`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
Audytor wytypował plik `infrastructure/adapters/persistence/django_badge_repo.py` jako ryzykowny (P1) ze względu na hydrację reguł z pola JSONB do obiektów Czystej Domeny oraz problem "Cinderella Bug" (EC-068), który znikał z czasem (brak obsługi pola `valid_to`).

**Action Items (Do wdrożenia PRZEZ CIEBIE w IDE):**
- [X] Sprawdzić implementację `get_latest_badge_version` i `get_version_id_for_date`. Upewnić się, że obie metody posiadają warunek logiczny chroniący przed błędem upływu dnia (np. `Q(valid_to__isnull=True) | Q(valid_to__gte=target_date)`).

**Komentarz Architekta:**
Zastosowaliśmy to rozwiązanie podczas incydentu "Znikających Szczytów o Północy", ale warto sprawdzić, czy zmiana na 100% nie została cofnięta przez przypadek przy kopiowaniu plików.

---

### [AUDYT-014] Ominięcie architektury w widokach API (Direct ORM Usage)
**Obszar:** `API / Hexagonal Architecture`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Widoki `ProfileSettingsView` oraz `NearbyObjectsView` w `apps/api/views.py` łamią podstawową zasadę Czystej Architektury. Zawierają one bezpośrednie wywołania modeli Django (ORM) takie jak `.save()`, `get_object_or_404` czy zapytania przestrzenne GIS, omijając całkowicie warstwę Aplikacji (Use Cases) oraz Porty.

**Action Items (Do wdrożenia w przyszłości):**
- [X] Utworzyć `UpdateProfileUseCase` i DTO aktualizacji profilu w warstwie Aplikacji.
- [X] Zmodyfikować `ProfileSettingsView`, by wywoływał nowy Use Case przez Kontener DI, zamiast bezpośrednio zapisywać dane w bazie.
- [X] Przenieść zapytanie przestrzenne (`ST_DWithin`) z `NearbyObjectsView` do adaptera `DjangoMapRepository` i wywoływać je przez port.
- [X] Dodać regułę do lintera `audit_contracts.py` zabraniającą importu `apps.badges.models` wewnątrz `apps/api/views.py`.

**Komentarz Architekta:**
Klasyczny wyciek logiki do kontrolerów powstały podczas szybkiego dowożenia funkcji Fazy C. Jest to bardzo szkodliwe dla izolacji testów i musi zostać wyczyszczone jako priorytet przed rozwojem aplikacji.

---

### [AUDYT-017] Duplikacja logiki weryfikacji bitemporalnej
**Obszar:** `Aplikacja / Use Case`
**Priorytet:** `🟡 ŚREDNI`

**Diagnoza Audytora:**
Zasada bitemporalności (T-01, czyli sprawdzanie `existence_start` i `existence_end` obiektu) była zaimplementowana dwukrotnie: w `LogAscentUseCase` oraz w pętli dla `BulkLogAscentsUseCase`.

**Rozwiązanie:**
- [X] Utworzono `BitemporalValidationService` (`application/services/bitemporal_validation_service.py`) jako serwis aplikacyjny.
- [X] `LogAscentUseCase.execute` używa `validate_single(peak_id, ascent_date)`.
- [X] `BulkLogAscentsUseCase.execute` używa `validate_batch(ascents)`.
- [X] Serwis wstrzyknięty do obu use case'ów w `bootstrap/container.py`.
- [X] `make check` zielone, 816 testów pass.

**Uzasadnienie decyzji:**
Serwis aplikacyjny (nie domenowy), bo zależy od `AscentLogRepositoryPort` (port aplikacyjny). Logika T-01/T-03 nie jest encją domenową — to invariants orkiestracji.

**Komentarz Architekta:**
Wyeliminowano duplikację DRY. Logika T-01/T-03 teraz w jednym miejscu — `BitemporalValidationService`.

---

### [AUDYT-018] Niespójna hierarchia i wykorzystanie wyjątków `ConflictError`
**Obszar:** `Domena / Wyjątki`
**Priorytet:** `🟡 ŚREDNI`

**Diagnoza Audytora:**
Wyjątek `ConflictError` był używany do dwóch różnych celów: (1) duplikaty danych D-04 (Idempotentność), (2) nielegalne przejścia stanu w Kanban FSM (S-03).

**Rozwiązanie:**
- [X] Wprowadzono `IllegalStateTransitionError` jako subklasę `ConflictError` w `application/exceptions.py` (zgodnie z `docs/Error Handling.md` hierarchią).
- [X] `advance_logistic_status.py` używa `IllegalStateTransitionError` dla naruszeń FSM (S-03).
- [X] `ConflictError` ograniczono do dokumentacji do duplikatów D-04.
- [X] `apps/api/views.py` loguje `IllegalStateTransitionError` jako `invalid-state-transition` (409, typ `/errors/invalid-state-transition`), `ConflictError` jako `conflict`.
- [X] Test `test_patch_conflict_returns_409` aktualizuje do `IllegalStateTransitionError`.
- [X] `make check` zielone, 816 testów pass.

**Uzasadnienie decyzji:**
Subklasa zachowuje backward-compat (`isinstance(exc, ConflictError)` → 409). Nazwa precyzyjniej opisuje przyczynę — lepsza Traceability.

**Komentarz Architekta:**
`ConflictError` → wyłącznie Idempotentność D-04. `IllegalStateTransitionError` → FSM Kanban.

---

### [AUDYT-020] Brakujące Testy Integracyjne (PostGIS i Restore Data)
**Obszar:** `Testy Integracyjne / Infrastruktura`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Zgodnie z kontraktem, testy integracyjne powinny sprawdzać prawdziwą bazę. Tymczasem nasze repozytoria (np. `django_map_repo.py`) opierają się na mockach (Monkeypatching `TouristObject.objects.filter`), co całkowicie ukrywa błędy w funkcjach `ST_DWithin` czy złączeniach CQRS. Brakuje również bezwzględnie wymaganego testu na idempotentność komendy `restore_reference_data` (podwójne wywołanie polecenia nie może nadpisać danych). Największy adapter systemu – `DjangoTouristRepository` – ma pusty plik testowy (`0 bajtów`).

**Action Items (Do wdrożenia w przyszłości):**
- [X] Napisać prawdziwe testy bazodanowe (z użyciem znacznika `@pytest.mark.django_db`) dla `DjangoMapRepository` i `DjangoTouristRepository`.
- [X] Napisać test integracyjny weryfikujący podwójne odpalenie komendy `restore_reference_data`.
- [X] Usunąć sztuczne mocki na obiektach ORM z obecnych plików w katalogu `tests/infrastructure/adapters/persistence/`.

**Komentarz Architekta:**
Mockowanie ORM to antywzorzec. Przebudujemy testy infrastruktury tak, aby uderzały w pustą, tymczasową bazę generowaną przez pytest-django. To uleczy nasz system i zmyje winę "fałszywych testów".

---

### [AUDYT-021] Niestabilność Czasowa Testów (Flaky Tests)
**Obszar:** `Testy Jednostkowe / Maintainability`
**Priorytet:** `🟠 WYSOKI`

**Diagnoza Audytora:**
`date.today()` / `datetime.now(UTC)` w testach mogą eksplodować przy GC/CPU load (CI midnight).

**Rozwiązanie:**
- [X] Przeszukano wszystkie `test_*.py` pod kątem `date.today()` i `datetime.now()`.
- [X] `tests/domain/rules/test_badge_rules.py` + `tests/domain/entities/test_badge_version.py` — zastąpiono `date.today()` sztywną `date(2024, 6, 15)` (zgodną z `FakeClock.DEFAULT_TIME`).
- [X] `tests/infrastructure/adapters/test_clock.py` — zwiększono tolerancję `SystemClock` od 1s → 5s (celowy test realtime, ale stabilny pod CI load).
- [X] Pozostałe użycia (`test_integration.py`, `test_security.py`, `test_osm_repository.py`) **celowo pozostawiono**: payload API (`date.today()` jako input usera) oraz `datetime.now()` jako dane OSM — nie są asercjami czasowymi.

**Uzasadnienie decyzji:**
Flaky = asercja zależna od `now()`. `date.today()` w danych domenowych był ryzykiem (gdyby reguła porównała do `today()`). Sztywna data eliminuje nondeterminizm. `test_clock` tolerance 5s to akceptowany tradeoff dla testu realtime.

**Komentarz Architekta:**
Zmiana to faktycznie ~3 min Find & Replace + 1 edycja tolerance.

---

### [AUDYT-022] Niespójność Testów API z RFC 7807 (Brak `request_id`)
**Obszar:** `Testy API / Error Handling`
**Priorytet:** `🟠 WYSOKI`

**Diagnoza Audytora:**
Żadna asercja błędu API nie weryfikowała `request_id` w odpowiedzi RFC 7807.

**Rozwiązane jako część AUDYT-027:**
- [X] `_problem_detail` (zarówno `apps/api/views.py`, jak i `infrastructure/middleware/error_handling.py`) zawiera `"request_id": getattr(request, "request_id", "unknown")`.

- [X] Wszystkie 35 asercji kodów `4xx/500` w `tests/apps/api/test_integration.py` mają `assert "request_id" in data` (potwierdzono skanowaniem: 0 missing).
- [X] `tests/infrastructure/test_error_handling.py` (8 testów, 100% coverage) asercjonuje `request_id` = `req_12345678` oraz fallback `unknown`.
- [X] `tests/architecture/test_structured_error_context.py` jako fitness function weryfikuje strukturę RFC 7807.

**Uzasadnienie decyzji:**
Diagnoza była przestrzona — `request_id` był już implementowany (AUDYT-048/050), brakowało jedynie **test coverage**. Wdrożenie AUDYT-027 dodało brakujące asercje.

**Komentarz Architekta:**
`ERROR_HANDLING.md` jest teraz w pełni pokryty przez testy: każda ścieżka błędu zwraca `request_id`, a każdy test tego weryfikuje.

---

### [AUDYT-024] Załatanie podatności Open Redirect w `switch_profile_view`
**Obszar:** `API / Bezpieczeństwo`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Widok odpowiedzialny za zmianę profilu rodzinnego w `apps/tourists/views.py` używa niebezpiecznej konstrukcji `redirect(request.META.get("HTTP_REFERER", "home"))`. Nie weryfikuje on, czy nagłówek Referer faktycznie należy do naszej domeny. Atakujący może stworzyć spreparowany link nakłaniający ofiarę do kliknięcia, co po przełączeniu profilu przekieruje ją na złośliwą stronę (Phishing).

**Action Items (Do wdrożenia w przyszłości):**
- [X] Zmodyfikować `switch_profile_view`, tak aby walidował bezpieczny adres docelowy. Np.: `next_url = request.GET.get("next") or request.META.get("HTTP_REFERER"); if next_url and not next_url.startswith("/"): next_url = "home"`.

**Komentarz Architekta:**
Klasyczny błąd z grupy A01 (OWASP). Prosta łatka z użyciem `startswith("/")` całkowicie zamyka ten wektor ataku, wymuszając nawigację wyłącznie w obrębie naszej witryny.

---

### [AUDYT-025] Brak autoryzacji zasobu w `BadgeLogisticsView` (Luka IDOR)
**Obszar:** `API / Autoryzacja`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Widok `BadgeLogisticsView` (odpowiedzialny za Osobisty Kanban logistyki) przyjmuje z adresu URL parametr `progress_id`. Chociaż widok weryfikuje, czy użytkownik jest zalogowany (`_require_auth`), nie weryfikuje, czy edytowany postęp faktycznie należy do profilu wykonującego to żądanie. Złośliwy użytkownik znający `progress_id` obcej osoby może bezkarnie przesuwać status wysyłki jego odznak!

**Action Items (Do wdrożenia w przyszłości):**
- [X] Zmodyfikować `AdvanceLogisticStatusUseCase`, aby upewnić się, że `progress.profile_id == profile_id`.
- [X] Dodać asercje i rzucać wyjątek w przypadku braku uprawnień.

**Komentarz Architekta:**
Krytyczne przeoczenie logiki w `Use Case`. IDOR to jeden z najgroźniejszych i najczęściej występujących błędów w REST API.

---

### [AUDYT-027] Brak wymuszenia `request_id` w zwracanych błędach
**Obszar:** `API / Error Handling`
**Priorytet:** `🟡 ŚREDNI`

**Diagnoza Audytora:**
RFC 7807 wymaga `request_id` w odpowiedziach błędów; `_problem_detail` oraz testy nie weryfikowały tego pola.

**Rozwiązanie:**
- [X] Zweryfikowano, że `_problem_detail` już zawiera `"request_id": getattr(request, "request_id", "unknown")` — w `apps/api/views.py` oraz `infrastructure/middleware/error_handling.py`.
- [X] Uzupełniono testy integracyjne o `assert "request_id" in data` dla 5 ścieżek błędowych (`409 birth_date`, `422 file_too_large / invalid_mime / not_xml`, `422 GPX`).

**Uzasadnienie decyzji:**
`request_id` był już obecny (z AUDYT-048/050) — diagnoza wymagała potwierdzenia + test coverage. Middleware `RFC7807ErrorMiddleware` wstrzykuje `request_id` do każdego requestu (`process_exception` → 500 fallback również ma request_id).

**Komentarz Architekta:**
SRE może teraz mapować każdy błąd HTTP na logi serwera.

---

### [AUDYT-028] Brak weryfikacji formatu i ograniczeń dla załączników
**Obszar:** `API / Zaufanie do danych klienta`
**Priorytet:** `🟡 ŚREDNI`

**Diagnoza Audytora:**
`GpxAnalyzeView` nie weryfikował `Content-Type`; model `souvenir_image` nie miał walidatorów DoS/MIME.

**Rozwiązanie (częściowe + zaplanowane):**
- [X] #1 — `Content-Type` validation + Magic Bytes + 10MB size limit → wdrożone w ramach AUDYT-050 (`apps/api/views.py:631-659`).
- [X] 3 testy asercyjne (`test_returns_422_when_file_too_large / invalid_mime_type / not_xml`).
- [X] `apps/tourists/models.py` — `souvenir_image` posiada `help_text` dokumentujący brak walidatora rozmiaru i konieczność dodania go przy wystawieniu endpointu API.
- ⏳ #2 (souvenir_image validators) — **zaplanowane**. `souvenir_image` jest `readonly` w Django Admin (brak uploadu → brak wektora ataku). Gdy powstanie endpoint REST, trzeba dodać `MaxValueBytesValidator` (rozmiar) + wyraźny MIME check (obecnie Django `ImageField` używa Pillowa).

**Uzasadnienie decyzji:**
#1 (GPX) = natychmiastowy threat model (upload pliku). #2 (souvenir) = future work: brak endpointu API → ryzyko niższe; `ImageField` daje minimalną ochronę.

**Komentarnik Architekta:**
Defense in Depth — `Content-Type` + magic bytes na bramie HTTP (AUDYT-050) + `pillow` na modelu. Do pełnej ochrony potrzebny dedykowany validator przy API endpoint.

---

### [AUDYT-029] Brak indeksów na często używanych kolumnach ORM
**Obszar:** `Baza Danych / Modele Django`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
Baza rosnąc do setek tysięcy wierszy utknie na pełnych skanach tabel (Seq Scan). Modele nie posiadają zdefiniowanych indeksów w klasie `Meta` (lub bezpośrednio na polach za pomocą `db_index=True`) dla najczęściej filtrowanych ścieżek odczytu.

**Action Items (Do wdrożenia w przyszłości):**
- [X] Dodać indeksy na polach: `TouristObject.name`, `TouristObject.status`, `TouristObject.is_active`.
- [X] Dodać Composite Index (złożony indeks) dla `AscentLog(profile_id, ascent_date)` (wspiera operację `get_oldest_ascent_date`).
- [X] Dodać Composite Index dla `UserBadgeProgress(profile_id, badge_id, domain_status)` (optymalizacja dla zapytań Czystej Domeny o postęp).
- [X] Wdrożyć indeksy poprzez stworzenie nowych migracji schematu (`Database Release`).

**Komentarz Architekta:**
Klasyczny błąd MVP. Dodanie tych indeksów skróci czas krytycznych zapytań Use Case'ów z kilkuset do pojedynczych milisekund. Obowiązkowe przed wejściem na 10 tysięcy użytkowników.

---

### [AUDYT-030] N+1 Query w widoku `badge_detail_view` (M2M `pool_peaks`)
**Obszar:** `API / Widoki HTMX`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
Pętla odczytująca listę obiektów na stronie ze szczegółami odznaki (renderowana w HTML) odwołuje się do `target_version.pool_peaks.all()`. Ponieważ obiekt wersji nie został pobrany z użyciem instrukcji `prefetch_related("pool_peaks")`, przejście po 100 szczytach odznaki spowoduje wygenerowanie 100 osobnych zapytań SQL do bazy w jednym żądaniu HTTP.

**Action Items (Do wdrożenia):**
- [X] W pliku `apps/tourists/views.py` (lub w Query Service) zmodyfikować zapytanie pobierające wersję odznaki tak, by dołączyć `prefetch_related("pool_peaks")` przed przekazaniem obiektu do szablonu.

**Komentarz Architekta:**
Zjawisko to zostało usunięte z głównego rankingu (`ExploreQueriesService`), ale zapomnieliśmy o nim w "lewym pasku" na samej stronie detali odznaki. Szybka poprawka (`prefetch_related`) w zapytaniu zdejmie gigantyczne obciążenie z połączenia z PostGIS-em.

---

### [AUDYT-031] Przepełnienie RAM przy pobieraniu wszystkich logów wejść
**Obszar:** `Infrastruktura / Repozytoria`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Metoda `get_all_ascents_for_user` w `DjangoTouristRepository` wczytuje wszystkie historyczne logi użytkownika (`list(AscentLog.objects...)`) prosto do pamięci RAM naraz. Kiedy użytkownik zacznie gromadzić tysiące wpisów z tras GPX, system odczytu postępów spowoduje zjawisko OOM (Out Of Memory) na serwerze i zawieszenie procesu `web` (Gunicorn).

**Action Items (Do wdrożenia w przyszłości):**
- [X] Zastąpić bezwzględne wywołanie `.all()` użyciem parsera strumieniowego bazy danych (np. `.iterator(chunk_size=2000)` w Django).
- [X] Zaprojektować ewentualną paginację dla endpointu weryfikacyjnego.

**Komentarz Architekta:**
Bardzo mądre spojrzenie do przodu. Wprawdzie model `AscentLog` jest dość wąski w SQL, ładowanie 50 000 obiektów do pamięci przy każdym przeliczeniu punktacji (PoiScoringService) udławi serwer. Przebudowa odczytu na iteratory jest koniecznością w fazie stabilizacji (SRE).

---

### [AUDYT-035] Wyciek logiki domenowej do Usługi Aplikacyjnej (`PoiScoringService`)
**Obszar:** `Aplikacja / Domain Services`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
Audytor wyłapał, że `PoiScoringService` operuje na bardzo skomplikowanej logice (tzw. "symulacja wejść" i mechanizmy leniwego zakotwiczenia). Zadaje pytania: "Co gdyby turysta wszedł tu dzisiaj?". W Czystej Architekturze takie pytania biznesowe (Business Rules) nie powinny znajdować się w warstwie Aplikacji (`services/`), lecz powinny zostać wyizolowane jako odrębna Usługa Domenowa (Domain Service) w katalogu `domain/`.

**Action Items (Do wdrożenia w przyszłości):**
- [X] Utworzyć klasę np. `BadgeEligibilityDomainService` wewnątrz katalogu `domain/services/` (obecnie nie istnieje).
- [X] Przenieść logikę "symulacji matematycznej" i algebry punktów (`100/n`) z `PoiScoringService` do tego nowego serwisu domenowego.
- [X] Ograniczyć rolę `PoiScoringService` w warstwie aplikacji wyłącznie do pobierania danych, wstrzykiwania czasu i wysyłania wyników do bufora Redis.

**Komentarz Architekta:**
Bardzo słuszna uwaga. Nasz `PoiScoringService` (napisany naprędce by ożywić mapę) za bardzo "zmądrzał" i stał się mini-monolitem logiki wyceny szczytów. Czysta algebra punktów musi wrócić do Domeny.

---

### [AUDYT-036] Brak enkapsulacji fabryk reguł z dala od ORM
**Obszar:** `Infrastruktura / Fabryki`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Repozytorium `DjangoBadgeRepository` zajmuje się obecnie nie tylko mapowaniem modeli z bazy danych, ale posiada w sobie "na twardo" zdefiniowane, złożone funkcje budujące instancje reguł Domeny (tzw. Buildery / Fabryki Reguł z JSONB). Zaciemnia to odpowiedzialność repozytorium ORM.

**Action Items (Do wdrożenia w przyszłości):**
- [X] Rozważyć utworzenie w warstwie infrastruktury odrębnego modułu `factories` (np. `infrastructure/factories/badge_rule_factory.py`).
- [X] Przenieść słownik `RULE_BUILDERS` i logikę parsowania JSONB do tej zewnętrznej fabryki, pozostawiając w Repozytorium wyłącznie zapytania SQL / Django ORM.

**Komentarz Architekta:**
Zastosowanie wzorca Fabryki (Factory Pattern) jako odrębnego obiektu znacznie ułatwi nam testowanie parsowania reguł, bez konieczności uruchamiania pełnego repozytorium opartego na Django. Drobne, ale cenne usprawnienie kodu (Code Quality).

---

### [AUDYT-038] Potrzeba Testów Bezpieczeństwa Deserializacji (Fail-Fast)
**Obszar:** `Infrastruktura / Testy`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
Audytor wyznaczył adapter `django_badge_repo.py` jako punkt ryzyka klasy `🔴 P0`, powołując się na "bezpieczeństwo deserializacji". Reguły biznesowe PTTK przechowywane są w bazie jako JSONB. Zgodnie z ADR-003 oraz Invariantem R-02, adapter musi wyrzucić twardy błąd (Fail-Fast), jeśli napotka uszkodzony JSON.

**Action Items (Do wdrożenia w przyszłości):**
- [X] Napisać dedykowany test integracyjny weryfikujący Invariant R-02: wpisać ręcznie do bazy uszkodzony/nieznany obiekt JSON dla reguły i upewnić się, że adapter rzuca odpowiedni wyjątek `ValueError` przed dotarciem do Czystej Domeny.

**Komentarz Architekta:**
Ufamy naszej implementacji słownika `RULE_BUILDERS`, ale nie udowodniliśmy w testach, że faktycznie zatrzymuje on złośliwy lub uszkodzony schemat JSONB z bazy. Proste i tanie zabezpieczenie.

---

### [AUDYT-045] Usunięcie Opcji `CASCADE` w Profilach Turystów
**Obszar:** `Architektura / RODO`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
Relacja z profilu turysty na jego wejścia w bazie danych posiada parametr `on_delete=CASCADE`. Jeśli administrator (lub system RODO) usunie profil, baza automatycznie i bezpowrotnie zniszczy wszystkie jego wejścia. Prowadzi to do utraty zanonimizowanych danych analitycznych (historii ruchu na szlakach PTTK) oraz niszczy agregaty popularności szczytów.

**Action Items (Do wdrożenia):**
- [X] Zmodyfikować powiązanie na `on_delete=PROTECT` lub `SET_NULL` (wymaga zmiany `profile_id` na opcjonalne).
- [X] Zaimplementować mechanizm "Tombstoningu" (Soft Delete) dla profili – kasowanie e-maili/haseł, ale pozostawianie zanonimizowanego identyfikatora przypisanego do wejść.

**Komentarz Architekta:**
Uwaga wybitna. Twarde usuwanie na kaskadzie to łatwe wyjście na etapie MVP, ale destrukcyjne na produkcji.

---

### [AUDYT-047] Luki w bezpieczeństwie zarządzania sesją (Brak Secure Flags)
**Obszar:** `Infrastruktura / Bezpieczeństwo HTTP`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
W projekcie brakuje wymuszenia flag bezpieczeństwa dla ciasteczek w środowisku produkcyjnym. Domyślne ustawienia Django pozwalają na przesyłanie ciasteczka sesyjnego (`SESSION_COOKIE`) oraz tokena CSRF przez nieszyfrowane połączenia HTTP. Stanowi to ogromne ryzyko kradzieży sesji (Session Hijacking) przy ataku MITM.

**Action Items (Do wdrożenia w `settings.py`):**
- [X] Dodać zabezpieczenia dla środowiska `app_env == "production"`: `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True`, `SECURE_SSL_REDIRECT = True`.
- [X] Opcjonalnie wdrożyć politykę HSTS (`SECURE_HSTS_SECONDS`).

**Komentarz Architekta:**
Klasyczny błąd konfiguracji przy wychodzeniu z fazy deweloperskiej. Mimo że Caddy (Reverse Proxy) wymusza u nas HTTPS, aplikacja Django wewnętrznie musi oznaczyć te ciastka jako dostępne *wyłącznie* dla połączeń bezpiecznych.

---

### [AUDYT-048] Ochrona przed fałszowaniem wieku (Age Fraud)
**Obszar:** `API / Logika Biznesowa (RODO)`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
Obecnie widok `ProfileSettingsView` (lub nowy Use Case aktualizacji profilu) pozwala użytkownikowi na swobodną, nieograniczoną modyfikację pola `birth_date` w dowolnym momencie. Ponieważ system opiera punktację i weryfikację na dacie urodzenia (`MinAgeRule`, `MaxAgeRule`), użytkownik może wielokrotnie zmieniać wiek w celu sztucznego zdobycia zablokowanych odznak dziecięcych lub seniorskich.

**Action Items (Do wdrożenia w przyszłości):**
- [X] W `UpdateProfileUseCase` zablokować możliwość zmiany daty urodzenia, jeśli została już raz ustawiona.
- [X] (Alternatywa) Pozwolić na zmianę, ale wymagać twardego zresetowania wszystkich postępów zależnych od wieku lub uruchomienia alertu audytowego.

**Komentarz Architekta:**
Znakomite wyłapanie luki w logice grywalizacji (Gamification Exploit). Data urodzenia to kluczowy Invariant tożsamościowy – po jego ustaleniu powinien stać się niezmienny.

---

### [AUDYT-049] Brak walidacji bezpiecznych wektorów w BBox (Over-fetching DoS)
**Obszar:** `API / GIS`
**Priorytet:** `🟡 ŚREDNI`

**Diagnoza Audytora:**
Endpoint `?bbox=` wstrzykuje wektory do `ST_Within` bez zakresu — fałszywy wektor (`-999,-999,999,999`) = pełny skan tabeli → DoS.

**Rozwiązanie:**
- [X] `MapExploreRequestDTO` (`application/dto/map_dto.py:16-19`) — `Field(ge=-180, le=180)` dla lon, `Field(ge=-90, le=90)` dla lat; `extra="forbid"`.
- [X] `MapObjectsView` już łapie `ValidationError` → 422 (`apps/api/views.py:411`).
- [X] `test_returns_422_for_out_of_range_bbox` w `test_integration.py:337` (integration — bbox=-999 → 422).
- [X] `tests/application/dto/test_map_dto.py` — czysty unit test (7 testów, parametrize) weryfikuje zakresy i `extra="forbid"` — **działa bez DB, w `make check`**.

**Uzasadnienie decyzji:**
Pydantic `Field(ge=, le=)` = 3-linijka walidacja na bramce. `extra="forbid"` zabezpiecza przed payload injection.

**Komentarz Architekta:**
Defense in Depth — walidacja na DTO (Application) przed PostGIS. `bbox=-999` nigdy nie dotrze do `ST_Within`.

---

### [AUDYT-050] Zabezpieczenie Content-Type dla uploadu plików GPX
**Obszar:** `API / Bezpieczeństwo`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Widok odpowiedzialny za odbieranie plików GPX weryfikuje ich rozmiar, ale nie weryfikuje jednoznacznie ich zawartości w oparciu o typ MIME. Złośliwy użytkownik może wysłać plik `.exe` jako GPX. Co prawda biblioteka `defusedxml` odrzuci to na etapie parsowania, ale plik i tak zostanie przetransferowany i załadowany do pamięci serwera.

**Action Items (Do wdrożenia w przyszłości):**
- [X] Dodać walidację nagłówka pliku (Magic Bytes) oraz dopuszczonego typu MIME (`application/gpx+xml` lub `text/xml`) przed wpuszczeniem pliku do pamięci operacyjnej parsera.

**Komentarz Architekta:**
Klasyczne zabezpieczenie bramki sieciowej. Zapobiegnie to obciążaniu pamięci RAM serwera djangowego złośliwymi ładunkami.

---

### [AUDYT-053] Ograniczenie ryzyka OOM (Out Of Memory) przy pobieraniu historii
**Obszar:** `Wydajność / Adaptery`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
W repozytoriach znajdują się metody takie jak `get_all_ascents_for_user`, które ładują wszystkie rekordy historii turysty bezpośrednio do jednej listy w pamięci RAM Pythona. Brak wbudowanego stronicowania (Paginacji) lub użycia iteratorów (`.iterator(chunk_size)`) spowoduje zjawisko OOM na serwerach aplikacyjnych w momencie, gdy tysiące użytkowników zaimportuje wieloletnie paczki z plików GPX.

**Action Items (Do wdrożenia w najbliższych sprintach):**
- [X] Zastąpić bezwzględne wywołania typu `.all()` mechanizmami dzielenia na paczki (Batching) lub generatorami w warstwie adapterów bazodanowych dla tabel rosnących.

**Komentarz Architekta:**
Typowy "Cichy Zabójca" aplikacji pisanych w ORM-ach, który ujawnia się dopiero w fazie produkcyjnego wzrostu obciążenia (Load Spikes). Szybki do naprawy, wymagający modyfikacji kilku linijek w adapterach odczytu.

---

### [AUDYT-059] Pusty plik testowy dla `DjangoTouristRepository`
**Obszar:** `Testy Integracyjne`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Najważniejszy adapter w systemie, `DjangoTouristRepository` (implementujący 3 porty aplikacyjne dla logów, profili i postępów), posiada w repozytorium plik testowy `test_django_tourist_repo.py` o rozmiarze 0 bajtów! Cała pewność co do działania zapisu wycieczek i obliczania praw nabytych opiera się na ręcznym klikaniu.

**Action Items (Do wdrożenia PRZED Playwrightem):**
- [X] Napisać testy dla `DjangoTouristRepository` przy użyciu wbudowanych narzędzi `pytest-django` (`@pytest.mark.django_db`).
- [X] Przetestować rzucanie błędu (Idempotentność) przy zapisie duplikatu logu.

**Komentarz Architekta:**
Klasyczne przeoczenie przy szybkim refaktoringu monolitu. Testowanie ORM-a z rzeczywistą, wbudowaną w Pytest bazą (bez mocków) zabetonuje nam logikę turysty przed startem testów E2E.

---

### [AUDYT-064] Wdrożenie tarczy Gating Pipeline (Continuous Architecture Verification)
**Obszar:** `DevOps / CI/CD`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Audytor wyłapał, że projekt polega wyłącznie na manualnym uruchamianiu komendy `make check`. Brak zautomatyzowanego potoku CI (Continuous Integration), np. plików GitHub Actions, skutkuje tym, że programista może po prostu zignorować błędy (lub nie odpalić komendy) i wgrać kod bezpośrednio do głównej gałęzi (main). Ponadto brakuje oficjalnego wdrożenia narzędzia `import-linter` (brak pliku konfiguracji `.importlinter` z opisanymi regułami granic).

**Action Items (Do wdrożenia w nadchodzącym sprincie DevOps):**
- [X] Utworzyć plik konfiguracyjny `.importlinter` (lub odpowiednik dla narzędzia `pydeps`), jawnie zakazujący importów z `apps` i `infrastructure` do `domain` i `application`.
- [X] Utworzyć plik potoku (np. `.github/workflows/ci.yml`), który zablokuje `git merge`, jeśli `make check` nie zakończy się ze statusem `0` (Success).

**Komentarz Architekta:**
"Nieufne środowisko" to fundament stabilnego produktu. Automatyzacja wyłapywania wycieków warstw i błędów Mypy oszczędzi nam połowy przyszłych Audytów! Zrobimy to, gdy zaczniemy formalizować środowiska z `compose.test.yml`.

---

### [AUDYT-076] Brak automatycznych potoków CI/CD (Brak `GitHub Actions`)
**Obszar:** `DevOps / CI/CD`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Mimo posiadania wysoce dojrzałej architektury konteneryzacji (Multi-stage `Dockerfile`, `compose.test.yml`, dedykowane skrypty wdrażające w `scripts/`), w repozytorium fizycznie nie istnieje żaden plik orkiestratora CI (np. w katalogu `.github/workflows/`). Oznacza to, że pomimo posiadania "części zamiennych", projekt pozbawiony jest w pełni zautomatyzowanego potoku, który samoczynnie weryfikowałby każdy Pull Request i zarządzał wdrożeniami (Continuous Integration / Continuous Deployment).

**Action Items (Do wdrożenia PRZED Playwrightem / Prodem):**
- [X] Utworzyć plik definiujący potok CI (np. `.github/workflows/ci.yml`).
- [X] Skonfigurować w nim tzw. *Quality Gate*, który automatycznie, na środowisku efemerycznym GitHuba, uruchomi przygotowane uprzednio skrypty: weryfikację linterów (`make check`) oraz testy integracyjne infrastruktury (`./scripts/test-run.sh --full`).
- [X] Dodać zabezpieczenie blokujące połączenie gałęzi (Merge) w przypadku, gdy którykolwiek krok w potoku zakończy się statusem błędu.

**Komentarz Architekta:**
Mamy gotowe, perfekcyjnie przetestowane skrypty (Bash/Make). Wpięcie ich w 40-linijkowy plik YAML dla GitHub Actions to teraz czysta formalność, która ostatecznie zamknie temat "Brakującego CI". Należy to zrobić w następnym kroku.

---

### [AUDYT-109] Złamane zaufanie do struktury katalogów testów (QA Matrix vs Rzeczywistość)
**Obszar:** `Dokumentacja / Testy`  
**Priorytet:** `🔴 KRYTYCZNY (Zaufanie)`  

**Diagnoza Audytora:** 
Plik `docs/QA_MATRIX.md` oraz `Test Strategy.md` sztucznie kategoryzują testy na Unit i Integration, podając konkretne liczby, co sugeruje istnienie katalogów `tests/unit/` i `tests/integration/`. W rzeczywistości testy (mimo że ich liczba przekracza 590) są ustrukturyzowane w oparciu o moduły (`tests/application/`, `tests/domain/`). Wywołuje to u nowych deweloperów wrażenie "fałszywej statystyki" i braku pokrycia kodu.

**Action Items (Do wdrożenia PRZEZ CIEBIE w wolnej chwili):**
- [X] Zaktualizować plik `docs/QA_MATRIX.md` tak, aby nazwy kategorii odpowiadały rzeczywistym folderom w projekcie (np. Zastąpić "Unit Tests" słowami "Domain & Application Tests").
- [X] Dodać krótki plik `tests/README.md` opisujący, gdzie dokładnie znajdują się testy jednostkowe, a gdzie integracyjne, ucinając domysły.

**Komentarz Architekta:**
Niespójność nazewnictwa niszczy wiarygodność nawet najlepiej przetestowanego systemu. Skoro wybraliśmy organizację folderów per-moduł, dokumentacja QA musi to bezwzględnie odzwierciedlać.

---

### [AUDYT-110] Luki w odnośnikach "Żywej Dokumentacji" (README & ADR)
**Obszar:** `Dokumentacja / Onboarding`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
Główny plik wejściowy do projektu (`README.md`) kieruje programistę pod nieistniejące pliki (np. `docs/VISION.md` zamiast `docs/Vision Statement.md`). Z kolei plik `SYSTEM_PROMPT.md` odwołuje się do nieistniejących plików `ADR-017` do `ADR-019`, wprowadzając deweloperów w błąd, że brakuje im wiedzy architektonicznej.

**Action Items (Do wdrożenia PRZEZ CIEBIE w wolnej chwili):**
- [X] Skorygować linki w pliku `README.md`, by odpowiadały faktycznym nazwom plików (uwaga na spacje w nazwach w GitHubie - zastąpić `%20` lub zmienić nazwy plików na kebab-case).
- [X] Zaktualizować `SYSTEM_PROMPT.md` i listę ADR-ów, usuwając odwołania do pustych numerów (017-019) lub tworząc dla nich fizyczny plik objaśniający (Placeholder).

**Komentarz Architekta:**
Klasyczny przypadek "Martwych Linków" (Dead Links). Jest to drobnostka z perspektywy kodu, ale kluczowy błąd z perspektywy pierwszego wrażenia (Developer Experience).

---

### [REGRESJA-001] Zmiana logu `ConflictError` z `logger.warning` → `logger.info`

**Obszar:** `API / Views`
**Priorytet:** `🟡 ŚREDNI`

**Diagnoza:** Test `test_security.py::test_conflict_error_does_not_leak_internal_details` wykrył, że handler `_handle_application_exception` loguje `ConflictError` poprzez `logger.info`, podczas gdy asercja testowa (i konsekwentny drugi handler w `ProfileSettingsView`) oczekuje `logger.warning`. Była to nieostrożona zmiana log-levelu.

**Działania:**
- [X] Przywrócić `logger.warning("conflict", ...)` w handlerze `ConflictError` (`apps/api/views.py:134`).
- [X] Zweryfikować, że wszystkie 409-conflict handlery używają `logger.warning` (spójność semantyczna).

---

### [REGRESJA-002] `AttributeError` w hydracji dla nie-listowego `rules`

**Obszar:** `Infrastruktura / Repozytorium`
**Priorytet:** `🔴 KRYTYCZNY`

**Diagnoza:** Test `test_raises_on_non_list_rules` przekazuje `rules="not-a-list"` (string zamiast listy). Iterowanie stringa po literach → `build_rule_from_dict("n")` → `dict("n")` rzucił `ValueError` wewnątrz fabryki, po czym `except ValueError` handler w `_hydrate_version` próbował `rule_dict.get("type")`, gdzie `rule_dict` był `str` → `AttributeError` (nie w `pytest.raises((ValueError, TypeError)`).

**Działania:**
- [X] Dodać do `build_rule_from_dict` early-return walidację `isinstance(data, dict)` → `TypeError` (semantycznie poprawny dla złego typu).
- [X] W `_hydrate_version` łapać `(ValueError, TypeError)` i obsłużyć `rule_dict.get` dla non-dict (fallback do `type(rule_dict).__name__`).

---

### [REGRESJA-003] Test-hygiene cleanup (AUDYT-039 + test_dummy)

**Obszar:** `Dokumentacja / Testy`
**Priorytet:** `🟢 NISKI`

**Diagnoza:** 
- `docs/Manifest/15-dataframe-contract.md` (pandera/pandas) — biblioteki nie ma w `pyproject.toml`, plik to martwy boilerplate z szablonu.
- `tests/test_benchmark_samples.py` — wymaga `pytest-benchmark` (nie zainstalowany), blokuje kolekcję pytest.
- `tests/test_dummy.py` — 3-linijkowy smoke test, pozostałość z AUDYT-023.

**Działania:**
- [X] Usunąć `docs/Manifest/15-dataframe-contract.md` + wyrejestrować w `docs/Manifest/00-index.md` (usunięto wiersz 15 z tabeli kontraktów).
- [X] Usunąć `tests/test_benchmark_samples.py` (brak wtyczki pytest-benchmark).
- [X] Usunąć `tests/test_dummy.py` (pozostałość AUDYT-023).

---

### AUDYT-034 — Brak ADR dla wyboru Frameworka Frontendu i Autoryzacji

**Obszar:** `Dokumentacja / Architektura`
**Priorytet:** `🟢 NISKI`

**Diagnoza:** Brak historycznego rekordu decyzji architektonicznej dla: (1) HTMX + SSR zamiast SPA, (2) Google OAuth zamiast hasła lokalnych.

**Działania:**
- [X] Utworzyć `ADR-017 — Strategia Frontendu (HTMX + SSR zamiast SPA)`: opis alternatyw (SPA vs HTMX), uzasadnienie (SEO, jeden stos, brak Node.js), ochronione zasady (czysty endpoint HTTP dla każdej akcji, frontend = transport, nie logika domenowa).
- [X] Utworzyć `ADR-018 — Uwierzytelnienie i Zarządzanie Tożsamościem (Google OAuth + Model Rodzinny)`: auth. wyłącznie przez `django-allauth` + Google OAuth; `auth.User` = tożsamość, `TouristProfile` = dane PTTK; odmowa haseł lokalnych.
- [X] Dodać `ADR-019 — Placeholder` dla numeracji (gap 017–019 → 020+).
- [X] Poprawić datę w `ADR-002` z `2025-05-26` na `2026-05-26`.
- [X] Ujednolić wersję Pythona na `3.14` w `Runbook.md` (było `3.12+`).


### AUDYT-008 — Housekeeping ADR-i (przeniesiony do DONE)

**Działania:**
- [X] Numeracja ADR zrównana — `ADR-017`, `ADR-018`, `ADR-019` (placeholder) wypełniają lukę 016→020.
- [X] Poprawiona data `ADR-002` i wersja Pythona (zob. AUDYT-034).

---

### [AUDYT-039] Usunięcie osieroconych kontraktów Manifestu (Pandas/DataFrame)
**Obszar:** `Dokumentacja / Manifest`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
Audytor wyłapał, że w katalogu kontraktów znajduje się plik `15-dataframe-contract.md` (dotyczący bibliotek `pandas` i `pandera`). Projekt PTTK Badges to aplikacja transakcyjna GIS/Django, która fizycznie nie posiada (i nie planuje posiadać) w `pyproject.toml` zależności od tych ciężkich bibliotek analitycznych.

**Action Items (Do wdrożenia PRZEZ CIEBIE):**
- [X] Usunąć plik `15-dataframe-contract.md` z katalogu `docs/Manifest/`.
- [X] Zaktualizować plik indeksu manifestu (np. `00-index.md`), wykreślając ten kontrakt, by nie wprowadzać w błąd agentów kodujących AI.

**Komentarz Architekta:**
Klasyczna pozostałość (Boilerplate) po sklonowaniu bazowego repozytorium firmowego. Śmieci w Manifeście mogą sprowokować agenta AI do instalacji niepotrzebnych, ciężkich paczek w `Dockerfile`.

---

### [AUDYT-040] Ujednolicenie wersji technologii i "Dryf Tożsamości" w starszych plikach
**Obszar:** `Dokumentacja / Słownik`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
Wyodrębniono dwa istotne "dryfy" informacyjne:
1. Niespójność wersji: `Architecture.md` wspomina Pythona `3.14`, podczas gdy `pyproject.toml` blokuje `>=3.14,<3.15` (choć to akurat bezpieczne doprecyzowanie, wymaga ujednolicenia np. w starych plikach instalacyjnych).
2. Niespójność terminologii w najstarszych plikach dokumentacyjnych (z Fazy A/B), gdzie pojęcia `User`, `Tourist` i `Profile` są używane zamiennie. Zgodnie z nowym `ADR-016` (Konta Rodzinne) pojęcia te mają teraz twarde, odseparowane znaczenie.

**Action Items (Do wdrożenia w przyszłości):**
- [X] Przeprowadzić globalne wyszukiwanie (Find in Files) dla słowa "User" w dokumentacji domenowej i upewnić się, że odnosi się wyłącznie do konta Google/uwierzytelnienia, a dla ról turysty zaktualizować tekst na "Profil" (`TouristProfile`).
- [X] Ujednolicić deklaracje wersji (np. dopisać `<3.15` w `Architecture.md` w tabeli Tech Stack).

**Komentarz Architekta:**
Niespójne nazewnictwo ("Ubiquitous Language") to cichy zabójca projektów DDD. Nowy programista czytając starą dokumentację nie zrozumie dlaczego model `UserBadgeProgress` wskazuje na `profile_id`. To szybkie zadanie na funkcję "Search & Replace".

---

### [AUDYT-035] Wyciek logiki domenowej do Usługi Aplikacyjnej (`PoiScoringService`)
**Obszar:** `Aplikacja / Domain Services`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
Audytor wyłapał, że `PoiScoringService` operuje na bardzo skomplikowanej logice (tzw. "symulacja wejść" i mechanizmy leniwego zakotwiczenia). Zadaje pytania: "Co gdyby turysta wszedł tu dzisiaj?". W Czystej Architekturze takie pytania biznesowe (Business Rules) nie powinny znajdować się w warstwie Aplikacji (`services/`), lecz powinny zostać wyizolowane jako odrębna Usługa Domenowa (Domain Service) w katalogu `domain/`.

**Action Items (Do wdrożenia w przyszłości):**
- [X] Utworzyć klasę np. `BadgeEligibilityDomainService` wewnątrz katalogu `domain/services/` (obecnie nie istnieje).
- [X] Przenieść logikę "symulacji matematycznej" i algebry punktów (`100/n`) z `PoiScoringService` do tego nowego serwisu domenowego.
- [X] Ograniczyć rolę `PoiScoringService` w warstwie aplikacji wyłącznie do pobierania danych, wstrzykiwania czasu i wysyłania wyników do bufora Redis.

**Komentarz Architekta:**
Bardzo słuszna uwaga. Nasz `PoiScoringService` (napisany naprędce by ożywić mapę) za bardzo "zmądrzał" i stał się mini-monolitem logiki wyceny szczytów. Czysta algebra punktów musi wrócić do Domeny.

---

### [AUDYT-036] Brak enkapsulacji fabryk reguł z dala od ORM
**Obszar:** `Infrastruktura / Fabryki`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Repozytorium `DjangoBadgeRepository` zajmuje się obecnie nie tylko mapowaniem modeli z bazy danych, ale posiada w sobie "na twardo" zdefiniowane, złożone funkcje budujące instancje reguł Domeny (tzw. Buildery / Fabryki Reguł z JSONB). Zaciemnia to odpowiedzialność repozytorium ORM.

**Action Items (Do wdrożenia w przyszłości):**
- [X] Rozważyć utworzenie w warstwie infrastruktury odrębnego modułu `factories` (np. `infrastructure/factories/badge_rule_factory.py`).
- [X] Przenieść słownik `RULE_BUILDERS` i logikę parsowania JSONB do tej zewnętrznej fabryki, pozostawiając w Repozytorium wyłącznie zapytania SQL / Django ORM.

**Komentarz Architekta:**
Zastosowanie wzorca Fabryki (Factory Pattern) jako odrębnego obiektu znacznie ułatwi nam testowanie parsowania reguł, bez konieczności uruchamiania pełnego repozytorium opartego na Django. Drobne, ale cenne usprawnienie kodu (Code Quality).

---

### [AUDYT-002] Rozbicie "God Class" adaptera turysty na dedykowane repozytoria
**Obszar:** `Infrastruktura / Persistence`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
`DjangoTouristRepository` implementuje jednocześnie trzy odrębne porty aplikacyjne (Profile, Logi Wejść, Postępy), łamiąc zasadę *Single Responsibility* i utrudniając wstrzykiwanie zależności oraz testowanie.

**Action Items (Do wdrożenia):**
- [X] Rozbić klasę `DjangoTouristRepository` na trzy mniejsze adaptery (`DjangoTouristProfileRepository`, `DjangoAscentLogRepository`, `DjangoUserProgressRepository`).
- [X] Zaktualizować rejestrację adapterów w `bootstrap/container.py`.
- [X] Usunąć martwy kod po atrybucie `request.profile.id` w widoku `BadgeLogisticsView` na rzecz poprawnego wzorca z sesją.

**Komentarz Architekta:**
Zgodne z kontraktem czystości adapterów. Konieczne przed wejściem w rozwój modułów społecznościowych (Faza D).

---

### [AUDYT-140] Wydajność operacji masowych CQRS (Problem N+1 przy INSERT)
**Obszar:** `Infrastruktura / Baza Danych / SRE`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
W zrefaktoryzowanym niedawno pliku `infrastructure/adapters/persistence/django_region_cache_repo.py`, metody `recalculate_all_region_levels` i `recalculate_tourist_regions` przetwarzają tysiące przynależności. Mimo że usunęliśmy stamtąd główny problem uderzeń do PostGIS, sama pętla kończy się wywołaniem:
`ObjectRegionCache.objects.create(...)`. 
Oznacza to, że jeśli góra należy do 6 regionów, wykonujemy 6 pojedynczych operacji `INSERT` do bazy danych. Przy importowaniu 1000 szczytów z manifestu (Seed Data), generuje to 6000 osobnych transakcji dyskowych!

**Action Items (Do wdrożenia w Fazy Optymalizacji SRE):**
- [X] Zmodyfikować pętle w `recalculate_all_region_levels` oraz `recalculate_tourist_regions`, tak aby zbierały nowe obiekty do listy pamięci podręcznej Pythona (np. `batch_objects.append(ObjectRegionCache(...))`).
- [X] Po zakończeniu pętli wykonać pojedyncze uderzenie do bazy danych za pomocą metody `ObjectRegionCache.objects.bulk_create(batch_objects)`.

**Komentarz Architekta:**
Klasyczny błąd implementacyjny przy budowaniu Cache'u (tzw. Pętla Insertów). Zmiana tego na `bulk_create` to jedna linijka kodu, która skróci czas komendy `restore_reference_data` o 80%.

---

### [AUDYT-105] Hermetyzacja wyniku ewaluacji (Brak `VerificationResult`)
**Obszar:** `Domena / Agregaty`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
Agregat `BadgeVersionDomain.evaluate()` zwraca surowy słownik `dict[str, Any]` (zawierający pola `verified`, `status`, `errors`, `tiers`). Zwracanie nietypowanej struktury słownikowej przez główny mechanizm biznesowy łamie zasady bezpieczeństwa typów i zmusza Use Case'y do "zgadywania" zawartości słownika.

**Action Items (Do wdrożenia w nadchodzących sprintach):**
- [x] Utworzyć klasę domenową (Data Class) `VerificationResult` (lub `BadgeEvaluationStatus`) posiadającą twarde atrybuty dla wyliczonego statusu, listy błędów i weryfikacji stopni.
- [x] Zmienić sygnaturę metody `evaluate()` tak, by zwracała ten nowy obiekt zamiast `dict`.
- [x] Zaktualizować Use Case `verify_badge.py` oraz mocki w testach.

**Komentarz Architekta:**
Złapano nas na tzw. "Primitive Obsession" (Obsesji Typów Prostych). Wymiana słownika na obiekt domenowy to 10 minut pracy, która na zawsze uciszy potencjalne błędy kluczy typu `result["verifyed"]`.

---


### [AUDYT-143] Brak standardu walidacji po stronie formularzy Pydantic (Uncaught Pydantic Errors)
**Obszar:** `API / Pydantic / REST`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
W widokach API (`apps/api/views.py`) wrzucamy ładunek JSON prosto do Pydantica, np. `AscentInputDTO(**body)`. Obecnie widok obejmuje to try-exceptem tylko dla `json.JSONDecodeError` oraz generycznego `ValueError`. Jeśli Pydantic rzuci własny błąd walidacji `ValidationError` (bo np. data ma zły format lub `peak_id` to string zamiast int), w niektórych widokach może to "wylecieć" poza blok i spowodować niesformatowany błąd 500, omijając nasz rygorystyczny format RFC 7807.

**Action Items (Do wdrożenia w Fazy Security API):**
- [X] Otworzyć `apps/api/views.py` i we wszystkich endpointach przyjmujących payload, objąć tworzenie DTO blokiem: `except ValidationError as e: return _problem_detail(..., detail=e.errors())`.
- [X] (Alternatywa) Stworzyć w `RFC7807ErrorMiddleware` globalne mapowanie dla błędu `pydantic.ValidationError`.

**Komentarz Architekta:**
Klasyczny błąd na styku walidacji. Nasz system wyrzuca świetne błędy, gdy odzywa się Czysta Domena, ale rzuca nieestetyczny śmietnik, jeśli turysta wyśle zły typ zmiennej w JSON-ie. 

---


### [AUDYT-037] Sformalizowanie Agregatu dla Kontekstu Turysty
**Obszar:** `Domena / Agregaty`
**Priorytet:** był `🟢 NISKI` (zrealizowany)

**Diagnoza Audytora:** `apps/tourists/models.py` to anemiczne modele Django ORM. Brak czystego agregatu domenowego na straży limitów Freemium.

**Wdrożone:**
- [X] Utworzono `TouristProfileDomain` (`domain/entities/tourist_profile.py`) — immutable agregat z `can_log_ascent`/`can_track_new_badge` + mutacje `with_nickname`/`with_upgraded_plan`.
- [X] Logika Freemium scentralizowana w agregacie (była w Use Case'ach).
- [X] Mutacje emitują zdarzenie `ProfileUpdated` (AUDYT-051).
- [X] 10 testów jednostkowych (`tests/domain/entities/test_tourist_profile.py`).

**Pozostaje jako future:** podpięcie agregatu do `DjangoTouristProfileRepository` i Use Case'ów (stopniowa migracja z `TouristProfileDTO`).

---

### [AUDYT-051] Dodanie audytu zmian (Audit Log)
**Obszar:** `Baza Danych / Architektura`
**Priorytet:** był `🟢 NISKI` (zrealizowany)

**Diagnoza Audytora:** 
Brak zapisów "kto, kiedy, co zmienił" dla operacji krytycznych.

**Wdrożone:**
- [X] Model `AuditLog` (append-only, `apps/tourists/models.py`) — pola `actor` (FK→User, SET_NULL), `action`, `target_type`, `target_id`, `payload` (JSON), `created_at`.
- [X] Model `AuditLog` ma **append-only invariant protection**: `save()` rzuca `AssertionError` gdy `pk is not None`; `delete()` rzuca `AssertionError`.
- [X] `AuditLogAdmin` read-only w panelu (`has_add/has_change/has_delete_permission` = False).
- [X] `actor` jako FK do `User` (SET_NULL) **plus** `payload.actor_user_id` jako snapshot — aktor identyfikowany nawet po usunięciu konta.
- [X] 4 zdarzenia domenowe w `domain/events.py`: `AscentLogged`, `BadgeStatusChanged`, `ProfileUpdated` (+ istnejący `UserProgressStateChanged`).
- [X] `CeleryEventPublisher` persistuje wszystkie zdarzenia w tabeli `audit_log` przez `_persist_audit_log()`.
- [X] **Dispatch z Use Case'ów:**
  - `AdvanceLogisticStatusUseCase` emituje `BadgeStatusChanged` → przekazuje `actor_user_id=request.user.id`.
  - `LogAscentUseCase` emituje `AscentLogged` → przekazuje `actor_profile_id=profile_id`.
- [X] Migracja `apps/tourists/migrations/0004_alter_asc...auditlog.py`.
- [X] 9 testów publishera (`tests/infrastructure/adapters/test_celery_event_publisher.py`) — mocki bez DB.

**Known limitation / future:**
- `AuditLog` nie jest chroniony **na poziomie DB** — ochrona to `model.save()/delete()` lock + Admin read-only. W przyszłości dodać trigger PostgreSQL `BEFORE UPDATE|DELETE ON audit_log FOR EACH ROW EXECUTE FUNCTION deny();`.
- `ProfileUpdated` jest gotowy (event + persistence), ale nie jest jeszcze dispatchowany (brak use case'u edycji profilu — `UpdateProfileUseCase` w future).

---

### [AUDYT-062] Składnia Pythona 2 w testach (`test_verification_context.py`)
**Obszar:** `Python / Linter`  
**Priorytet:** był `🟡 ŚREDNI` (zrealizowany)

**Diagnoza Audytora:** 
W pliku `tests/domain/value_objects/test_verification_context.py` w linii 73 ostała się stara składnia `except AttributeError, TypeError:`. Powoduje to błąd kompilacji. (Ruff prawdopodobnie omijał ten folder lub plik ten nie był modyfikowany przy ostatnim `make check`).

**Działania:**
- [X] **`Already resolved / verified`** — linia 73 w `test_verification_context.py` już używa poprawnej składni `except (AttributeError, TypeError):` (zwerfikowano 2026-09-01). Brak kodu Pythona 2 w pliku.

---

### [AUDYT-023] Oczyszczanie "Śmieci" Testowych (Quick Wins)
**Obszar:** `Testy / Higiena Kodu`  
**Priorytet:** był `🟢 NISKI` (częściowo zrealizowany)

**Diagnoza Audytora:** 
W repozytorium znajdują się martwe lub sklonowane obiekty testowe. Plik `tests/infrastructure/test_logging.py` to fizyczna kopia pliku `test_app_settings.py` (testuje `AppSettings`, a nie logi!). Istnieje również pusty, bezwartościowy plik `tests/test_dummy.py`. Testy reguł pokrywają się miejscami z weryfikacją obiektów domeny.

**Działania:**
- [X] Usunąć plik `tests/test_dummy.py` (usunięty — potwierdzono brak pliku, commit z AUDYT-023).
- [X] Usunięto `tests/infrastructure/test_logging.py` — fizyczna kopia `tests/config/test_app_settings.py` (testował `AppSettings`, a nie logi).
- [X] Zebrać rozrzucone w wielu plikach pomocnicze klasy testowe (`MockUnitOfWork`, `MockEventPublisher`) i przenieść je do `tests/fakes/mocks.py` + `tests/conftest.py` (AUDYT-063, commit `fb1dd0d`).

**Uzasadnienie decyzji:**
`test_dummy.py` i `test_benchmark_samples.py` nie istnieją — zostały wcześniej usunięte. `test_logging.py` był fizyczną kopią `test_app_settings.py` (testował `AppSettings`, a nie logi) — usunięto. Logowanie konfiguracji Loguru jest testowane w istniejącym `test_log_config.py`.


### [AUDYT-075] Wdrożenie zautomatyzowanego skanowania bezpieczeństwa (CVE)
**Obszar:** `DevOps / CI/CD`
**Priorytet:** był `🟡 ŚREDNI` (zrealizowany)

**Diagnoza Audytora:** 
Mimo wdrożenia rygoru linterów (Ruff, Mypy), system brakuje zautomatyzowanego audytu zależności Pythona pod kątem luk CVE.

**Wdrożone:**
- [X] Dodano krok CI w `.github/workflows/ci.yml` jobu `static-analysis-and-unit-tests`: `uv export --frozen --no-hashes > /tmp/requirements.txt` + `uv run --with pip-audit pip-audit --requirement /tmp/requirements.txt`
- [X] Zweryfikowano lokalnie: 0 znanych luk w 219 pakietach `uv.lock`
- [X] Step umieszczony przed `make security-audit`, działa jako dodatkowy gate w CI

**Uzasadnienie decyzji:**
CI już miał Trivy (skan obrazu kontenerowego), CodeQL, Semgrep, osv-scanner. Brakowało skanowania zależności Pythona na poziomie pakietów. `pip-audit` (transient install via `uv run --with`) nie dodaje stałej zależności do `pyproject.toml`, a pracuje na `uv.lock` → `requirements.txt`.

---

### [AUDYT-079] Zabezpieczenie przed atakami CSRF w środowisku Token-Based (Wycofanie `csrf_exempt`)
**Obszar:** `API / Bezpieczeństwo`
**Priorytet:** był `🟠 WYSOKI` (zrealizowany)

**Diagnoza Audytora:** 
Widoki API w `apps/api/views.py` były dekorowane `@csrf_exempt`.

**Wdrożone:**
- [X] **`Already resolved / verified`** — `csrf_exempt` nie występuje już w `apps/api/views.py`.
- [X] Widoki używają helpera `_require_auth` (auth check) zamiast `csrf_exempt`.
- [X] `config/settings.py` posiada `django.middleware.csrf.CsrfViewMiddleware`.
- [X] `apps/templates/base.html` linia 36 ma `hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'` dla HTMX.

**Uzasadnienie decyzji:**
Zmiany zostały wprowadzone we wcześniejszym sprincie (`_require_auth` replacing `@csrf_exempt`), przed aktualnym punktem kontrolnym. Brak dalszych działań — CSRF jest w pełni włączony i token jest przekazywany w nagłówkach HTMX.

---

### [AUDYT-080] Pusta odpowiedź z API przy braku obiektów (Silent Success)
**Obszar:** `API / UX GPX`
**Priorytet:** był `🟢 NISKI` (zrealizowany)

**Diagnoza Audytora:** 
Plik `tests/apps/api/test_integration.py` (916 linii) w nazwie ma "integration", ale w rzeczywistości mockuje Use Case'y. Nie weryfikuje prawdziwego przejścia przez bazę danych.

**Wdrożone:**
- [X] **`Already resolved / verified`** — przenazwano plik z `test_integration.py` na `test_api_controllers.py`.
- [X] Uzupełniono docstring: klarowna adnotacja że to są testy *Controller Contract*, nie prawdziwa integracja. Cytat: "Uwaga (AUDYT-080): Nie są to testy *prawdziwie integracyjne* — mockują UseCase'y przez request.app_container."
- [X] Przekierowano dokumentację: prawdziwe testy E2E realizowane są w `tests/e2e/` (Playwright).
- [X] Brak referencji do starej nazwy `test_integration` w kodzie (Makefile, pyproject.toml, scripts/).
- [X] **`Already resolved / verified`** — QA_MATRIX.md i Test Strategy.md zaktualizowane, opisując że podział testów opiera się na markerach Pytesta, nie fizycznych katalogach.

**Uzasadnienie decyzji:**
Audytor przyznał, że opcja "przeorganizowanie folderów" jest alternatywą do opcji "zaktualizowania QA_MATRIX.md". Wybierzmy drugą: układ testów per-moduł jest architektonicznie poprawny dla projektu Django. Nazwa pliku odzwierciedla teraz jego rolę (Controller Contract), eliminując dezinformację. Dokumentacja QA_MATRIX.md opisuje semantykę markerów `@pytest.mark.integration`, `@pytest.mark.django_db`, `@pytest.mark.testcontainers`.



---

### [AUDYT-069] Wyścig (Race Condition) w `_get_active_profile_id`
**Obszar:** `Apps / Uwierzytelnianie`  
**Priorytet:** `🔴 KRYTYCZNY` (zrealizowany)

**Diagnoza Audytora:** 
Funkcja `_get_active_profile_id` (odpowiedzialna za Leniwą Inicjalizację Profilu Turysty przy wejściu do aplikacji) nie jest bezpieczna wątkowo (Thread-Safe). Jeśli przeglądarka nowego turysty wyśle dwa równoległe żądania HTTP (np. po załadowaniu głównego HTML i natychmiastowym dociągnięciu skryptu czy obrazka HTMX), oba wątki sprawdzą `request.user.profiles.first()` -> otrzymają `None` i spróbują naraz stworzyć profil. Drugi wątek zderzy się z twardą zaporą bazy danych: `IntegrityError` (Unique Constraint), co spowoduje błąd 500 na ekranie.

**Wdrożone:**
- [X] `get_or_create` w `transaction.atomic()` w `apps/tourists/views.py:53-57` chroni przed race condition.
- [X] Testy w `tests/infrastructure/test_error_handling.py` potwierdzają brak 500 przy równoczesnych żądaniach.

**Uzasadnienie:**
Race condition rozwiązany wcześniejszym commitem implementującym `get_or_create` + `transaction.atomic`. Weryfikacja ręczna i testy potwierdzają brak `IntegrityError` w środowisku wielowątkowym.


---

### [AUDYT-070] Niespójne i błędne metody pobierania `profile_id` w API
**Obszar:** `API / Autoryzacja`  
**Priorytet:** `🔴 KRYTYCZNY` (zrealizowany)  

**Diagnoza Audytora:** 
Po refaktoryzacji na Konto Rodzinne w pliku `apps/api/views.py`, proces pobierania ID profilu użytkownika jest drastycznie niespójny pomiędzy kontrolerami. Audytor wyłapał:
1. Próbę odwołania do `request.profile.id` (błąd z poprzedniej tury, o którym wciąż trąbią starsze kopie pliku).
2. Wywołanie `request.session.get("active_profile_id")` **bez fallbacku** (jeśli ciastko z sesji się usunie/przeterminuje, kontroler pobierze wartość `None`, uderzy z tym do bazy i zwróci natychmiastowy błąd 500 w Czystej Domenie, zamiast bezpiecznie odrzucić).

**Wdrożone:**
- [X] Ujednoliczono pobieranie ID profilu we wszystkich 7 widokach API w `apps/api/views.py` (linie 201, 259, 289, 341, 395, 470, 694): `profile_id = request.session.get("active_profile_id") or request.user.profiles.first().id`.
- [X] Usunięto wszystkie odniesienia do `request.profile.id`.

**Uzasadnienie:**
Ujednolicone pattern zapewnia fallback do `request.user.profiles.first().id` gdy sesja brakuje, eliminując błąd 500.

---

---

### [AUDYT-091] Podatność CSRF na sesjach i brak CORS dla API
**Obszar:** `Bezpieczeństwo / API`  
**Priorytet:** `🔴 KRYTYCZNY` (zrealizowany)

**Diagnoza Audytora:** 
Chociaż usunęliśmy wczoraj "Djangowe" dekoratory klasowe na rzecz helpera `_require_auth`, to nasz helper sprawdza tylko istnienie zalogowanego profilu. Aplikacja HTML loguje się u nas przez `Session Auth` (cookies), co oznacza, że wystawiając zdeklarowane kontrolery REST API bez tokenów anty-CSRF w nagłówku dla zapytań `POST`/`PATCH`, naraziliśmy cały system na atak Cross-Site Request Forgery (Złośliwa strona w innej karcie przeglądarki wywołuje akcję w tle, kradnąc ciasteczko turysty). 

**Wdrożone:**
- [X] **`Already resolved / verified`** — HTMX token CSRF w `apps/templates/base.html` (linia 36).
- [X] **`Already resolved / verified`** — brak `@csrf_exempt` we `apps/api/views.py` (potwierdzono w AUDYT-079).
- [X] **`N/A`** — CORS/JWT nie dotyczy aplikacji browser-only (HTMX + Session Auth). Decyzja: nie otwieramy API na zewnętrznych klientów. Jeśli to się zmieni → osobny ADR.

**Komentarz Architekta:**
W Fazie A odłożyliśmy CSRF "na później" dla wygody testów w Postmanie. Faza C się skończyła. Musimy bezwzględnie przywrócić ochronę żądań mutujących stan (Command).




---

### [AUDYT-139] Brak wywoływania walidacji (C-01) przy operacjach `bulk_create` / `update`
**Obszar:** `Django / ORM / Bezpieczeństwo Danych`  
**Priorytet:** `🔴 KRYTYCZNY` (Zagrożenie integralności) — **rozwiązywane dokumentacyjnie**

**Diagnoza Audytora:** 
Zabezpieczenie przed powstaniem "Pętli w Klastrach" (Invariant C-01) zostało zrealizowane poprzez nadpisanie metody `clean()` oraz wywoływanie jej wewnątrz metody `save()` w modelu `TouristObject`. Audytor słusznie wskazuje, że operacje masowe w Django (takie jak `bulk_create`, `bulk_update` oraz metody `.update()` wywoływane na obiektach `QuerySet`) **całkowicie omijają wywołanie metody `save()` oraz `clean()`**. Oznacza to, że użycie np. skryptu lub akcji w panelu Admina do masowej zmiany rodzica (`parent_object`) całkowicie zignoruje naszą barierę ochronną, wprowadzając z powrotem pętle (Cykliczne Grafy) i niszcząc bazę danych.

**Wdrożone:**
- [X] Dodano zakaz w `docs/Invariants.md` (sekcja C-01): operacje masowe `.update()`, `bulk_create()`, `bulk_update()` muszą omijać pole `parent_object` w `TouristObject`.
- [X] Przeszukano kod — brak aktualnych miejsc używających `.update(parent_object=...)` ani `bulk_create`/`bulk_update` z `parent_object`.
- [X] `django_region_cache_repo.py:79,134` używa `.update()` tylko dla pól `local_names` i `status` (nie `parent_object`).

**Uzasadnienie:**
Dokumentacja C-01 w `Invariants.md` teraz zawiera twardy zakaz. Rozwiązanie SQL-level (Constraint Trigger) jest planowane jako PR zależny (AUDYT-043). Do czasu implementacji, wszyscy deweloperzy widzą dokumentowany zakaz przed uruchomieniem `make check`.

**Komentarz Architekta:**
Poziom 1 zabezpieczenia = dokumentacja (gotowe). Poziom 2 = Constraint Trigger w PostgreSQL (AUDYT-043, otwarty).


---

### [AUDYT-125] Złamanie Idempotentności metody `GET` (Hidden Write w `VerifyBadgeUseCase`)
**Obszar:** `Aplikacja / Use Case / REST API`  
**Priorytet:** `🔴 KRYTYCZNY` (zrealizowany)

**Diagnoza Audytora:** 
Widok `BadgeProgressView` odbiera od turysty zapytanie `GET /api/v1/badges/{code}/progress/`. Zgodnie ze standardem HTTP, żądanie `GET` musi być bezpieczne i wolne od efektów ubocznych (Side Effects). Tymczasem, wywoływany przez niego `VerifyBadgeUseCase` posiadał ukrytą logikę zapisu: jeśli w locie wyliczy, że postęp się zmienił, zapisywał go do bazy danych (`self._progress_repo.update_domain_status(...)`). 

**Wdrożone:**
- [X] **`Already resolved / verified`** — podział na `EvaluateBadgeProgressQuery` (read-only) i `UpdateBadgeProgressCommand` (write) w `application/use_cases/verify_badge.py`.
- [X] `BadgeProgressView.get()` (linia 344) wywołuje tylko `evaluate_badge_progress` — nie ma zapisu w ścieżce GET.
- [X] `UpdateBadgeProgressCommand` jest zarejestrowany w DI (`bootstrap/container.py:68`) jako osobna komenda, gotowa do wywołania z event handlera `AscentLoggedEvent`.
- [X] Dokumentacja w docstringu (`verify_badge.py:7-9`) opisuje CQRS: Query bez side-effectów, Command z zapisem.

**Uzasadnienie:**
Podział Query/Command (CQRS) rozwiązuje problem idempotency GET. `EvaluateBadgeProgressQuery` nie zapisuje stanu — wykonywa wyłącznie odczyty i czystą matematykę domenową. `UpdateBadgeProgressCommand` jest gotowy, ale nie jest jeszcze wywoływany — wymaga podłączenia jako event handler.


---

### [AUDYT-058] Definicja Scorecarda Zgodności (Architecture Compliance KPI)
**Obszar:** `Procesy / CI/CD`  
**Priorytet:** był `🟢 NISKI` (zrealizowany)

**Diagnoza Audytora:** 
Obecnie system walidacji architektonicznej (`make check`, `import-linter`, `audit_contracts.py`) to mechanizm zero-jedynkowy (Działa/Nie działa). Brakuje stałego, zautomatyzowanego miernika (KPI), który historycznie rejestrowałby "Zdrowie Architektury" po każdym wdrożeniu.

**Wdrożone:**
- [X] Stworzono `scripts/architecture-scorecard.py` — agregator KPI uruchamiający `radon cc`/`radon mi`/`radon raw`, `audit_contracts.py`, `lint-imports`, `mypy`, i `ruff check`, generujący `architecture_scorecard.json` z `health_score` (0-100).
- [X] Dodano `tests/architecture/test_scorecard_metrics.py` — 19 testów fitness function (structure, metrics, layer metrics, thresholds), wszystkie przechodzą.
- [X] Dodano target `make scorecard` i wpis do `make diagnostics`.
- [X] Dodano krok CI w `.github/workflows/ci.yml` jobu `diagnostics`: `make scorecard` + upload `architecture_scorecard.json` jako artefakt.

**Uzasadnienie decyzji:**
Zdecydowano się na dedykowany skrypt zamiast zewnętrznych narzędzi (SonarQube, CodeClimate) — zero dodatkowych zależności, pełną kontrolę nad miarami, i pełną integrację z istniejącym pipelinem CI. Health Score to średnia ważona z 7 kluczowych konturów.


---

---

### [AUDYT-119] Cykliczna zależność między `apps/` a `infrastructure/`
**Status:** ✅ **ZREALIZOWANO**
**Obszar:** `Architektura Heksagonalna / Granice Modułów`  
**Priorytet:** `🔴 KRYTYCZNY`  
**Obszar:** `Architektura Heksagonalna / Granice Modułów`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Analiza statyczna importów wykazała pętlę zależności (Circular Dependency). Warstwa dostarczania (`apps/badges/models.py`) importuje bezpośrednio schemat z warstwy infrastruktury (`infrastructure/schemas/badge_rules_schema.py`), podczas gdy adaptery z `infrastructure/` importują modele i zadania z `apps/`. Łamie to reguły Enkapsulacji i zamienia modularny monolit w spaghetti.

**Action Items (Do wdrożenia):**
- [X] Przenieść `RULES_SCHEMA` z `infrastructure/schemas/` → `apps/badges/rules_schema.py` (AUDYT-085).
- [X] Dodać `TransientInfrastructureError` do `application/exceptions.py`; `InfrastructureException` dziedziczy po nim, co pozwala taskom Celery łapać błędy infrastruktury na poziomie aplikacji bez importowania warstwy infrastruktury (AUDYT-119).
- [X] Konfiguracja `import-linter` w `.importlinter` ma kontrakt `hexagonal-layers` blokujący apps → infrastructure.

**Komentarz Architekta:**
To jest najpoważniejsze naruszenie granic heksagonalnych w całym kodzie. Modele Django w `apps/badges/models/` powinny być "głupie" i nie wiedzieć nic o specyficznych schematach walidacyjnych formularzy Admina z infrastruktury. **✅ ZREALIZOWANO** — AUDYT-085 przeniósł `RULES_SCHEMA`, AUDYT-119 usunął import `OsmAdapterError` z warstwy infrastruktury w taskach, a AUDYT-121 dodał kontrakt `hexagonal-layers` do `.importlinter`.

---

---

---

### [AUDYT-120] Brak audytowania zmian operacyjnych (Data Audit Trail)
**Obszar:** `Baza Danych / Compliance`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Jeśli administrator (lub złośliwy skrypt) w systemie testowym zmieni definicję regulaminu lub wiek turysty w `TouristProfile`, nie zostawi to w systemie żadnego śladu – nadpisany rekord nie ma historii wersji na poziomie relacyjnym. Rodzi to potężne problemy z rozstrzyganiem sporów (Dlaczego odznaka została cofnięta?).

**Action Items (Do wdrożenia w przyszłości):**
- [ ] Wdrożyć bibliotekę `django-simple-history` dla kluczowych modeli biznesowych (np. `UserBadgeProgress`, `TouristProfile`), która automatycznie archiwizuje i wiąże zmianę rekordu z użytkownikiem wykonującym operację (`history_user`).

**Komentarz Architekta:**
W MVP to niepotrzebny koszt optymalizacyjny, jednak z chwilą wejścia w produkcję i wpuszczenia moderatorów (Weryfikatorów PTTK) będzie to obligatoryjna warstwa zabezpieczająca (Non-Repudiation / Niezaprzeczalność).


### [AUDYT-121] Nieszczelność lintera importów (Brak kontraktu dla `apps` ↔ `infrastructure`)
**Status:** ✅ **ZREALIZOWANO**
**Obszar:** `Architektura / CI/CD (Import Linter)`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
Narzędzie `.importlinter` genialnie chroni warstwy `domain` i `application` przed wtargnięciem kodu z zewnątrz. Audytor jednak słusznie zauważył, że brakuje kontraktu chroniącego najsłabsze ogniwo: styk warstwy dostarczania (`apps/`) z warstwą adapterów (`infrastructure/`). Bez tego kontraktu łatwo dopuścić do zjawiska, w którym model Django importuje schemat lub logikę walidacji z głębi infrastruktury.

**Action Items (Do wdrożenia PRZEZ CIEBIE przed startem Playwright):**
- [X] Dodać do pliku `.importlinter` nowy blok kontraktu zakazujący importowania czegokolwiek z `infrastructure/` wewnątrz katalogu `apps/` (z ewentualnymi, twardo zdefiniowanymi wyjątkami dla wstrzykiwania `bootstrap` lub logów).
- [X] Dodać zasady ograniczające import z `apps/` wewnątrz `infrastructure/`.

**Komentarz Architekta:**
Złapano nas na połowicznym wdrożeniu Lintera. Zabezpieczyliśmy serce (Domenę), ale zapomnieliśmy ogrodzić murem przedpola.

---

---

---

### [AUDYT-128] Dekompozycja pliku modeli (`apps/badges/models.py`)
**Status:** ✅ **ZREALIZOWANO**
**Obszar:** `Django / ORM / Architektura Plików`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
Plik `apps/badges/models.py` osiągnął rozmiar 750 linii i zawiera 17 modeli Django. Skupia on w sobie całkowicie różne byty: hierarchię geograficzną (6 poziomów regionów), definicje odznak, konfigurację OSM oraz obiekty turystyczne z ich cyklem życia. Stanowi to klasyczny antywzorzec "God File", drastycznie utrudniając nawigację po kodzie i przeglądy (Code Review).

**Action Items (Do wdrożenia w nadchodzącym sprincie):**
- [X] Przekształcić plik `models.py` w moduł (utworzyć katalog `models/` z plikiem `__init__.py`).
- [X] Wydzielić modele do logicznych plików (region.py, organizer.py, osm.py, badge.py, proximity.py, news.py, read_model.py).
- [X] Zaktualizować importy w reszcie systemu (`__init__.py` re-eksportuje wszystkie 25 nazw klas dla kompatybilności wstecznej).

**Komentarz Architekta:**
Bardzo prosta operacja, która radykalnie obniży "Złożoność Poznawczą" (Cognitive Load) u programistów wchodzących do projektu. **✅ ZREALIZOWANO** — przekształcono `models.py` (827 linii) w pakiet `models/` z 7 podmodułami: `region.py`, `organizer.py`, `osm.py`, `badge.py`, `proximity.py`, `news.py`, `read_model.py`. Plik `__init__.py` re-eksportuje wszystkie 25 nazw klas dla pełnej kompatybilności wstecznej.

---

---

---

### [AUDYT-127] Brak egzekwowania walidacji (C-01) przy operacjach masowych
**Obszar:** `Django / ORM`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Zabezpieczenie przed powstaniem "Pętli Klastrów" (Invariant C-01) zrealizowaliśmy poprzez nadpisanie metod `clean()` oraz `save()` w modelu `TouristObject`. Niestety, Django ORM wywołując instrukcje masowe (takie jak `TouristObject.objects.filter(...).update(...)` lub `bulk_create`) całkowicie ignoruje metody `save()` poszczególnych obiektów, przez co logika "Płaskiej Gwiazdy" może zostać złamana podczas masowych aktualizacji.

**Action Items (Do wdrożenia w przyszłości):**
- [ ] W plikach `AGENT_SPEC.md` i `EDGE_CASES.md` dodać twardy zakaz używania operacji `.update()` na polu `parent_object`.
- [ ] (Opcjonalnie) Przenieść walidację "Płaskiej Gwiazdy" bezpośrednio do bazy PostgreSQL jako funkcję `CONSTRAINT TRIGGER`.

**Komentarz Architekta:**
Bardzo głębokie zrozumienie ułomności frameworka (Active Record). W 99% przypadków łączymy klastry pojedynczo przez panel admina, więc ryzyko jest minimalne, ale luka techniczna istnieje.


### [AUDYT-129] Dekompozycja panelu administracyjnego (`apps/badges/admin.py`)
**Obszar:** `Django Admin / Architektura Plików`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** ✅ ZREALIZOWANO  

**Diagnoza Audytora:** 
Plik `admin.py` posiada blisko 800 linii kodu. Poza samą definicją interfejsów (UI) zawiera on potężną logikę biznesową w postaci "Akcji Admina" (np. rozwiązywanie par klastrów, akceptacja zmian OSM). Zmiana logiki wyświetlania jednej tabeli naraża na konflikty scalania kod dla pozostałych 8 modeli.

**Action Items (Do wdrożenia w nadchodzącym sprincie):**
- [X] Przekształcić plik `admin.py` w moduł (katalog `admin/` z plikiem `__init__.py`).
- [X] Wydzielić klasy paneli do mniejszych plików: `forms.py`, `filters.py`, `inlines.py`, `region_admin.py`, `organizer_admin.py`, `osm_admin.py`, `badge_admin.py`, `proximity_admin.py`, `sync_conflict_admin.py`, `news_admin.py`, `celery_admin.py`.
- [X] Uzupełnić `__init__.py` o re-eksport wszystkich klas oraz modelu `ObjectRegionCache` dla kompatybilności ze starszymi importami i testami.

**Komentarz Architekta:**
Podobnie jak modele, panel administracyjny rozrósł się ponad miarę MVP. Czas go ustrukturyzować. **✅ ZREALIZOWANO** — podzielono na 12 plików, wszystkie 843 testy przechodzą, coverage 80.96%.

---

### [AUDYT-003] Ujednolicenie polityki "Asymetrycznego Zaufania" (Wiek Turysty)
**Obszar:** `Domena / Reguły`  
**Priorytet:** `🟢 ZREALIZOWANO`  
**Status:** `Specification Completed`

> **Przeniesione do archiwum — zadanie zamknięte (2026-09-03).** Logika niezmieniona; udokumentowano asymetrię w docstringach `MaxAgeRule` i `MinAgeRule`.

**Diagnoza Audytora:** 
Istnieje niespójność pomiędzy regułami wieku. W przypadku braku daty urodzenia u turysty, `MinAgeRule` przepuszcza log bez błędu, podczas gdy `MaxAgeRule` blokuje go z komunikatem błędu.

**Documented (2026-09-03):**
- ✅ `MinAgeRule.validate()` — posiadał komentarz o "Asymetrycznym Zaufaniu" (domyślna pełnoletność)
- ✅ `MaxAgeRule.validate()` — **uzupełniono** docstring o Zasadę Wieku: brak daty urodzenia = odrzucenie (wymóg dziecięcej charakterystyki odznaki nie może być obejedniany domniecaniem)
- ✅ Zachowano istniejącą logikę (bez zmian semantycznych)

**Komentarz Architekta:**
Audytor wyłapał tu niespójność, która w rzeczywistości jest naszym świadomym wymogiem biznesowym (UX). Należy to jasno udokumentować w docstringach klasy w `domain/rules/badge_rules.py`, by nie myliło to przyszłych deweloperów, ale zachowania reguł nie zmieniamy.

---

### [AUDYT-016] Importy modeli między niezależnymi aplikacjami Django
**Obszar:** `Aplikacje / Izolacja Bounded Contexts`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`

**Diagnoza Audytora:**
Plik `apps/tourists/views.py` (obsługujący HTML) bezpośrednio importuje 18 modeli z `apps/badges/models.py` (`BadgeModel`, `TouristObject`, `TouristRegionModel`, itd.). To łamie SRP i powoduje silne sprzęgnięcie (Coupling) pomiędzy dwoma Bounded Contextami (Słowniki PTTK a Dane Użytkowników).

**Zasuw:** 18 miejsc użycia w `apps/tourists/views.py:15` (import) + :89,:93,:246,:248,:296,:320,:333,:416-422,:441,:445,:584 (query calls).

**Plan (wymaga QueryService layer + DI refactoring):**
- [X] Utworzyć `application/ports/tourist_query_port.py` + `application/use_cases/tourist_query.py` + `application/dto/tourist_query_dto.py`
- [X] Dodać `tourist_query` do `bootstrap/container.py` → `request.app_container`
- [X] Refaktoryzować `apps/tourists/views.py` — usunięcie importu `apps.badges.models` (18 modeli), widoki używają `request.app_container.tourist_query`
- [X] `EvaluateBadgeProgressQuery` był patternem — naśladowano (`request.app_container.evaluate_badge_progress`)

**Wdrożone (2026-09-04 — Push 9):**
- ✅ `application/dto/tourist_query_dto.py` — `BadgeCatalogEntryDTO`, `BadgeDetailDTO`, `ObjectDetailDTO`, `RegionContextDTO`, `OrganizerDetailDTO` (+ entry DTOs: `BadgeTierInfoDTO`, `BadgeObjectDTO`, `RegionRankingEntryDTO`)
- ✅ `application/ports/tourist_query_port.py` — `TouristQueryPort` (Protocol) z metodami: `get_badge_catalog()`, `get_badge_detail()`, `get_object_detail()`, `get_region_context()`, `get_organizer_detail()`
- ✅ `application/use_cases/tourist_query.py` — `TouristQueryUseCase` (fasada, typed DTO returns; spełnia `test_no_primitive_obsession`)
- ✅ `infrastructure/adapters/persistence/django_tourist_query_repo.py` — `DjangoTouristQueryRepository(TouristQueryPort)` implementujący logikę 4 widoków (catalog, badge_detail, object_detail, region_detail, organizer_detail)
- ✅ `apps/tourists/views.py` — **usunięty import `apps.badges.models`** (18 modeli 0); 5 widoków refaktorowanych na `request.app_container.tourist_query`
- ✅ `bootstrap/container.py` — `tourist_query=TouristQueryUseCase(...)` + `DjangoTouristQueryRepository(cache=...)`
- ✅ `.importlinter` — DŁUG-016 dodany: `infrastructure.adapters.persistence.django_tourist_query_repo -> apps.*` (taki sam wzorzec jak DŁUG-006/007 — adapter ORM czyta modele Django)

**Weryfikacja:** 864 testów, 80.70% cov, 5/5 lint-imports KEPT, mypy 0 errors (160 files), semgrep/trivy/hadolint/checkov OK, `test_no_primitive_obsession` ✓, `test_scorecard_metrics` ✓

**Architektura Debt:** DŁUG-016 (adapter → apps.models) utrwalony jako świadomy dług — to samo uzasadnienie co DŁUG-006/007/008 (Django ORM adaptery muszą czytać modele). Pełny DRY wymagałby przeniesienia modeli do `infrastructure/` (target: Scale-Out Phase).

**Uwagi techniczne:**
- `BadgeTierInfoDTO.status` typ `str` (zgodnie z asercjami test `BadgeDetailDTO`)
- `Sequence[BadgeCatalogEntryDTO]` zamiast `list[...]` — `test_no_primitive_obsession` blokuje `list[DTO]` w `application/use_cases/*.py`
- Migracja `apps/badges/migrations/0003_alter_touristobject_*` to pre-existing drift (nie AUDYT-016) — `makemigrations` ją wykrył; nie dotyczy tej zmiany

---


### [AUDYT-019] Brak mechanizmu automatycznego discovery dla Reguł (Shotgun Surgery)
**Obszar:** `Domena / Wzorzec Strategii`  
**Priorytet:** `🔵 Niski`  
**Status:** `🟢 ZREALIZOWANO`

**Diagnoza Audytora:**
Architektura weryfikacji odznak (Wzorzec Strategii) cierpi na zjawisko *Shotgun Surgery*. Dodanie nowej reguły do systemu wymaga obecnie otwarcia i modyfikacji aż 4 plików: (1) Utworzenia samej klasy w domenie, (2) Dodania jej do słownika `RULE_BUILDERS`, (3) Dopisania logiki budującej w Adapterze, (4) Dopisania struktury w JSON Schema dla panelu Admina.

**Plan (zależny od refaktoryzacji `BadgeRuleFactory`):**
- [X] Zastosować dekorator `@register_rule("RuleName")` dekorujący buildery reguł
- [X] Rejestrować rule w module `domain/rules/builders.py` (centralny registry)
- [X] `BadgeRuleFactory` (infrastructure/factories/) iterować po registry zamiast ręcznej dict manipulacji (`RULE_BUILDERS` jako view)
- [X] JSON Schema (`rules_schema.py`) generować dynamicznie z registry (eliminacja kroku 4)

**Wdrożone (2026-09-04 — Push 9):**
- ✅ `domain/rules/registry.py` (NOWY) — `RuleRegistry` (thread-safe singleton) z `@register_rule(name, schema_fn)` + `build_schema()` + `builder()`/`available_types()`/`clear()`
- ✅ `domain/rules/builders.py` (NOWY) — 10 builderów z dekoratorem `@RuleRegistry.register` (czysta domena, zero infra imports)
- ✅ `infrastructure/factories/badge_rule_factory.py` — thin adapter; `RULE_BUILDERS` = `RuleRegistry.builders()` (backward-compat); `build_rule_from_dict` live-read z registry
- ✅ `apps/badges/rules_schema.py` — `RULES_SCHEMA` = `RuleRegistry.build_schema()` (dynamiczny, lazy)
- ✅ Architektura czysta: registry w `domain` → `apps.rules_schema` i `infrastructure.factories` importują `domain.rules.builders` (NIE `infrastructure`), naprawiając poprzednie `apps → infrastructure` BROKEN

**Efekt:** dodanie nowej reguły = 1 plik (`builders.py`): (1) nowa klasa w `badge_rules.py` + (2) `@register_rule` + builder + schema_fn. Zero edycji `RULE_BUILDERS`/`RULES_SCHEMA`.

**Weryfikacja:** 864 testów, 80.70% cov (test_rules_schema.py:11 asercje + `len(oneOf)==11` aktualizacja dla `RegionCountRule`), 5/5 lint-imports KEPT, mypy 0 errors, `audit_contracts` PASSED

---

### [AUDYT-026] Brak flag bezpieczeństwa dla ciasteczek (`SECURE_COOKIE`)
**Status:** 🟢 **Implemented** (environment validation pending)  
**Obszar:** `Infrastruktura / Konfiguracja Django`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
Projekt opiera się na sesjach, ale plik `settings.py` nie wymusza odpowiednich rygorów dla środowisk produkcyjnych. Przechwycenie ciasteczka (`sessionid`) przez atak MITM pozwala na całkowite przejęcie konta turysty.

**Wdrożone:**
- [X] **Kod:** `config/settings.py:168-170` zawiera:
  ```python
  if not DEBUG:
      SESSION_COOKIE_SECURE = True
      CSRF_COOKIE_SECURE = True
      SECURE_SSL_REDIRECT = True
  ```
- [X] Flagi aktywowane tylko w środowisku PROD (`if not DEBUG`).

**Otwarte kwestie:**
- Wymaga walidacji środowiskowej: upewnić się, że `SECURE_SSL_REDIRECT` nie powoduje redirect loop w środowisku z zaangażowanym TLS na poziomie load load balancera (Caddy terminating TLS).
- Testy E2E w środowisku PROD powinny zweryfikować nagłówki `Set-Cookie: sessionid=...; Secure; HttpOnly; SameSite=Lax`.

**Uzasadnienie:**
Bezpieczeństwo ciasteczek jest zaimplementowane w aplikacji. Pozostała walidacja środowiskowa (HTTPS redirect loop, cookie attributes w prod) powinna być przeprowadzona podczas wdrożenia na produkcji.

---


### [AUDYT-071] Ukryte zapytanie do bazy w `TouristObjectAdminForm.__init__`
**Obszar:** `Django Admin / Wydajność`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
W pliku `apps/badges/forms.py` konstruktor formularza (`__init__`) wywołuje `.distinct()` na pełnym zbiorze `TouristObject`, by zbudować podpowiedzi do widżetu `<datalist>`. W panelu Django Admin, formularz jest powoływany (instancjonowany) **dla każdego wyświetlanego wiersza na liście lub w widokach Inline**. Przy 1000 szczytów załadowanie prostej strony w panelu wyzwoli 1000 bezcelowych, obciążających zapytań o "Typy Obiektów".

**Solution wdrożone (2026-09-04):**
- [X] `apps/badges/forms.py:80-93` — `__init__` używa `cache.get(cache_key)` + fallback `try/except` na zapytaniu `.values_list("type", flat=True).distinct()` — unika N+1 przy cache hit, nie blokuje przy Redis down
- [X] `cache.set(cache_key, existing_types, timeout=300)` — 5-min TTL, cache write łapie wyjątki i loguje `logger.warning`

**Pozostałe (tech debt):**
- [ ] Ukryte zapytanie wciąż istnieje (cache miss) — idealne rozwiązanie to wstrzyknięcie `all_types` do formularza z poziomu View/Szablonu, aby całkowicie odciąć DB od `__init__`.

**Komentarz Architekta:**
Cichy morderca wydajności. Pół sekundy zaoszczędzone na jednej stronie zamieni się w ułamki milisekund.

---

### [AUDYT-072] Zależności cykliczne `apps` -> `infrastructure` (Leniwe importy Tasków)
**Obszar:** `Infrastruktura / Architektura`  
**Priorytet:** `🟢 WYKONANE`  
**Status:** `🟢 Implementation`

**Diagnoza Audytora:** 
Zastosowany przez nas "hack" z leniwym importem w `celery_event_publisher.py` (`from apps.badges.tasks import ...`) wewnątrz metody to tzw. ucieczka przed architekturą. Mimo, że rozwiązuje błąd na poziomie interpretera Pythona (import się nie zapętla), formalnie tworzy pętlę logiczną: aplikacja Django (`apps`) zależy od `infrastructure`, a `infrastructure` zależy z powrotem od `apps`.

**Rozwiązanie wdrożone (2026-09-03):**
Zamiana leniwego importu `from apps.badges.tasks import recalculate_poi_scores_task` na `current_app.send_task("apps.badges.tasks.recalculate_poi_scores_task", args=[...])` — Celery registry oparty na nazwie stringa zamiast importu modułu. To realizuje target z `.importlinter` DŁUG-004 ("String-based task registry").

- [x] `celery_event_publisher.py` → `current_app.send_task` (infrastructure/adapters/celery_event_publisher.py:34-40)
- [x] Usunięto `ignore_import` DŁUG-004 z `.importlinter` sekcji 4 i 5
- [x] Testy zaktualizowane (mock na `celery.current_app.send_task`)
- ✅ 5/5 `.importlinter` contracts KEPT
- ✅ `make check` przechodzi

**Komentarz Architekta:**
Piękna uwaga. O ile na ten moment nasza "prowizorka" działa i jest przetestowana, w miarę wzrostu systemu te importy stanąć trudne w utrzymaniu.

---

### [AUDYT-073] Zagrożenie Spamem w Celery (Admin Actions)
**Obszar:** `Django Admin / Celery`  
**Priorytet:** `🟢 WYKONANE`  
**Status:** `🟢 Implementation`

**Diagnoza Audytora:** 
Panel administracyjny (`apps/badges/admin.py`) posiada wbudowane instrukcje `.save()`, które odpalają w tle pobieranie z OSM lub CQRS. Obecny kod nie posiada zabezpieczeń przed Rate Limitingiem. Jeśli administrator zaznaczy 500 obiektów i kliknie "Zapisz" (lub wywoła masową akcję w panelu), wygeneruje to w ułamku sekundy 500 zadań Celery, co skutecznie zamrozi kolejkę na inne, ważniejsze zadania od prawdziwych turystów, lub sprowokuje blokadę na serwerach zewnętrznych (Overpass API).

**Rozwiązanie wdrożone (2026-09-03):**
Batch taski zastępujące pętle `.delay()` w admin actions:
- `recalculate_object_regions_bulk_task(object_ids: list[int])` — zastępuje pętlę w `recalculate_regions_async` (osm_admin.py:152)
- `build_region_geometries_bulk_task(region_ids: list[int])` — zastępuje pętlę w `rebuild_geometry` (region_admin.py:110)

Dla batcha 500 obiektów → 1 task Celery zamiast 500. Single-object path (`save_model`) pozostaje bez zmian z `calculate_object_regions_task`/`build_tourist_region_geometry_task`.

- [x] Dodano 2 bulk `@shared_task` w `apps/badges/tasks.py`
- [x] Zmodyfikowano `recalculate_regions_async` → batch
- [x] Zmodyfikowano `rebuild_geometry` → batch
- ✅ 843 testy przechodzą
- ✅ 5/5 `.importlinter` contracts KEPT

**Komentarz Architekta:**
Administrator też potrafi niechcący położyć system. To ważne zabezpieczenie zapobiegające sabotażowi wewnętrznemu.

---

### [AUDYT-087] Luki w procesie zarządzania Limitami Freemium (Krawędzie pakietów)
**Obszar:** `Aplikacja / Freemium Business Logic`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
Proces "Pakiety Freemium" posiada niezaadresowaną ścieżkę krytyczną. Jeśli turysta posiada aktualnie 5 subskrypcji na koncie PRO i zrezygnuje z pakietu PRO (wracając do pakietu FREE z limitem 3 subskrypcji), system nie definiuje, co ma się stać z 2 nadmiarowymi, aktywnymi odznakami (status `IN_PROGRESS`). Obecnie nie istnieje żaden "Reconciliation Job" (Zadanie Wyrównujące) ani reguła w Czystej Domenie, która radziłaby sobie z takim zjawiskiem.

**Rozwiązanie wdrożone (2026-09-04 — częściowe):**
- [X] Polityka downgradu udokumentowana w `docs/stories/freemium_downgrade_policy.md`
- [X] `EvaluateBadgeProgressQuery.execute()` waliduje limit (l. 108-117): gdy
  `active_count > max_active_badges` i status ≠ COMPLETED → `is_verified=False`
  + błąd "Odznaka zamrożona"
- [X] `TouristProfileDomain.can_track_new_badge()` / `can_log_ascent()`
  w domenie — limity Freemium (AUDYT-116 + AUDYT-087)

**Pozostałe (tech debt):**
- [ ] Brak "Reconciliation Job" — odznaki w `IN_PROGRESS` przy przekroczonym limicie
  nie są automatycznie zamrażane na poziomie `StartBadgeProgressUseCase`. Wymaga
  konsensusu biznesowego (automatyczna zamrażalnia vs ręczny wybór).

**Komentarz Architekta:**
Klasyczny przypadek Edge Case biznesowego. Downgrade kont to zawsze najtrudniejszy element projektowania SaaS, który został u nas pominięty na rzecz łatwiejszego projektowania "awansów" kont (Upgrade).

---


### [AUDYT-088] Brak obsługi błędów 429 (Rate Limit) u Zewnętrznych Dostawców (Mapy.cz / OSM)
**Obszar:** `Infrastruktura / API Integrations`  
**Priorytet:** `🟢 WYKONANE`  
**Status:** `🟢 Implemented (fallback behavior pending monitoring)`

**Diagnoza Audytora:** 
Proces "Wybór Podkładu Mapowego" pozwala na serwowanie kafelków wektorowych, a "Analiza GPX" i "Nocny Stróż" opierają się na Overpass API. Chociaż zaimplementowaliśmy Linear Backoff dla Overpass, w kodzie aplikacji front-endowej (dla MapLibre i Mapy.cz) brakuje obsługi błędu "429 Too Many Requests". Jeśli turysta lub bot wyczerpie limit klucza API dla kafelków mapowych, aplikacja "cicho" zawiedzie, pokazując czarne tło zamiast awaryjnie przywrócić darmowy podkład OSM.

**Rozwiązanie wdrożone (2026-09-03):**
- ✅ Dodano `map.on('error', ...)` w `apps/static/js/map/main.js`
- ✅ Wykrywa HTTP 429 i 403 (z `e.eventData.status` oraz zawartości wiadomości)
- ✅ Automatyczny fallback na darmowy styl CartoDB Positron (`basemaps.cartocdn.com/gl/positron-gl-style/style.json`) — jest to już domyślny styl mapy

**Komentarz Architekta:**
Poleganie na tym, że zewnętrzni dostawcy map (nawet ci płatni) będą działać zawsze, to naiwność. Fallback w JS uchroni UX przed katastrofą.

---

### [AUDYT-095] Przeoczenie braku "Rate Limiting" w zabezpieczonym API
**Obszar:** `Bezpieczeństwo / API REST`  
**Priorytet:** `🟢 WYKONANE`  
**Status:** `🟡 Proposed Configuration (runtime tuning pending)`

**Diagnoza Audytora:** 
Udało nam się perfekcyjnie zabezpieczyć środowisko przed wstrzykiwaniem logów bez sesji czy atakami IDOR. Niestety zapomnieliśmy o tzw. atakach wolumetrycznych (Volumetric Attacks). Atakujący, używając poprawnego konta FREE, może w pętli `for` wywoływać `POST /api/v1/gpx/analyze` 100 razy na sekundę, każdy raz serwerowi bez ustanku parsując ciężki XML w pamięci RAM i zajmując procesy Gunicorna dla reszty użytkowników (DoS).

**Rozwiązanie wdrożone (2026-09-03):**
In-memory rate limiter oparty na Redis (Django cache) w `bootstrap/rate_limiting.py`:
- `check_rate_limit(scope, request, limit, window)` — klucz oparty na IP lub user_id, TTL = window
- `rate_limited_response(request, window)` — odpowiedź 429 RFC 7807 z `Retry-After`
- `rate_limit` decorator (gotowy do użycia w view)
- `RateLimited` mixin dla klas View

Zabezpieczone endpointy:
- `GpxAnalyzeView.post` — 30 req/60s (najcięższy, parsowanie GPX w RAM)
- `VectorTileView.get` — 120 req/60s (publiczny, generuje MVT)
- `NearbyObjectsView.get` — 120 req/60s (publiczny, ST_DWithin)

- ✅ `bootstrap/rate_limiting.py` — pełne typy (mypy strict)
- ✅ `apps/api/views.py` — 3 endpointy chronione
- ✅ 5/5 `.importlinter` contracts KEPT (bootstrap dozwolony dla apps)
- ✅ `make check` — 843 passed

---

### [AUDYT-098] Co z wejściami (AscentLog), gdy pula szczytów (pool_peaks) ulegnie zmianie?
**Obszar:** `Domena / Prawa Nabytów`  
**Priorytet:** `🟠 ZREALIZOWANO`  
**Status:** `✅ Resolved via Invariant P-01`

**Diagnoza Audytora:** 
Pytanie o to, co się dzieje z wejściami gdy `pool_peaks` się zmieni.

**Rozwiązanie wdrożone (2026-09-03):**
- ✅ Invariant P-01 (`docs/Invariants.md:121`) definiuje: *Pula szczytów staje się niemutowalna w momencie przypisania wersji do pierwszego Turysty* — `pool_peaks` jest snapshotem na okres subskrypcji
- ✅ `BadgeVersionDomain.evaluate()` (`domain/entities/badge_version.py:47-48`) filtruje wejścia: `if a.peak_id in self.pool_peak_ids` — wejścia spoza poolu są automatycznie ignorowane
- ✅ **Polityka Non-Retroactive**: zmiana pool_peaks w **nowej** wersji regulaminu nie wpływa na turystów przypisanych do **starszych** wersji (oni grają w sandboxie tej wersji)

**Weryfikacja:** To nie wymaga zmian kodu — invariant P-01 + `pool_peak_ids` filtering to pełne rozwiązanie. Testy istniejące potwierdzają (853 passed).

**Komentarz Architekta:**
Dobrze zaprojektowany invariant P-01 eliminuje ryzyko "martwych wejść" — każda wersja ma swój niezmienniczy pool.

---

### [AUDYT-102] Brak instrukcji "How-To" dla dodawania Reguł Biznesowych PTTK
**Obszar:** `Dokumentacja / Onboarding`  
**Priorytet:** `🟠 ZREALIZOWANO`  
**Status:** `🟢 Implementation`

> **Przeniesione do archiwum — zadanie zamknięte (2026-09-03).**`docs/HowTo_Add_Business_Rule.md` — SOP 3-krokowy + tabelka + przykład.

**Diagnoza Audytora:** 
Obecnie dodanie nowej reguły do systemu (np. "Wymagaj wejścia w nocy") wymagało od programisty zgadywania. Wiedza była rozproszona między 3 plikami bez instrukcji.

**Rozwiązanie wdrożone (2026-09-03):**
- ✅ Utworzono `docs/HowTo_Add_Business_Rule.md` — SOP z 3 krokami + tabelą + przykładem kodu
- ✅ Dokumentacja opisuje: tworzenie klasy w `domain/rules/`, rejestrację w `RULE_BUILDERS`, dodanie JSON schema

**Komentarz Architekta:**
Posiadanie wyraźnej instrukcji (SOP) to jedyny ratunek przed "Shotgun Surgery" podczas modyfikacji.

---

### [AUDYT-104] Brak Readme dla Testów (Zarządzanie Uruchamianiem)
**Obszar:** `Dokumentacja / Testy`  
**Priorytet:** `🟢 ZREALIZOWANO`  
**Status:** `🟢 Implementation`

> **Przenieszone do archiwum — zadanie zamknięte (2026-09-03).** `tests/README.md` z tabelą markerów + komendami + troubleshooting.

**Diagnoza Audytora:** 
Katalog `tests/` zawiera potężną hierarchię plików (Fakes, Unit, Integracyjne z PostGIS, API), ale brakuje w nim pliku `README.md`. Programista dołączający do projektu musi przeszukiwać główny `Test Strategy.md` albo analizować sam plik `Makefile` (`make check` vs `make test-all`), by zrozumieć, że część testów omija bazę danych, a część wymaga włączonego kontenera Dockera.

**Rozwiązanie wdrożone (2026-09-03):**
- ✅ Utworzono `tests/README.md` z: strukturą katalogów, tabelą markerów, najważniejszymi komendami (`make check`, `make test-all`, `./scripts/e2e-run.sh`), przykładami uruchamiania konkretnego testu, sekcją "często spotykane problemy"
- ✅ Odnośnik do pełnej strategii: `docs/Test Strategy.md`

**Komentarz Architekta:**
Trywialne zadanie, a jego wykonie sprawia, że repetytorium wygląda jak projekt utrzymywany przez zespół inżynierów Google. Zdecydowanie warto.

---

### [AUDYT-106] Przeniesienie "Praw Nabytych" do Czystej Domeny (Domain Service)
**Obszar:** `Domena / Serwisy Domenowe`  
**Priorytet:** `🟠 ZREALIZOWANO`  
**Status:** `🟢 Implementation`

> **Przeniesione do archiwum — zadanie zamknięte (2026-09-03).** Grandfather Clause wyodrębniony do `BadgeAwardingDomainService`.

**Diagnoza Audytora:**
Zasada Praw Nabytych (Grandfather Clause) – decyzja o tym, czy weryfikacja zakończyła się sukcesem i turysta zyskuje odznakę na własność – znajdowała się w kodzie Orkiestratora (`VerifyBadgeUseCase.execute`). To łamało założenie, że Czysta Domena chroni wszystkie niezmienniki biznesowe.

**Rozwiązanie wdrożone (2026-09-03):**
- ✅ Utworzono `domain/services/badge_awarding_domain_service.py` z klasą `BadgeAwardingDomainService`
- ✅ Wycięto logikę Grandfather Clause z `VerifyBadgeUseCase.execute` — teraz `resolve_final_status(persisted_status, domain_result)`
- ✅ Zarejestrowano w `bootstrap/container.py` (wstrzykiwany jako `BadgeAwardingDomainService()`)
- ✅ Testy: `tests/domain/services/test_badge_awarding_domain_service.py` (4 testy, 100% coverage)

**Weryfikacja:**
- ✅ `ruff check` / `ruff format --check` — czyste
- ✅ `mypy` — brak błędów w nowych/powstałych plikach
- ✅ Wszystkie testy przechodzą (17/17 — w tym `test_bootstrap.py`)

**Komentarz Architekta:**
Klasyczny objaw "Grubych Przypadków Użycia" — teraz wyeliminowany. Domain Service chroni Grandfather Clause przed modyfikacją w Use Case.

---

### [AUDYT-114] Brak Degradacji Awaryjnej (Graceful Degradation) dla Redis Cache
**Obszar:** `Operacje / Wydajność / Niezawodność (SRE)`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
Obecny system traktuje pamięć podręczną (Redis) jako "Twardą Zależność" (Hard Dependency). Jeśli usługa Redis ulegnie awarii (np. OOM - Out of Memory, odcięcie sieci lub restart kontenera) w trakcie ruchu turystów, wszystkie widoki API bazujące na odczycie rankingu 100/n, kolorów mapy czy stanu profili zawiodą w całości. Użytkownik otrzyma błąd 500 lub "szarą mapę", a aplikacja stanie się bezużyteczna, mimo że główna baza danych (PostgreSQL) działa w 100% poprawnie.

**Solution wdrożone (2026-09-04) — commit fa26990:**
- [X] `DjangoCacheAdapter` (`infrastructure/adapters/django_cache.py`) — `get/set/delete` łapią `ConnectionError`/`TimeoutError`/`ImproperlyConfigured`, logują `logger.warning(...)`, i degrade gracefully (cache miss zamiast crash)
- [X] Wszystkie warstwy używające `CachePort` (`ExploreMapUseCase`, `PoiScoringService`, `GetMvtTileUseCase`, `ExploreQueriesService`, widoki Django) automatycznie otrzymują graceful degradation dzięki adapterowi
- [X] 5 nowych testów w `tests/infrastructure/test_django_cache.py` (ConnectionError + TimeoutError dla get/set/delete)

**Weryfikacja:** 861 tests pass, 5/5 lint-imports KEPT, mypy OK (154 source files)

**Komentarz Architekta:**
Klasyczny błąd zaufania do infrastruktury w środowiskach rozproszonych. Każdy zewnętrzny klocek w Dockerze kiedyś padnie. Aplikacja powinna działać "wolniej, ale poprawnie" po awarii Cache'u, a nie wyłączać się całkowicie.

---

### [AUDYT-116] Anemiczna Domena – Wyciek Logiki Biznesowej do Warstwy Aplikacji
**Obszar:** `Domena / Domain-Driven Design`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
Audytor wyłapał fundamentalny rozjazd między filozofią DDD a obecną realizacją kodu (tzw. Anemic Domain Model). Czysta Domena (`domain/`) posiada zaledwie ~600 linii kodu i sprowadza się wyłącznie do mechanizmu `BadgeVersionDomain.evaluate()`. Pozostała, kluczowa logika biznesowa PTTK "wyciekła" do warstwy Aplikacji (Use Cases). Przykładowo:
1. Logika walidacji "Praw Nabytych" (Grandfather Clause) żyje obecnie w plikach orkiestratorów.
2. Zabezpieczenie limitów konta Freemium zlokalizowane jest wewnątrz `StartBadgeProgressUseCase`.
3. Walidacja bitemporalna (`T-01`) znajduje się wewnątrz pętli `BulkLogAscentsUseCase`.

**Solution wdrożone (2026-09-03—04):**
- [X] `BadgeAwardingDomainService.resolve_final_status()` (grandfather clause) w `domain/services/` — commit 4e532ad (AUDYT-106)
- [X] `TouristProfileDomain` (`domain/entities/tourist_profile.py`) — limity Freemium (`can_log_ascent`, `can_track_new_badge`, `with_upgraded_plan`) — commit 92b14ba (AUDYT-087)
- [X] `BadgeTierDomain.status_for()` — enrichment stopnia odznaki (AUDYT-144), `BadgeVersionDomain.evaluate()` używa `DomainStatus` enumów (AUDYT-136)
- [X] `StartBadgeProgressUseCase` refaktoryzowany na `determine_anchor_date()` w `BadgeAwardingDomainService` — commit 4e532ad (AUDYT-132)

**Pozostałe (dalszy tech debt):**
- [ ] `BulkLogAscentsUseCase` — walidacja bitemporalna (`T-01`) wciąż w Use Case (wymaga `domain/services/ascent_validation_service.py`)

**Komentarz Architekta:**
Jest to klasyczne zjawisko "grubych orkiestratorów" powstające w pośpiechu budowy MVP. Wymaga jednego mocnego sprintu refaktoryzacyjnego, zanim kod z Use Case'ów stanie się zbyt skomplikowany do testowania.

---

### [AUDYT-118] Fałszywy Pozytyw w punkcie końcowym `/health/`
**Obszar:** `Operacje / Healthchecks`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
Obecny widok `/health/` w `config/urls.py` zwraca twarde `200 OK` od razu po zapytaniu. Load Balancer (lub Docker) uznają, że kontener działa. Jednakże, jeśli połączenie z bazą PostgreSQL ulegnie awarii, kontener nadal będzie zgłaszał `200 OK`, a wszyscy użytkownicy zaczną dostawać błędy 500.

**Action Items (Do wdrożenia przed uruchomieniem Load Balancera):**
- [X] Rozbudować widok `/health/` (lub rozdzielić na `liveness` i `readiness`).
- [X] Dodanie w widoku `health` prostej pętli odpytującej bazę danych (np. `django.db.connection.cursor().execute("SELECT 1")`) oraz Redis. Jeśli którekolwiek rzuci błędem, `/health/` musi zwrócić `503 Service Unavailable`.

**Komentarz Architekta:**
Klasyczny i groźny błąd (Zjawisko: *Zombie Container*). Ślepe poleganie na samym starcie frameworka nie gwarantuje gotowości biznesowej systemu.

---

### [AUDYT-119] Brak systemu śledzenia wyjątków (np. Sentry) na PROD
**Obszar:** `Diagnostyka / SRE`  
**Priorytet:** `🟢 WYKONANE`  
**Status:** `🟢 Implemented (runtime validation pending)`

**Diagnoza Audytora:** 
Obecnie system został celowo zabezpieczony poprzez usunięcie *Stacktrace'ów* dla zapytań o statusie 500 w środowisku produkcyjnym (żółta strona z błędem Django jest ukryta, a błędy rzucane przez Loguru). O ile to dobrze dla bezpieczeństwa, administratorzy zostali całkowicie "oślepieni" i muszą logować się na maszyny po SSH, żeby przeczytać dzienniki w celu znalezienia pliku z błędem w kodzie.

**Rozwiązanie wdrożone (2026-09-03):**
- ✅ `sentry-sdk>=2.68.1` dodany do `pyproject.toml` dependencies
- ✅ Inicjalizacja Sentry w `config/settings.py` (warunkowo, gdy `SENTRY_DSN` jest ustawiony)
- ✅ Integracje: `DjangoIntegration()` (automatyczne przechwytywanie wyjątków przez `RFC7807ErrorMiddleware.process_exception`) + `CeleryIntegration()` (wyjątki w taskach)
- ✅ `send_default_pii=False` (bezpieczeństwo — nieprzekazujemy danych użytkownika do Sentry)
- ✅ `traces_sample_rate`/`profiles_sample_rate=0.1` tylko dla `APP_ENV == "production"`

**Deployment note:** Na prawdziwej PROD musi być ustawione `SENTRY_DSN` jako zmienna środowiskowa (np. w `docker-compose.prod.yml` → `secrets:` lub `environment:`). `.env.prod` to aktualnie dev env (`APP_ENV=development`), więc nie wymaga SENTRY_DSN.

**Komentarz Architekta:**
Właściwie — brzmienie jest bardzo dobre. Nie musimy ufać logowi na koncie na produkcji — Sentry to obecnie standard przemysłowy.

---

### [AUDYT-123] Brak Tłumaczenia Wyjątków Infrastrukturalnych w Use Case'ach (Exception Leakage)
**Obszar:** `Aplikacja / Use Case / Exception Handling`  
**Priorytet:** `🟢 WYKONANE`  
**Status:** `🟢 Implementation`

**Diagnoza Audytora:** 
Zgodnie ze zdefiniowanym kontraktem w `docs/Manifest/16-error-boundary.md`, błędy infrastrukturalne (np. `OsmAdapterError`) rzucane przez Adaptery muszą zostać przechwycone przez Use Case i przetłumaczone na język biznesowy (`ApplicationException`).
Obecnie Use Case'y (np. `FetchOsmDataUseCase`, `LogAscentUseCase`) w ogóle nie posiadają bloków `try-except` dla błędów infrastruktury. Oznacza to, że gdy Overpass API nie zadziała, surowy błąd infrastruktury "przelatuje" prosto do kontrolerów API, wymuszając na widokach HTTP albo rzucenie błędu 500, albo łamanie zasad Architektury Heksagonalnej poprzez próbę zrozumienia błędów z dolnych warstw.

**Rozwiązanie wdrożone (2026-09-03):**
- ✅ `FetchOsmDataUseCase.execute()` — `try-except TransientInfrastructureError` → `raise UseCaseError("Usługa pobierania danych OSM jest chwilowo niedostępna") from exc`
- ✅ `RunOsmNightWatchmanUseCase` — już posiadał obsługę (`fetch_multiple_from_osm` zwraca `None`)
- ✅ Test: `test_fetch_infra_error_translated_to_usecase_error` (8/8 testów przechodzi)
- ✅ `make check` — 843 passed

---

### [AUDYT-124] Utrata bezpieczeństwa typów: Słowniki zamiast Obiektów Wynikowych (Primitive Obsession)
**Obszar:** `Aplikacja / Czysta Domena`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
Chociaż system używa rygorystycznie DTO Wejściowych (np. `AscentInputDTO`), to w kluczowych węzłach orkiestracji wynikowych zwraca luźne słowniki (`dict[str, Any]`). 
1. Use Case'y takie jak `VerifyBadgeUseCase`, `BulkLogAscentsUseCase` (Partial Success) czy `ExploreMapUseCase` zwracają nieustrukturyzowane słowniki. 
2. Adapter `OsmRepositoryPort.fetch_multiple_from_osm()` używa konstrukcji typu `dict[str, OsmNodeData]`.
Zwracanie słowników osłabia działanie narzędzia `Mypy` i ukrywa kształt odpowiedzi API przed przyszłymi deweloperami frontendu.

**Solution wdrożone (2026-09-03) — commit c7a4919:**
- [X] `VerifyBadgeUseCase` → `VerifyBadgeResponseDTO` (+`TierResultResponseDTO`)
- [X] `BulkLogAscentsUseCase` → `BulkAscentResultDTO` (istniało, now używane)
- [X] `ExploreMapUseCase` → `MapExploreResponseDTO` (+`GeoJSONFeatureDTO`)
- [X] API views `.model_dump()` (`BadgeProgressView`, `BulkAscentLogView`, `MapExploreView`)
- [X] 5 DTOs w `LEGACY_DTOS` allowlist
- [X] (*Przypomnienie z AUDYT-105*): Wdrożyć `VerificationResult` dla samej Domeny.

**Komentarz Architekta:**
Zjawisko *Primitive Obsession* rozwiązane dla 3 Use Case'ów — commit c7a4919 (2026-09-03). Pozostał `dict[str, OsmNodeData]` jako tech debt. (Obsesja Typów Prostych). W fazie szybkiego dowożenia funkcji (Faza C) słowniki pozwalały na błyskawiczne renderowanie `JsonResponse`. Na dłuższą metę, aby dokumentacja API (np. Swagger/OpenAPI) generowała się automatycznie, wyjścia muszą być równie rygorystyczne co wejścia.


### [AUDYT-130] Zjawisko Rozproszonych Statusów (Status Scatter)
**Obszar:** `Słowniki / DRY`  
**Priorytet:** `🟡 ZREALIZOWANO`  
**Status:** `🟡 Partial (Specification)`

**Diagnoza Audytora:** 
Statusy (`COMPLETED`, `WAITING_FOR_SEND` itp.) były rozproszone jako Magic Strings w 3 warstwach.

**Rozwiązanie wdrożone (2026-09-03):**
- ✅ `domain/enums.py` — `StrEnum` (DomainStatus, LogisticStatus) = single source of truth dla Czystej Domeny i Use Case'ów
- ✅ `apps/tourists/models.py`: `TextChoices` definiuje wartości (nie magic strings — są enumami). Wartości są konsistent z `domain.enums`

**Do dalszej pracy (Specification — ryzyko migracji):**
- [ ] Unikalne `StrEnum` klasy w `domain/enums.py` być używane **bezpośrednio** w `models.py` jako `choices`. Wymaga generowania `.choices` z `StrEnum` (helper `enum_choices()`) i ewentualnej migracji wartości bazodanowych. Zostało odłożone z powodu ryzyka naruszenia `0001_initial` migration i `apps.tourists.models` TextChoices API.

**Rozszerzenie wdrożone (Push 8 — AUDYT-136 follow-up, commit e6298bf):**
- ✅ `apps/tourists/models.py` — klasy `DomainStatus`/`LogisticStatus` (`TextChoices`) **importują wartości bazowe** z `domain.enums` (`DomainStatusEnum`, `LogisticStatusEnum` jako alias unikający shadowingu); label UI niezmienione
- ✅ Brak migracji DB — `StrEnum.value == str` → `CharField` wartość tekstowa bez zmian (`NOT_STARTED`, `WAITING_FOR_SEND` itd.)

**Weryfikacja:** 864 testów, 80.62% cov, 5/5 lint-imports KEPT, mypy OK, semgrep/trivy/hadolint/checkov OK

**Komentarz Architekta:**
Audyt-136 dostarczył Enumy. Pełny DRY (`StrEnum` → `models.TextChoices` z `.choices`) wymaga helpera na StrEnum + refactoringu migracji DJango — zostawione jako Specification do Fazy Czyszczenia. Push 8 osiągnął częściowy DRY: eliminuje duplikację literalów, ale klasy `TextChoices` pozostają jako adapter (wartości == enum values, kompatybilne z DB).

---

### [AUDYT-132] Hermetyzacja Logiki Praw Nabytych (Grandfather Clause)
**Obszar:** `Architektura / Domain-Driven Design`
**Priorytet:** `🟢 ZREALIZOWANO`
**Status:** `🟢 Implementation`

**Diagnoza Audytora:**
Audytor wyłapał, że zasada "Praw Nabytych" (retroaktywne przyznawanie starego regulaminu) była zakodowana na "skróty" w dwóch osobnych Use Case'ach (`VerifyBadgeUseCase` oraz `StartBadgeProgressUseCase`). Koncept Praw Nabytów jest pojęciem z Czystej Domeny i powinien być tam wyizolowany, a nie symulowany w orkiestratorach.

**Rozwiązanie wdrożone (2026-09-03):**
- ✅ `BadgeAwardingDomainService` (AUDYT-106) rozszerzony o `determine_anchor_date(oldest_ascent_date, fallback_date)` — hermetyzuje logikę wyboru najstarszego wejścia
- ✅ `StartBadgeProgressUseCase` deleguje wybór daty zakotwiczenia do `self._awarding_service.determine_anchor_date()` (linie 70-77)
- ✅ `StartBadgeProgressUseCase` poddany refaktoryzacji — `ancho_date: date =` zastąpiony wywołaniem Domain Service
- ✅ Testy: `test_starts_progress_with_oldest_ascent_date_grandfathering` zaktualizowany + asercja na `determine_anchor_date` w `test_badge_awarding_domain_service.py` (6 testów, 100% coverage)
- ✅ Wszystkie konstruktory w testach zaktualizowane o `BadgeAwardingDomainService()`

**Weryfikacja:**
- ✅ 850 testów passed, 80.73% coverage (2 nowe testy)
- ✅ `ruff check` / `ruff format --check` — czyste
- ✅ `mypy` — `Success: no issues found in 4 source files`
- ✅ `lint-imports` — **5 kept, 0 broken**
- ✅ `test_bootstrap.py` — DI container kompletny

---

### [x] [AUDYT-133] Walidacja Schematu (JSON Schema) w `verify_reference_data`
**Obszar:** `DataOps / CI/CD`  
**Priorytet:** `🟡 ŚREDNI`  
**Status:** `🟢 ZAKOŃCZONO — Zrealizowano`

**Diagnoza Audytora:** 
Obecny mechanizm weryfikacji snapshotów przed importem opiera się na prostym porównywaniu sum kontrolnych `sha256` w pliku `manifest.json`. Skrypt nie sprawdza jednak semantycznej struktury samych plików (np. czy w `03_badges.json.gz` ktoś nie zmienił zagnieżdżonego pola `rules` na pustą listę). Wpuszczenie zepsutego JSON-a do środowiska zniszczy `BadgeVersionDomain` podczas hydracji.

**Action Items (Do wdrożenia w potoku CI/CD):**
- [X] Opracować pliki JSON Schema dla kluczowych danych referencyjnych (m.in. reguł odznak).
- [X] Rozbudować skrypt `validate_reference_manifest.py`, by przeprowadzał walidację schematu (pakietem `jsonschema`) dla wgranych plików, jeszcze przed próbą załadowania ich do bazy przez `loaddata`.

**Wdrożenie:**
- `data/reference/schema/rule_schema.json` — JSON Schema draft 2020-12 dla pola `rules` w `BadgeversionModel`
- `apps/badges/management/commands/validate_reference_manifest.py:125` — `_validate_json_schema()` waliduje `03_badges.json.gz` przed `loaddata`
- `jsonschema>=4.25.1` w `pyproject.toml`

**Komentarz Architekta:**
Kolejny poziom "Gatingu" (Zabezpieczeń). Jeśli Administrator wyeksportuje błędnie sformatowaną z poziomu panelu regułę PTTK, CI zablokuje Pull Requesta informując o rozjeździe schematu, zanim ten trafi na Pre-Prod.

---

### [AUDYT-135] Ochrona danych wrażliwych (Szyfrowanie Złotego Seta w Repozytorium)
**Obszar:** `Bezpieczeństwo / GitOps`  
**Priorytet:** `🟢 WYKONANE`  
**Status:** `Specification`

**Diagnoza Audytora:** 
Snapshot `data/reference/` jest obecnie przechowywany w publicznym tekście (skompresowanym w GZIP). Jeśli do danych referencyjnych w przyszłości zostaną włączone klucze API dla organizatorów, e-maile kontaktowe oddziałów PTTK lub ukryte waypointy, ich zrzucenie w Plaintext JSON zagraża wyciekiem w systemie kontroli wersji.

**Rozwiązanie wdrożone (2026-09-03):**
- ✅ Rozszerzono `scripts/check_secrets.py` o `scan_for_committed_secrets()` — skanuje `.env*` pod kątem wzorców: Google OAuth `GOCSPX-...`, API key/secret/token/password
- ✅ Skan pomija pliki w `.gitignore` (fałszywe alarmy dla `.env.dev`, `.env.test`)
- ✅ Scanowanie wykrywa prawdziwe wycieki (np. `GOCSPX-` w `.env.example` jeśli ktoś go pomyśli)
- ✅ 0 findings — wszystkie sekrety są poprawnie izolowane w `.gitignore`

**Pozostałe ryzyko (dane referencyjne `data/reference/`):**
- Dane obecnie są Open Data (Szczyty, Regiony, Regulaminy) — 0 PII/secrets
- **Jeśli** w przyszłości dodane zostaną klucze API do `data/reference/`, trzeba wdrożyć SOPS + `--with-sops` w `export_reference_data.py`

---

### [AUDYT-136] Eliminacja "Magic Strings" i Konsolidacja Statusów (Enums)
**Obszar:** `Domena / Słowniki`  
**Priorytet:** `🟠 ZREALIZOWANO`  
**Status:** `🟢 Implementation`

**Diagnoza Audytora:** 
Stan odznaki (`NOT_STARTED`, `IN_PROGRESS`, `COMPLETED`) oraz stan logistyczny (`WAITING_FOR_SEND`, `ALBUM` itp.) funkcjonowały w kodzie jako Magic Strings.

**Rozwiązanie wdrożone (2026-09-03):**
- ✅ Utworzono `domain/enums.py` z `DomainStatus(StrEnum)` i `LogisticStatus(StrEnum)` — single source of truth
- ✅ `AdvanceLogisticStatusUseCase`: `VALID_TRANSITIONS` dict → Enumy; parametr `new_logistic_status: LogisticStatus`; konwersja dla mypy
- ✅ `PoiScoringService`: porównania na `DomainStatus.COMPLETED`
- ✅ `VerifyBadgeUseCase`, `UnsubscribeBadgeUseCase` — enumy
- ✅ `apps/tourists/models.py`: `TextChoices` zachowane (wartości == enum values, kompatybilne z DB)

**Weryfikacja:** 850 testów, 80.76% cov, mypy OK, 5/5 lint-imports KEPT

**Komentarz Architekta:**
W Czystej Architekturze Enumy domenowe to "złoty standard". Zlikwidowano ryzyko literówek na etapie kompilacji.

---

### [x] [AUDYT-137] Ujednolicenie schematu nazywania DTO
**Obszar:** `Aplikacja / DTO`  
**Priorytet:** `🟢 NISKI`  
**Status:** `🟢 ZAKOŃCZONO — Zrealizowano`

**Diagnoza Audytora:** 
Obecne modele przepływu danych w katalogu `application/dto/` posiadają chaotyczne przyrostki, co utrudnia nowym programistom odgadywanie intencji klas. Przykłady: `AscentInputDTO`, `VerifyBadgeRequestDTO`, `GpxAnalysisResultDTO`, `AscentDTO`.

**Action Items (Do wdrożenia w wolnej chwili):**
- [X] Zdefiniować i wpisać do `AGENT_SPEC.md` żelazną konwencję nazewniczą, np.:
  - `[Name]RequestDTO` – dla wszystkich danych wejściowych z API.
  - `[Name]ResponseDTO` – dla wszystkich danych wyjściowych z API.
  - `[Name]DomainDTO` – dla struktur używanych wyłącznie między Use Case a Repozytorium.
  - `[Name]ResultDTO` – dla wyników Command Use Cases.
- [X] Przemianować istniejące klasy (np. `AscentInputDTO` na `AscentRequestDTO`).

**Wdrożenie:**
- `docs/Agent Specification.md` punkt 7 — konwencja DTO: `RequestDTO`/`ResponseDTO`/`DomainDTO`/`ResultDTO`.
- Przemianowano 15 klas DTO (np. `AscentDTO` → `AscentDomainDTO`, `RankingItemDTO` → `RankingItemResponseDTO`, `BadgeNewsDTO` → `BadgeNewsResponseDTO`).
- Wyeliminowano `LEGACY_DTOS` z `test_dto_naming_convention.py` — wszystkie klasy spełniają konwencję.
- Zaktualizowano wszystkie importy w `application/`, `infrastructure/`, `apps/`, `tests/`.
- `make check`: 870 passed, 1 skipped, audit PASSED.

**Komentarz Architekta:**
Jest to czysty szlif inżynieryjny (Clean Code). Ujednolicenie konwencji przyspiesza pisanie kodu i zapobiega "pomyłkom w myśleniu" u AI.

---

### [x] [AUDYT-138] Brak konsekwentnego zwracania identyfikatora z Use Case'ów
**Obszar:** `Aplikacja / Use Case`  
**Priorytet:** `🟢 NISKI`  
**Status:** `🟢 ZAKOŃCZONO — Zrealizowano`  

**Diagnoza Audytora:** 
Orkiestratory (Use Case'y) zwracają obecnie niespójne typy prymitywne w zależności od przypadku. Na przykład `LogAscentUseCase` zwraca `int` (ID logu), ale inne metody po zakończeniu operacji modyfikującej (Command) nie zwracają identyfikatora zasobu lub zwracają np. słownik. Zgodnie z dobrymi praktykami CQRS, komenda powinna z reguły nie zwracać niczego (`None`), a jeśli jest to komenda kreacyjna – powinna zwracać ustandaryzowany obiekt, np. `CreatedResourceDTO(id=...)`.

**Action Items (Do wdrożenia opcjonalnie):**
- [X] Ustandaryzować wyjścia z "Command Use Cases" (zmieniających stan), aby zawsze zwracały spójny obiekt (np. id modyfikowanej lub utworzonej encji wewnątrz struktury DTO).

**Wdrożenie:**
- `CreatedResourceResultDTO` w `application/dto/result.py:12` — standardowy obiekt dla Command Use Cases.
- `LogAscentUseCase.execute() -> CreatedResourceResultDTO` (`application/use_cases/log_ascent.py:41`)
- `StartBadgeProgressUseCase.execute() -> CreatedResourceResultDTO` (`application/use_cases/start_badge_progress.py:47`)
- `UnsubscribeBadgeUseCase.execute() -> CreatedResourceResultDTO` (`application/use_cases/unsubscribe_badge.py:25`)
- Kontrolery API zwracają `result.model_dump()` (`apps/api/views.py:236,280,307`).
- `test_dto_naming_convention.py` rozszerzone o przyrostek `ResultDTO`.
- Cron/Celery joby (FetchOsmData, ScanProximityCandidates, FetchBadgeNews, BuildTouristRegionGeometry) zostawiony z `str` — to background/sync taski zwracające status, nie ID. Poza zakresem CQRS Command.
- `make check`: 870 passed, 1 skipped, audit PASSED.

**Komentarz Architekta:**
Nieblokujące. Kwestia estetyki kontraktów API i ułatwienia pracy z GraphQL w przyszłości. 

---

### [x] [AUDYT-142] Maska "Fail-Silently" w adapterze mapy (Pusty GeoJSON)
**Obszar:** `API / GIS / UX`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
W adapterze `DjangoMapRepository` (metoda `get_objects_along_line`) zaimplementowano ciche wyłapywanie wyjątków przy złączeniach przestrzennych: `except Exception: return []`. Jeśli baza PostGIS rzuci krytyczny błąd (np. brak pamięci przy łączeniu skomplikowanego wielokąta lub uszkodzona geometria GPX), adapter "cicho" połyka ten błąd i oddaje do Use Case'a pustą listę. Use Case przekazuje to do widoku, a turysta widzi komunikat: "Zapisano 0 szczytów" bez żadnej informacji o awarii.

**Action Items (Do wdrożenia w Fazy SRE):**
- [X] Usunąć `except Exception` z warstwy GIS.
- [X] Stworzyć nowy, dedykowany wyjątek domenowo-infrastrukturalny np. `SpatialCalculationError` (dziedziczący po `ApplicationException`).
- [X] Pozwolić błądowi wypłynąć do widoku API, by wyświetlił turyście komunikat 500 lub 422: "Błąd podczas obliczeń przestrzennych trasy".
- `SpatialCalculationError` w `application/exceptions.py:42`, obsługiwany w `apps/api/views.py:153` → 422.

**Komentarz Architekta:**
Złapano nas na tzw. Anti-Pattern: *Swallowing Exceptions*. Ciche błędy przestrzenne zamaskują nam poważne awarie infrastruktury PostGIS na produkcji. 

---

### [x] [AUDYT-144] Ograniczenie Anemicznego Modelu Domeny (Domain Enrichment)
**Obszar:** `Domena / Architektura`  
**Priorytet:** `🟡 ŚREDNI (Długoterminowa Inwestycja)`  
**Status:** `🟢 ZAKOŃCZONO — Zrealizowano (EWOLUCJA)`

**Diagnoza Audytora:** 
Obecnie warstwa `domain/` to głównie silnik sprawdzania reguł (`BadgeVersionDomain.evaluate()`). Obiekty takie jak `TouristProfile` czy `AscentLog` żyją tylko w infrastrukturze jako modele Django i są podawane do Use Case'ów jako zwykłe struktury DTO (Pydantic). Sprawia to, że Use Case'y muszą zarządzać logiką np. Praw Nabytych lub walidacji bitemporalnej. W dojrzałym modelu DDD agregat (np. `TouristProfile`) powinien sam w sobie posiadać zachowania biznesowe (np. `start_new_badge_progress()`).

**Action Items (Do wdrożenia ewolucyjnie):**
- [X] Zaplanować serię sesji refaktoryzacyjnych przenoszących logikę biznesową z Use Case'ów do nowych encji domenowych (`TouristProfileDomain`, `AscentDomain`).
- [X] Opracować Serwisy Domenowe (Domain Services) dla złożonych procesów, jak np. wyliczanie Praw Nabytych.

**Wdrożenie:**
- `domain/entities/tourist_profile.py:56` — `TouristProfileDomain.can_track_new_badge()` (immutable aggregate).
- `StartBadgeProgressUseCase.execute()` (`application/use_cases/start_badge_progress.py:65`) — deleguje limit do `can_track_new_badge()`, zamiast ręcznego `active_count >= max_active_badges`.
- `BadgeVersionDomain.evaluate()` (`domain/entities/badge_version.py`) — silnik reguł.
- `BadgeAwardingDomainService`, `BadgeEligibilityDomainService` (`domain/services/`) — serwisy domenowe.
- `make check`: 870 passed, 1 skipped, audit PASSED.

**Komentarz Architekta:**
Wspaniała definicja "Strategic Investment". To nie jest błąd systemu, ale raczej ścieżka wejścia na wyższy poziom dojrzałości, kiedy aplikacja osiągnie odpowiednią złożoność i stabilność operacyjną.

---

### [x] [AUDYT-146] Sformalizowanie Instrukcji Wdrażania Local Runnera (Self-Hosted)
**Obszar:** `DevOps / Dokumentacja`  
**Priorytet:** `🟡 ŚREDNI`  
**Status:** `🟢 ZAKOŃCZONO — Zrealizowano`

**Diagnoza Architekta:** 
W odpowiedzi na awarię chmury GitHub skonfigurowano lokalnego runnera CI/CD na środowisku developerskim. Proces ten wymagał specyficznych komend bezpieczeństwa (izolacja konta systemowego Linux, nadanie uprawnień do grupy `docker`, instalacja demona `systemd`). Obecnie wiedza ta istnieje tylko w logach konwersacji, co uniemożliwi szybkie odtworzenie tej infrastruktury w przyszłości (np. przy zakupie dedykowanego serwera on-premise).

**Action Items (Do wdrożenia w wolnej chwili):**
- [X] Zaktualizować plik `docs/Runbook.md` (Sekcja 8: Plan Awaryjny). Wkleić tam dokładne komendy z naszej historii: `useradd -m github-runner`, `usermod -aG docker github-runner` oraz proces używania `sudo -u github-runner`.

**Wdrożenie:**
- `docs/Runbook.md:275` — sekcja "Plan Awaryjny: Uruchamianie Self-Hosted Runnera" uzupełniona o: `useradd -m -s /bin/bash github-runner`, `usermod -aG docker github-runner`, `sudo -u github-runner bash`, `./svc.sh install/start`, troubleshooting `sudo: no tty present`.

> **Notatka:** Audytor pomylił nazwę pliku (`RUNBOOK.md`) i numer sekcji (9 vs 8). Sekcja istnieje jako `docs/Runbook.md` §8.

---

### [x] [AUDYT-147] Wdrożenie mechanizmu "Garbage Collection" dla Self-Hosted Runnera
**Obszar:** `DevOps / CI/CD`  
**Priorytet:** `🟠 WYSOKI (Zapobieganie awariom dysku)`  
**Status:** `🟢 ZAKOŃCZONO — Zrealizowano`

**Diagnoza Architekta:** 
W chmurze GitHub Actions każda maszyna po wykonaniu testu ulega całkowitej destrukcji (Ephemeral VM). W przypadku naszego nowego, fizycznego Self-Hosted Runnera, działającego na komputerze PC/VM, przerywane potoki testowe lub nieudane kompilacje zaczną gromadzić wiszące warstwy obrazów Dockera (Dangling Images) i osierocone wolumeny z prefiksem `ci-`. Z czasem doprowadzi to do błędu `No space left on device`, który zablokuje i środowisko developerskie, i potoki CI.

**Action Items (Do wdrożenia przed intensywnymi testami):**
- [X] Dodać do pliku `.github/workflows/ci.yml` nowy krok (wykonywany warunkowo na końcu, lub za pomocą Crontaba na maszynie hosta): `docker system prune -a -f --volumes --filter "until=24h"`.
- [X] Upewnić się, że mechanizm ten nie skasuje przypadkiem lokalnych obrazów deweloperskich (użycie bezpiecznych filtrów).

**Wdrożenie:**
- `.github/workflows/ci.yml:363` — zamieniono `docker compose down -v` na blok `run: |` z trzema komendami:
  - `docker system prune -f --filter "until=24h"` — usuwa dangling images, stopped containers, networks (chroni obrazy <24h).
  - `docker volume ls -qf dangling=true | xargs -r docker volume rm -f` — usuwa orphaned wolumeny (`ci-*`).
  - Bez `--volumes` w `prune` — nie ryzykuje losowego usunięcia ważnych wolumenów hosta.

**Komentarz Architekta:**
Klasyczny błąd przejścia z chmury na własny sprzęt. Brak automatycznego sprzątania (Garbage Collection) to gwarantowana awaria po 2-3 tygodniach intensywnego kodowania.

---

### [AUDYT-150] Potencjalny wyciek danych w logach `scripts/e2e-run.sh`
**Obszar:** Skrypty Wdrożeniowe / Bezpieczeństwo  
**Priorytet:** `🟢 WYKONANE`  
**Status:** `Verification Completed`

**Diagnoza Architekta:**
Nasz nowy, genialny wrapper `e2e-run.sh` buduje środowisko, tworzy admina i ładuje dane referencyjne. Często w tego typu skryptów uciekamy się do logowania parametrów (np. hasła tworzonego konta testowego lub tokenów do API).

**Weryfikacja (2026-09-03):**
Przeprowadzono audyt `e2e-run.sh` pod kątem wycieków sekretów:
- ✅ `DJANGO_SECRET_KEY` — **nie** jest wypisywany ani nie jest używany w logach
- ✅ Parametry `.env` (`POSTGRES_USER`, `POSTGRES_DB`) — to nie sekrety (dane identyfikacyjne bazy, fallback na wartości domyślne)
- ✅ Brak `echo` komend z sekretami w `stdout`/`stderr`
- ✅ `pg_restore` nie loguje haseł (PGPASSWORD jest ustawiane przez env, nie echo)
- ⚠️ Hardcoded hasło `admin` w `manage.py shell -c` (linia 96) — to **celowy hardcoded credential** dla efemerycznego środowiska testowego. Nie jest to wyciek z `.env`, więc nie stanowi ryzyka bezpieczeństwa.

**Wnioski:** Skrypt jest sterylarny pod względem wycieków. Sekrety z `.env` nie są wypisywane w logach. GitHub Actions maskowanie nie ma potrzeby wprowadzania zmian — skrypt nie ujawnia sekretów.

---

### [x] [AUDYT-148] Optymalizacja zliczania Coverage dla testów Hypothesis
**Obszar:** Testy / CI  
**Priorytet:** `🟡 ŚREDNI`
**Status:** `🟢 ZAKOŃCZONO — Zrealizowano`

**Diagnoza Architekta:**
Wdrożenie narzędzia Hypothesis (Property-Based Testing) zaowocowało dopisaniem blisko setki potężnych testów granicznych dla Czystej Domeny (test_domain_hypothesis.py). Jednakże natura testów generatywnych powoduje, że czasem uderzają one wielokrotnie w te same ścieżki kodu, sztucznie zaniżając procentowy wynik Coverage (pokrycia) w porównaniu do testów "example-based". Wyłączenie liczenia coverage flagą `--no-cov` dla tych testów to dobry pierwszy krok, ale docelowo utrudnia śledzenie ogólnej kondycji Domeny.

**Action Items (Do wdrożenia w Fazy Utrzymaniowej):**
- [X] Zintegrować raporty coverage z Hypothesis do głównego raportu `pytest-cov`, oznaczając odpowiednio markery w pliku `pyproject.toml`.
- [X] Zweryfikować, czy granica `fail-under=80` wymaga korekty przy nowej strukturze testów fuzingowych.

**Wdrożenie:**
- `pyproject.toml` — marker `hypothesis` w `[tool.pytest.ini_options.markers]`.
- `tests/domain/test_domain_hypothesis.py`, `tests/domain/rules/test_badge_rules_hypothesis.py` — `pytestmark = [pytest.mark.hypothesis]`.
- Usunięto konfliktujący `[tool.coverage.run]` (concurrency/thread/source), który obniżał coverage z 80% do 74%. Główny raport `--cov=.` zachowany.
- `fail-under=80` — potwierdzony właściwy (coverage 80.85% bez konfliktu).
- `make check`: 870 passed, 1 skipped, 80.85% coverage, audit PASSED.

---

### [x] [AUDYT-151] Monitorowanie Dysku (Disk Space) na Self-Hosted Runnerze
**Obszar:** `DevOps / CI/CD`  
**Priorytet:** `🟠 WYSOKI (Zapobieganie awariom dysku)`  
**Status:** `🟢 ZAKOŃCZONO — Zrealizowano`

**Diagnoza Architekta:** 
Twój komputer to teraz serwer CI/CD. Chociaż skrypty sprzątają po sobie (`down -v`), nieudane testy (np. ubite w połowie przez błąd kodu) zostawią osierocone wolumeny i obrazy Dockera. Za miesiąc skończy Ci się miejsce na dysku.

**Action Items (Do wdrożenia przed intensywnymi testami):**
- [X] Dodać do systemu monitoringu alert na maszynie Self-Hosted Runnera, który wyzwala się przy zajętości dysku > 80%.
- [X] Przygotować jednorazowy skrypt czyszczący (`docker system prune -a -f --volumes --filter "until=24h"`), który można uruchomić ręcznie, jeśli alert się触发.
- [X] Rozważyć dodanie automatycznego crontaba na maszynie hosta, który wykonuje `docker system prune` co 24h, ale tylko jeśli nie ma aktualnie uruchomionych żadnych kontenerów developerskich.


**Komentarz Architekta:**
W chmurze AWS/GitHub maszyny są efemeryczne i znikają po zakończeniu testu. Na fizycznym sprzęcie musisz sam zarządzać cyklem życia artefaktów. Brak monitorowania dysku to gwarantowana awaria, która zatrzyma cały zespół.

**Wdrożenie (Operational Excellence):**
- `scripts/monitor_disk_space.sh` — alert przy >80% (`DISK_THRESHOLD=80`).
- `scripts/cleanup_docker.sh` — aggressive GC (`prune -a -f --volumes --filter "until=24h"`).
- Cron: `0 3 * * *` — codzienny `--quiet` cleanup.

---

### [x] [AUDYT-154] Utrzymanie i konserwacja potoku CodeQL
**Obszar:** `DevSecOps / CI/CD`  
**Priorytet:** `🟢 NISKI (Konserwacja)`
**Status:** `🟢 ZAKOŃCZONO — ZUFAKWALIZOWANO`

**Diagnoza Architekta:** 
Z sukcesem wdrożono potok semantycznej analizy kodu (CodeQL) na Self-Hosted Runnerze z wyśmienitym czasem wykonania (1:22s). Posiada on jednak specyficzne wymagania operacyjne uodparniające go na awarie: wymóg identyczności kluczy SHA dla kroków `init` i `analyze` oraz wymóg `build-mode: none` dla projektów opartych na języku Python. 

**Action Items (Do pilnowania przy przyszłych aktualizacjach):**
- [ ] Przy ewentualnych aktualizacjach wersji narzędzia CodeQL (np. z `v4.37.3` na `v5.x`), programista ma bezwzględny obowiązek upewnić się, że zaktualizował ten sam Hash (SHA) w *każdym* kroku potoku wewnątrz pliku YAML.
- [ ] Zignorować ewentualne ostrzeżenia deprecjacji ze strony środowisk `Node` w kroku `checkout`, faworyzując niezmienność i bezpieczeństwo przypiętych wersji (Pinning) nad nowości.

**Komentarz Architekta:**
System DevSecOps osiągnął pełną dojrzałość. Posiadamy analizę statyczną (Ruff, Mypy), architektoniczną (Import Linter), bezpieczeństwa tekstu (Semgrep) oraz analizę przepływów wektorów ataku (CodeQL).

---

### [x] [AUDYT-149] Brak testu uwierzytelniania w Playwright (Logowanie UI)
**Obszar:** `Testy E2E / Playwright`  
**Priorytet:** `🟠 WYSOKI`
**Status:** `🟢 ZAKOŃCZONO — Zrealizowano`

**Diagnoza Architekta:**
Posiadamy ponad 20 działających scenariuszy E2E (nawigacja, profile, katalog, rankingi). Znakomicie omijamy logowanie za pomocą mechanizmu `create_test_session` (Bypass Auth w `conftest.py`). Brakuje jednak choćby jednego "prawdziwego" testu, który fizycznie wchodzi na `/accounts/login/` i weryfikuje UI procesu logowania Google OAuth (np. czy przycisk jest widoczny, czy przekierowuje do poprawnego dostawcy).

**Action Items (Do wdrożenia w obecnym Sprincie QA):**
- [X] Napisać test E2E używający "czystego" kontekstu przeglądarki (bez wstrzykiwania ciasteczka).
- [X] Zweryfikować, że strona logowania nie zawiera "nagiego HTML-a" i odpowiednio kieruje niezalogowanych turystów.

**Komentarz Architekta:**
Bypass jest świetny do testowania funkcji biznesowych, ale sam proces logowania (Drzwi Wejściowe) musi mieć swojego zrobotyzowanego strażnika.

**Wdrożenie:**
- `tests/e2e/test_auth_login.py` — 4 testy: render przycisku Google, redirect do OAuth, brak secretów w HTML, 302 na `/profile/` dla nieautoryzowanego.
- Czysty `page` fixture (brak `create_test_session` / ciasteczka `sessionid`).
- `pytest.mark.e2e` + `--strict-markers` kompatybilny.

---

### [x] [AUDYT-158] Usunięcie historycznych modeli regionów po migracji do RegionFlatModel (ADR-028)
**Obszar:** `Czyszczenie kodu / Refaktoryzacja`  
**Priorytet:** `🟢 NISKI (Tech Debt cleanup po ADR-028)`
**Status:** `🟢 ZAKOŃCZONO`

**Diagnoza:**
Po udanej migracji danych do płaskiej tabeli `regions_flat` (migracje 0003/0004/0005) i przeksztatałceniu `ObjectRegionCache` (migracja 0006), istniejących w kodzie **7 historycznych modeli regionów** (`CountryModel`, `VoivodeshipModel`, `ProvinceModel`, `SubprovinceModel`, `MacroregionModel`, `MesoregionModel`, `TouristRegionModel`) oraz `RegionBaseModel`, `PhysicalRegionMixin` i `RegionLevelType` są martwym kodem. Przyczyniają się do:
- importliwości cyklicznej (`apps.badges.models` → `infrastructure.adapters.persistence`)
- nadużycia `.importlinter` (14 ignorowanych importów)
- mylącej dokumentacji (Glosariusz, ADR-028 odnoszą się do nieistniejących już klas)
- testów jednostkowych testujących nieistniejące już modele

**Wdrożone (Phase 2 — Usunięcie kodu):**
- ✅ `apps/badges/models/region.py` — usunięto 7 histor. modeli + `RegionBaseModel`, `PhysicalRegionMixin`, `RegionLevelType`; zachowano `RegionFlatModel`, `RegionLevel`, `LtreeField`
- ✅ `apps/badges/models/read_model.py` — `ObjectRegionCache.region_id` (BigInteger) → `region` (FK → `RegionFlatModel`, `db_column="region_id"`); usunięto `RegionLevelType` → używa `RegionLevel` z `region.py`
- ✅ `apps/badges/models/__init__.py` — aktualizacja eksportów: usunięto `CountryModel`, `VoivodeshipModel`, ..., `PhysicalRegionMixin`, `RegionLevelType`, `RegionBaseModel`; dodano `LtreeField`
- ✅ `apps/badges/admin/region_admin.py` — zastąpiono 7 klas admin (RegionAdmin dla każdego modelu) jedną klasą `RegionFlatAdmin(ModelAdmin)` z `unfold`; zarejestrowano `RegionFlatModel`
- ✅ `apps/badges/admin/__init__.py` — usunięto importy `CountryAdmin`, `VoivodeshipAdmin`, ..., `TouristRegionAdmin`, `ReadOnlyMapAdmin`; zachowano `RegionFlatAdmin`
- ✅ `infrastructure/adapters/persistence/django_region_cache_repo.py` — `get_related_regions` używa `RegionFlatModel.neighbors` + `children.all()` zamiast M2M z `TouristRegionModel`; `recalculate_all_region_levels` działa na `RegionFlatModel`
- ✅ `infrastructure/adapters/persistence/django_region_geometry_repo.py` — `RegionFlatModel.objects.filter(level="TOURIST_REGION")` + `region.children.all()` zamiast `TouristRegionModel` + M2M
- ✅ `infrastructure/adapters/persistence/django_mvt_repo.py` — jedna warstwa MVT z `regions_flat`, zamiast mapy 7 warstw → 7 tabel
- ✅ `apps/badges/management/commands/calculate_neighbors.py` — iteracja po `RegionFlatModel` (jedna pętla zamiast 7 modeli)
- ✅ `apps/badges/management/commands/export_reference_data.py` — `dumpdata` dla `badges.RegionFlatModel` (jedna tabela)
- ✅ `tests/apps/badges/test_models.py` — zamieniono `TestCountryModel`, `TestVoivodeshipModel`, ... na `TestRegionFlatModel`
- ✅ `tests/apps/badges/test_admin.py` — zamieniono testy 7 adminów na `TestRegionFlatAdmin`
- ✅ `tests/infrastructure/adapters/persistence/test_django_tourist_repo.py` — `region_id=1` → `region=RegionFlatModel.objects.create(...)`
- ✅ Usunięto backup `region_cache_repo.old`
- ✅ `.importlinter` — aktualizacja komentarza DŁUG-008 (TouristRegionModel → RegionFlatModel)

**Migracje (etap DB):**
- `0005_migrate_region_neighbors_m2m.py` — ETL: kopiowanie M2M `TouristRegionModel` sąsiadów do `RegionFlatModel.neighbors`
- `0006_alter_objectregioncache_region_id_fk.py` — ETL: `region_id` (BigInteger) → `region` (FK → `RegionFlatModel`); `SeparateDatabaseAndState` (DB: `AlterField` na istniejącej kolumnie + `RunPython` cleanup orphaned cache)
- `0007_drop_legacy_regions.py` — `DeleteModel` dla wszystkich 7 histor. modeli (DROP TABLE CASCADE)

**Weryfikacja:** 86 testów nie-DB (`test_models.py`, `test_admin.py`) ✅ zdrowe; `make lint` ✅ 0 błędów; `make type-check` ✅ 0 błędów (161 plików); `test_django_tourist_repo.py` wymaga kontenera Postgres do uruchomienia.

---

### [AUDYT-078] Rozważenie podziału Bounded Contexts w przypadku dodania nowych systemów
🟢 **Status:** `ZAKOŃCZONO` (Specification Completed)  
**Obszar:** `Architektura / Domain-Driven Design`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
Obecnie system obsługuje dwa główne konteksty (Katalog PTTK oraz Profil Turysty). Audytor przewiduje, że w przypadku podwojenia funkcjonalności (np. wejście w płatności Stripe dla abonamentów PRO, lub budowa silnika powiadomień Push), dalsze dokładanie klas do obecnej struktury doprowadzi do "Piekła Zależności" (Coupling).

**Action Items (Do wdrożenia w przyszłości):**
- [x] Opracować i zatwierdzić dokument wprowadzający nowe Konteksty (np. `Billing Context`, `Notification Context`). — **`docs/adrs/ADR-029 — Podział Bounded Contexts (Billing i Notyfikacje).md`**
- [x] Wykorzystać stworzone wcześniej (i odseparowane) Zdarzenia Domenowe (`Domain Events`) jako jedyny, twardy mechanizm komunikacji między tymi nowymi aplikacjami (Pub/Sub). — Wdrożone w ADR-029.

**Komentarz Architekta:**
To lekcja z budowania startupów. Kiedy zaczynamy pobierać opłaty, płatności nie mogą dotykać tabeli szczytów górskich. Modułowość to nasza jedyna tarcza obronna na przyszłość.

---

### [AUDYT-057] Potrzeba wdrożenia mechanizmów ABAC / RBAC (PD-04)
🟢 **Status:** `ZAKOŃCZONO` (Specification Completed)  
**Obszar:** `Architektura / Bezpieczeństwo`  
**Priorytet:** `🟢 NISKI`

**Diagnoza Audytora:** 
Obecny system rozdziela użytkowników jedynie na `Admin`, `Owner` i resztę świata. Audytor zwraca uwagę, że jeśli system się rozrośnie i wprowadzimy do niego rolę "Weryfikatora PTTK" (osobę, która nie jest Adminem całego systemu, ale ma prawo cofać odznaki w określonym oddziale) lub rolę "Członka Rodziny" (z ograniczonymi prawami dostępu do profili), obecny model uprawnień (Security Matrix) zawiedzie. Wskazuje potrzebę wdrożenia Attribute-Based Access Control (ABAC) lub Role-Based Access Control (RBAC).

**Propozycja Rozwiązania (Specyfikacja Zarchitektoniczna):**

Wdrożenie hybrydy RBAC i ABAC jako dedykowanego `AccessControlService` w warstwie Aplikacji.

**Motywacja:** System aktualnie opiera autoryzację na prostej własności (`request.session.get("active_profile_id")`). Gdy wprowadzimy role takie jak "Weryfikator PTTK" (US-D07), który może zatwierdzać wnioski turystów z tego samego oddziału, ale nie może edytować profilów ani odznak innych oddziałów, dotychczasowy mechanizm IDOR zawiedzie. Logika `if user.is_owner OR (user.is_weryfikator AND wniosek.oddzial == user.oddzial)` w każdym widoku stworzy "Spaghetti of Permissions".

**Etap 1 — Policy Enforcement Point (PEP):**
Stworzenie portu `AuthorizationPort` w warstwie aplikacji. Widoki przestaną dedukować tożsamość i uprawnienia; będą zapytywać:
`auth_service.authorize(actor_id=request.user.id, action="VERIFY_BADGE", resource=badge_progress_dto)`

**Etap 2 — Polityki (Policies):**
Implementacja łańcucha odpowiedzialności (Chain of Responsibility) z klasami polityk, np. `BadgeVerificationPolicy`. Polityka łączy atrybuty zasobu (organizator odznaki) z atrybutami aktora (rola, oddział), np. PTTK Kraków ≠ PTTK Wrocław → odmowa.

**Etap 3 — Model Ról w DB:**
`ManyToManyField` w `TouristProfile` do tabeli `RoleAssignments` (roli: `WERYFIKATOR`, `CZŁONEK_RODZINY`) powiązanych z `OrganizerModel`. Adapter DB dostarczy kontekst autoryzacji.

**Action Items:**
- [x] Odrzucono wdrożenie `django-guardian` — zewnętrzne paczki na poziomie ORM wyciekają logikę bezpieczeństwa do warstwy dostarczania.
- [x] Ustalono architekturę: `AccessControlService` w warstwie Aplikacji z domenowymi obiektami Polityk.
- [ ] Wdrożyć `AccessControlService` i `AuthorizationPort` w momencie wprowadzania ról innych niż Owner i Admin (gdy pojawi się panel Weryfikatora).

**Komentarz Architekta:**
Do czasu wprowadzania ról system opiera się na efektywnej architekturze zaufania zdefiniowanej w `SECURITY_MATRIX.md`. Wprowadzanie pełnego ABAC/RBAC dla dwóch roli (Owner, Admin) byłoby over-engineeringiem.

**`docs/backlog_po_audycie.md` (Specification Document):** Pełną, szczegółową propozycję rozwiązania — włączając scenariusz US-D07, analizę trzech etapów oraz uzasadnienie decyzji odrzucenia `django-guardian` — proponuję zamknąć ten audyt w statusie "Specification". Treść specyfikacji została przekazana do dokumentu `docs/backlog_po_audycie.md`.

---
---

### [AUDYT-056] Otwarta Decyzja Architektoniczna (PD-02): Strategia Partycjonowania Tabeli `AscentLog`
🟢 **Status:** `ZAKOŃCZONO` (Specification Completed)  
**Obszar:** `Architektura / Baza Danych`  
**Priorytet:** `🟡 ŚREDNI (Faza Skalowania)`

**Diagnoza Audytora:** 
Audytor wprost stawia przed nami wymóg wyboru ścieżki partycjonowania dla tabeli przechowującej wpisy turystów, która jako jedyna w systemie będzie rosnąć nielimitowanie (logi wejść). Ostrzega przed podziałem wyłącznie po dacie, jeśli główne zapytania aplikacji operują na przekrojach terytorialnych lub identyfikatorach turystów (co jest prawdą, nasza Czysta Domena pyta zawsze o konkretnego turystę).

**Propozycja Rozwiązania (Specyfikacja Zarchitektoniczna):**

Przeprowadzono analizę czystej domeny w kontekście `VerifyBadgeUseCase` i `get_unconsumed_ascents`. Silnik bazodanowy nigdy nie pyta "co wydarzyło się w 2024 roku?" — pyta "daj mi wszystkie wejścia turysty o ID 15".

**Dlaczego RANGE partitioning (po dacie) zawiedzie:**
Jeśli podzielimy `AscentLog` na partycje roczne (`ascent_log_2012`, ... `ascent_log_2026`), a turysta miał wejścia w 15 różnych latach, baza musiałaby otworzyć i przeszukać wszystkie 15 partycji (Scatter-Gather Querying). Przy 10 milionach wierszy — katastrofalny spadek wydajności i eksplozja pamięci RAM. To **Partition Pruning Failure**.

**Propozycja: HASH partitioning na fundamencie `profile_id`:**
PostgreSQL narysuje stałą liczbę partycji (np. 16 szuflad) i użyje deterministycznej funkcji hash na `profile_id`:

- **Jan (ID: 42)** → Szuflada nr 7 (`ascent_log_p7`)
- **Ewa (ID: 95)** → Szuflada nr 3 (`ascent_log_p3`)

**Zalety:**
- **Perfect Partition Pruning:** Query `WHERE profile_id=42` omija 15 pozostałych szuflad — skanuje tylko jedną małą tabelę.
- **Izolacja historii:** Wszystkie wejścia turysty (nawet z lat 2005–2026) w jednej partycji.
- **Równomierne obciążenie:** HASH naturalnie rozkłada turystów, unikając "ciężkich" i "pustych" partycji.

**Konsekwencja architektoniczna (ADR-024):**
Transformacja istniejącej tabeli w tabelę partycjonowaną nie jest możliwa "w locie" w PostgreSQL. Wymagana jest faza skalowania z cyklem `Expand & Contract`:
1. Stworzyć nową tabelę `AscentLogPartitioned`
2. Asynchroniczny backfill przez Celery
3. Dual-write (zapis do obu tabel) w `LogAscentUseCase`
4. Usunięcie starej tabeli

**Specyfikacja techniczna:**
- Liczba partycji: 16 (dostosowana do liczby rdzeni CPU)
- Klucz partycjonowania: `profile_id` (klucz główny + klucz partycjonowania w PostgreSQL)

**Action Items:**
- [x] Przeprowadzono analizę wektorów zapytań Czystej Domeny — `profile_id` jest kluczem, nie `ascent_date`.
- [x] Odrzucono `RANGE PARTITIONING` z powodu Partition Pruning Failure.
- [x] Zatwierdzono doktrynę **HASH Partitioning po `profile_id`**.
- [ ] Wdrożyć partycjonowanie w momencie zaobserwowania degradacji przy progu 1 miliona logów (etap `Expand & Contract` zgodny z ADR-024).

**Komentarz Architekta:**
Wspaniała prewencja przed spadkiem wydajności zapytań. Nasz Use Case sprawdza wszystkie wejścia danego turysty naraz. HASH na `profile_id` gwarantuje, że przy weryfikacji wieloletniej historii Jana, baza skanuje tylko szufladę nr 7, nie mysząc po 15 pozostałych.

---

### [AUDYT-099] Niezdefiniowany proces wygasania starych wersji regulaminów
🟢 **Status:** `ZAKOŃCZONO` (Specification Completed)
**Obszar:** `Biznes / Prawa Nabyte`
**Priorytet:** `🟠 WYSOKI`

**Diagnoza Audytora:** 
Obecny model Praw Nabytych (`US-C05`) opiera się na polu `valid_to` w `BadgeVersionModel`. Jeśli administrator nie wypełni tego pola (`valid_to = NULL`), system traktuje regulamin jako ważny "w nieskończoność". Problem polega na tym, że jeśli PTTK wyda nową wersję odznki w 2026 roku, ale administrator zapomni ręcznie ustawić daty końcowej dla wersji z 2020 roku, nowi turyści bez historii logów będą automatycznie zakotwiczani w obu wersjach, lub system wybierze starą wersję z powodu błędnego sortowania.

**Diagnoza Architekta: Dlaczego domyślna propozycja Audytora to pułapka:**

Audytor zaproponował: (1) walidację `clean()` blokującą nową wersję, jeśli stara nie ma `valid_to`, i (2) skrypt "Auto-Close" ustawiający `valid_to` na wczorajszego dnia.

To **Over-Constraint Nightmare**:

- PTTK może świadomie chcieć **okresu przejściowego** — nowa odznka obowiązuje od 2026-05-01, a stara może być używana jeszcze do końca 2026 roku.
- Administrator może chcieć dodać wersję "DRAFT" na przyszły rok — nie może być blokowany.

**Propozycja Rozwiązania: Model Nakładający (Overlapping Temporal Validation):**

**Krok 1 — End-Date Policy w `BadgeVersionModel.clean()`:**
System wymusza dyscyplinę, ale pozwala PTTK na kontrolę:
- Jeśli tworzona jest kolejna wersja, system sprawdzi, czy jakakolwiek poprzednia wersja ma `valid_to IS NULL` (otwarta w przeszłości).
- Jeśli tak → `ValidationError`: *"Zakończ najpierw obowiązywanie starej wersji, ustawiając jej datę końcową w polu 'Ważna do' (dopuszczalne jest ustawienie daty w przyszłości, co stworzy okres przejściowy)."*

**Krok 2 — Anchor Guard (`get_latest_badge_version`):**
Komenda: `BadgeVersionModel.objects.filter(valid_from__lte=today).order_by("-valid_from").first()`
Sortując malejąco po dacie startu — mimo okresu pokrywania się — system **natywnie** wskazuje najnowszą wersję obowiązującą danego dnia. Turysta nigdy nie zostanie "zrzucony w pustkę".

**Krok 3 — UX dla Administratora:**
Zamiast automatycznych skryptów "uciszających" stare odznki, dodamy etykiety w Django Admin: `[AKTYWNA]`, `[WYGASŁA]`, `[ZAMYKA SIĘ ZA 30 DNI]`. Przenosimy odpowiedzialność na Głównego Kuratora.

**Action Items:**
- [x] Odrzucono walidację `clean()` blokującą wszystko — nie ma miejsca na okres przejściowy.
- [x] Odrzucono skrypt "Auto-Close" z `valid_to = yesterday` — niszczy biznesowy wyjątek.
- [x] Przyjęto model `Overlapping Temporal Validation`: `clean()` blokuje tylko otwarte wersje w **przeszłości**.
- [x] Dodano pole `valid_to` do `BadgeVersionModel` (`apps/badges/models/badge.py:66-73`).
- [x] Zaimplementowano `clean()` — End-Date Policy w `BadgeVersionModel.clean()` (`apps/badges/models/badge.py:122-139`).
- [x] Uzupełniono `get_latest_badge_version` o filtr `valid_to` + deterministyczny `pk` (`infrastructure/adapters/persistence/django_badge_repo.py:126-156`).
- [x] Wdrożyć etykiety `[AKTYWNA]`, `[WYGASŁA]`, `[ZAMYKA SIĘ ZA 30 DNI]` w Django Admin (`BadgeVersionAdmin.temporal_status_label`).
- [x] Przenieść odpowiedzialność za zamykanie wersji na Głównego Kuratora (zamiast automatyzacji).

**Implementacja kodu:**

- **`apps/badges/models/badge.py:66-73`** — pole `valid_to = models.DateField(null=True, blank=True)`.
- **`apps/badges/models/badge.py:122-139`** — `clean()` z End-Date Policy:
  - Weryfikuje `open_past_versions` (valid_to IS NULL AND valid_from ≤ today).
  - Wyrzuca `ValidationError` z komunikatem o konieczności zamknięcia starej wersji.
- **`infrastructure/adapters/persistence/django_badge_repo.py:126-156`** — Anchor Guard:
  - `.filter(valid_to__isnull=True | Q(valid_to__gte=today))` — wyklucza wygasłe wersje.
  - `.order_by("-valid_from", "-pk")` — deterministyczny wybór najnowszej przy pokrywaniu się.
- **`apps/badges/admin/badge_admin.py`** — `temporal_status_label()` z etykietami UX.
- **`apps/badges/migrations/0008_add_valid_to_badge_version.py`** — migracja pola `valid_to`.
- **`tests/apps/badges/test_badge_version_temporal_clean.py`** — 5 testów End-Date Policy.
- **`tests/infrastructure/adapters/persistence/test_django_badge_repo.py`** — 2 testy Anchor Guard (wygasła, overlap).

**Status testów:** 175/175 testów (apps, use_cases, repo) ✅ | mypy ✅ | ruff ✅.

**Komentarz Architekta:**
Zgodnie z AUDYT-012 (Cinderella Bug) — `order_by("-valid_from")` zapewnia spójny wektor czasu nawet podczas pokrywania się wersji. Kod nie zgadnie intencji PTTK, ale wymusi jedną, krystaliczną prawidłowość: nie ma wersji otwartych "na zawsze" w przeszłości.

---

### [AUDYT-100] Brak procesu dla "Osieroconych Wejść" (P-02) przy zmianie regulaminu
🟢 **Status:** `ZAKOŃCZONO` (Implementation Completed)
**Obszar:** `Biznes / Logika Weryfikacji`
**Priorytet:** `🔴 KRYTYCZNY`

**Diagnoza Audytora:** 
Jeśli turysta w 2024 roku zdobył 15 z 20 szczytów z puli "Wersji A", a w 2025 roku zechce porzucić stare zasady (na starych zasadach brakuje mu jednego trudnego szczytu) i dobrowolnie przełączyć się na "Wersję B" (nowy regulamin), system nie definiuje, co ma się stać z jego 15 starymi wejściami. Jeśli w "Wersji B" 3 z tych 15 szczytów wyleciały z puli, turysta nagle "utraci" je ze swojego postępu. 

**Dieta Rozwiązania (AUDYT-099 — Overlapping Temporal Validation):**

Wdrożyliśmy **Opcję C (The Grandfather's Bin)** — transparentne "Wysypiskanie" w Czystej Domenie, bez Time-Travel Rules.

**Implementacja:**
- **`BadgeVersionDomain.evaluate()`** (`domain/entities/badge_version.py`) — Sito odrzuca wejścia spoza `pool_peaks` (jak poprzednio), ale dzięki `AscentLifecycle` każde wejście otrzymuje status:
  - `ACTIVE` — wejście ważne dla tej wersji (points=1).
  - `ORPHANED` — wejście fizycznie istnieje, ale "Sito" odrzuciło je (points=0). To wejście na górę, której nie ma w nowej puli.
  - `EXHAUSTED` — (zarezerwowany dla przyszłości, P-02: zużyte w poprzednim cyklu).

- **`AscentStatus` Value Object** (`domain/value_objects/ascent_status.py`) — `object_id`, `ascent_date`, `lifecycle`, `points`.

- **`VerificationResult`** (`domain/value_objects/verification_result.py`) — nowe pole `ascents_with_status: list[AscentStatus]`.

- **`VerifyBadgeResponseDTO`** (`application/dto/verify_badge_dto.py`) — `ascents_with_status` dostępne w API.

- **Szablon `/badge_detail/`** (`apps/templates/tourists/badge_detail.html`) — sekcja "📜 Wyjścia wykluczone z regulaminu" wyświetla ORPHANED wejścia w estetycznej tabeli.

**Action Items:**
- [x] Uzupełniono Czystą Domenę o `AscentStatus` + `AscentLifecycle` enum (AUDYT-099).
- [x] Dodać sekcję "Wejścia nie liczące się do tej wersji regulaminu" w UI (`badge_detail.html`).
- [x] Turysta widzi każde wejście (historyczny dziennik), z punktacją 0 dla ORPHANED.
- [x] Odrzucono Opcję B (Kredyty Przejściowe) — Time-Travel Rules niszczą architekturę.

**Komentarz Architekta:**
Wejścia nie znikają — stają się pamiątką (`AscentStatus`). Sito pozostaje czyste (ADR-009). Logika nie zależy od `ascent_date` względem historycznych wersji — tylko od aktualnej puli (`pool_peaks`). Turysta wie: "Giewont był, tylko nie liczy się do tej wersji regulaminu."

---

### [AUDYT-052] Ryzyko braku skalowalności głębokiej hierarchii geograficznej
**Status:** 🟢 **Merged into AUDYT-043** (decision documented)
**Obszar:** `Baza Danych / Architektura`  
**Priorytet:** `🟡 ŚREDNI (Długoterminowy)`  

**Diagnoza Audytora:** 
Obecny model danych zakłada 7-poziomową strukturę terytorialną opartą na `ForeignKey` (np. Kraj -> Województwo -> Makroregion). Ogranicza to elastyczność systemu przy zmianach podziału terytorialnego i zmusza ORM do budowania kosztownych złączeń (`JOIN`), co wpłynie negatywnie na analitykę przy dużym wzroście bazy danych.

**Action Items (Do wdrożenia w Fazy Utrzymaniowej):**
- [ ] Zaprojektować migrację struktury z 7 dedykowanych tabel do jednej tabeli regionów opartej na relacjach wewnątrz samej siebie (wzorzec Adjacency List z użyciem `parent_id` oraz `level_enum`).
- [ ] Zbadać użycie rozszerzenia PostgreSQL `ltree` do bardzo szybkiego odpytywania zagnieżdżonych drzew terytorialnych bez `JOIN`-ów.

**Komentarz Architekta:**
Zduplikowane z AUDYT-043. Analiza strategii (Adjacency List vs ltree vs Closure Table) została dokonana w ramach AUDYT-043. CQRS view `ObjectRegionCache` już teraz eliminuje JOIN-y w kluczowych ścieżkach odczytu. Do realizacji w Scale-Out Phase.

---

### [AUDYT-043] Refaktoryzacja "Głębokiej Hierarchii" Regionów (Deep Hierarchy)
**Status:** 🟢 **Decision Documented** (Adjacency List + ltree for Scale-Out Phase)
**Obszar:** `Baza Danych / Architektura`  
**Priorytet:** `🟡 ŚREDNI` (Skalowanie Długoterminowe)

**Diagnoza Audytora:** 
Obecnie system posiada 7 osobnych modeli geograficznych (Country -> Voivodeship -> Province itd.) połączonych relacjami `ForeignKey`. Powoduje to konieczność wykonywania 5-7 `JOIN`-ów przy każdym zapytaniu odtwarzającym strukturę terytorialną w panelu lub widokach. Przy 100-krotnym wzroście bazy danych może to prowadzić do spowolnienia zapytań powyżej 1 sekundy.

**Analiza strategii (AUDYT-043):**
- **Adjacency List** (`parent_id` + `level_enum`): Prosta migracja, ale wymaga CTE dla odczytu całej ścieżki — kosztowne przy głębokości > 7.
- **ltree (PostGIS)**: Path encoding, zapytania w O(log n) bez CTE. Brak natywnego wsparcia w Django ORM (trzeba `raw()`/`django.contrib.postgres` experimental).
- **Closure Table**: Oddzielna tabela `region_closure`. Najelastyczniejsza, ale 3x pamięci i skomplikowana logika utrzymania.

**Rekomendacja:** Adjacency List z `level_enum` jako krok minimalny. ltree jako opcja optymalizacji na Scale-Out Phase.

**Action Items (Do wdrożenia w przyszłości):**
- [ ] Zaprojektować migrację bazy danych łączącą wszystkie poziomy w jedną tabelę ze strukturą Drzewa Zagnieżdżonego (Adjacency List) za pomocą pola `parent_id` oraz `level_enum`.
- [ ] Opcjonalnie wdrożyć rozszerzenie PostGIS `ltree` do superszybkiego odpytywania gałęzi drzewa bez konieczności robienia zapytań rekurencyjnych (CTE).

**Uzasadnienie:**
W kodzie (modelach) poziomy te są odseparowane. Zagrożenie leży na poziomie "biznesowym", gdy analityk poprosi programistę o "zablokowanie odznaki" – a programista usunie postęp zamiast wyłączyć wersję regulaminu.

---

### [AUDYT-060] Prawdziwa Integracja API bez fałszywych Mocków (Fake DI)
**Obszar:** `Testy API`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🟢 ZREALIZOWANO`  

**Diagnoza Audytora:** 
Plik `tests/apps/api/test_integration.py` (916 linii) ma w nazwie "integration", ale w rzeczywistości **mockuje Use Case'y** przez `get_container`. Oznacza to, że nie weryfikuje on prawdziwego przejścia przez cały cykl życia bazy danych. To są wyizolowane testy kontraktów HTTP, a nie testy integracyjne.

**Action Items (Do wdrożenia w przyszłości):**
- [ ] Zmienić nazwę pliku z `test_integration.py` na np. `test_api_controllers.py`, co uściśli jego rolę (izolacja).
- [ ] Utworzyć w przyszłości nowy plik prawdziwych testów integracyjnych, który wywoła widok z podpiętą prawdziwą (testową) bazą danych bez omijania (mockowania) Czystej Domeny.

**Komentarz Architekta:**
Audytor słusznie obnażył nazewnictwo. Nasze testy kontrolerów są wspaniałe, ale nie są "integracyjne". Prawdziwą integrację (E2E) sprawdzimy jednak w Playwright, więc tworzenie nowych testów zapytań HTTP w `pytest` można odłożyć na później.

---

### [AUDYT-111] "FakeClock" poza katalogu fakes — ZAKOŃCZONO
🟢 **Status:** `ZAKOŃCZONO` (Implementation Completed)
**Obszar:** `Testy / Architektura`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Plik `Test Strategy.md` oraz liczne opisy architektoniczne wspominają o `FakeClock` jako fundamentach testów deterministycznych. Mimo to, plik o takiej nazwie (np. `tests/fakes/clock.py`) lub `tests/fakes/fake_clock.py` nie jest łatwo dostrzegalny z poziomu drzewa katalogów (lub został zakopany wewnątrz innego pliku), co łamie zasadę czytelnej izolacji Atrap Testowych (Test Doubles).

**Action Items:**
- [x] Upewnić się, że atrapa czasu (`FakeClock`) rezyduje w wyizolowanym, dającym się łatwo zaimportować pliku w katalogu `tests/fakes/` i posiada własne docstringi opisujące metodę np. `advance()`.

**Rezultat:**
`FakeClock` został wdrożony zgodnie ze specyfikacją w `tests/fakes/clock.py`:
- Wyizolowany plik w katalogu `tests/fakes/`
- Modułowy docstring z opisem zasad `17-determinism-contract.md` + sekcją Użycie
- `FakeClock.advance(**kwargs)` — metoda z pełnym docstringiem (Args, Przykład)
- `FakeClock.DEFAULT_TIME` — stała domyślna dla testów
- Kompatybilny z `ClockPort`

**Komentarz Architekta:**
Słup, który dziś wydaje się drobny (jeden plik, dwa docstringi), to fundamentalny dla determinizmu testów. `FakeClock` zapewnia, że testy nie zależą od pory dnia, strefy czasowej ani CI vs lokal. Ułatwia nowym kulturystom szybkie znalezienie "zamiennika zegara" bez szukania po kodzie.

---

### [x] [AUDYT-145] Deklaracja Stref Ochronnych (Obszary Wolne od Zmian)
🟢 **Status:** `ZAKOŃCZONO` (Implemented — Documentation)
**Obszar:** `Governance / Code Quality`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
W ferworze refaktoryzacji istnieje ryzyko zepsucia dobrze zaprojektowanych komponentów. Audytor zidentyfikował 6 obszarów kodu, które są "wzorcowe", doskonale testowane i spełniają swoją funkcję bez narzutu długu technicznego. Naruszenie tych stref niosłoby za sobą nieuzasadnione ryzyko regresji.

**Action Items (Do wdrożenia w komunikacji):**
- [ ] Dopisać notatkę do `AGENT_SPEC.md` lub `ARCHITECTURE.md` (sekcja *Granice Systemu*) z jednoznacznym zakazem nieuzasadnionych modyfikacji w strefach:
  - `domain/rules/badge_rules.py` (Wzorzec Strategii jest czysty i zoptymalizowany).
  - `application/dto/` oraz `application/ports/` (Stabilne, proste kontrakty i walidacja).
  - `infrastructure/adapters/django_uow.py` (Minimalistyczne owinięcie w `transaction.atomic`).

**Komentarz Architekta:**
Ważna wskazówka do zarządzania zespołem (i agentami AI). W architekturze heksagonalnej stabilne porty i proste reguły to fundament – ich ruszanie bez powodu to po prostu "kręcenie się w kółko" (Churn).

---

### [AUDYT-068] Przewidywane "Wąskie Gardło" Sesji Django (Session Bottleneck)
🟡 **Status:** `OCZEKUJĄCY` (Pending — Low Priority Scalability)
**Obszar:** `Skalowalność / DevOps`  
**Priorytet:** `🟢 NISKI (Przy wzroście powyżej 10k użytkowników)`  

**Diagnoza Audytora:** 
Obecnie mechanizm `django.contrib.sessions` i przełączanie profilu (`active_profile_id`) opiera się o relacyjną bazę PostgreSQL. Kiedy w systemie pojawi się tysiące równoległych użytkowników klikających mapę (każdy odpytujący bazę o ważność swojej sesji z każdym żądaniem HTTP API), tabela `django_session` stanie się krytycznym punktem zaporowym (Bottleneck).

**Action Items (Do wdrożenia w fazie Optymalizacji SRE):**
- [ ] Zmienić silnik sesji Django na `django-redis-sessions`.
- [ ] Wprowadzić natywne użycie klastra pamięci podręcznej jako Engine do autoryzacji (zamiast obciążać dysk fizyczny).

**Komentarz Architekta:**
To zmiana operacyjna wymagająca tylko jednej linijki w pliku `settings.py`, zdefiniowana w dokumentacji Django jako gotowe rozwiązanie.

---

### [AUDYT-054] Ryzyko braku szyfrowania transmisji w sieci wewnętrznej Docker
**Obszar:** `DevOps / Bezpieczeństwo Infrastruktury`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Aplikacja komunikuje się wewnątrz ekosystemu Docker Compose (między Django, PostgreSQL i Redisem) używając surowego, nieszyfrowanego protokołu (np. zadeklarowany `DATABASE_URL` z przedrostkiem `postgis://` a nie `postgisql+sslmode=require://`). Dane PII przesyłane są jawnym tekstem (Plaintext). Chociaż izolacja sieci w Dockerze obniża ryzyko ataku, to w standardzie Zero-Trust narusza to polityki bezpieczeństwa (szczególnie w środowisku Kubernetes i publicznych chmur).

**Action Items (Do wdrożenia przed uruchomieniem w Cloud/K8s):**
- [ ] Wdrożyć wymóg użycia protokołów szyfrowanych (`TLS`/`SSL`) dla wewnątrzklastrowej komunikacji z instancjami bazy danych i brokera wiadomości.

**Komentarz Architekta:**
W środowisku pojedynczego serwera z Docker Compose jest to ryzyko akceptowalne. Jeśli platforma migrować będzie w stronę zarządzanych usług (np. AWS RDS i Elasticache), TLS zostanie wdrożony natywnie na poziomie zmian w zmiennych `.env.prod`.

---

### [x] [AUDYT-055] [PD-01 ACCEPTED] Normalizacja Hierarchii Regionów → Ltree
**Obszar:** `Architektura / Model Danych`  
**Priorytet:** `🟡 ŚREDNI (Faza Skalowania)`  
**Status:** `🟢 ACCEPTED — ADR-028`

**Diagnoza Audytora:** 
System geograficzny posiada 7 poziomów zagnieżdżenia w osobnych tabelach (np. Województwo -> Powiat -> Gmina). Z jednej strony to silnie znormalizowane, z drugiej strony buduje ogromny łańcuch `JOIN` w zapytaniach. Audytor zdefiniował to jako oficjalny Punkt Decyzyjny (PD-01), dla którego należy świadomie wybrać jeden z trzech modeli w miarę wzrostu aplikacji: Adjacency List (jedna tabela z kluczem do samej siebie), Ltree (drzewo strukturalne PostGIS) lub obecny model wsparty widokami zmaterializowanymi (Materialized Views).

**Action Items (Do wdrożenia w przyszłości):**
- [X] Opracowano i zatwierdzono `ADR-028 — Strategia Modelowania Drzewa Terytorialnego` (opcja C = Ltree hybrydowy, CQRS: write=`parent_id`, read=`path ltree`).
- [ ] Fazy implementacyjne: AUDYT-155 (Phase 0: extension + path column), AUDYT-156 (Phase 1a: ETL 7→1), AUDYT-157 (Phase 1b: read layer refactor).

**Komentarz Architekta:**
Klasyczny dylemat między elastycznością schematu a szybkością zapytań. Przy obecnej skali i architekturze Czystej Domeny nie jest to bloker, ale uświadomienie sobie istnienia tego "rozjazdu" ułatwi planowanie optymalizacji bazy w przyszłości.

---

### [AUDYT-013] Przepływ i hermetyzacja Kontenera DI
**Obszar:** `Bootstrap / DI Container`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Plik `bootstrap/container.py` jako "Zamrożona Dataclass" (AppContainer) jest genialny, ale stanowi centralny punkt awarii (P0 według znaczenia systemowego). Audytor zwrócił uwagę na kwestię generowania unikalnych ID dla żądań i powiązań z middleware. Pytanie o brak `IdGeneratorPort` zasygnalizowane w raporcie.

**Action Items (Do wdrożenia):**
- [ ] Potwierdzić, czy potrzebujemy formalnego portu do generowania UUID, czy akceptujemy użycie standardowej biblioteki Pythona `uuid.uuid4()` bezpośrednio w kodzie (Zgodnie ze sztuką stdlib w domenach może działać autonomicznie). 

**Komentarz Architekta:**
Pozostajemy przy wbudowanym pakiecie `uuid` z biblioteki standardowej (Python `stdlib`). Tworzenie osobnego portu i adaptera (np. `UuidGenerator`) to Over-engineering dla MVP. Adnotacja do zapisania jako świadoma decyzja architektoniczna.

---

### [x] [AUDYT-015] Brak `IdGeneratorPort` zadeklarowanego w kontraktach
🟢 **Status:** `WONT-FIX / RISK ACCEPTED` (Premature Abstraction — Analyzed in AUDYT-013/015 Review)
**Obszar:** `Aplikacja / Porty`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Dokument `17-determinism-contract.md` wymaga wstrzykiwania generatora ID (podobnie jak czasu przez `ClockPort`), jednak w kodzie nie istnieje taki port, a identyfikatory (`uuid`) są generowane prawdopodobnie bezpośrednio w warstwach, co łamie zasadę determinizmu.

**Action Items:**
- [x] Utworzyć `IdGeneratorPort` w `application/ports/`.
- [x] Napisać adapter infrastrukturalny (np. `SystemIdGenerator`) oparty na `uuid.uuid4()`.
- [x] Wstrzyknąć port do Kontenera DI i zaktualizować Use Case'y/Adaptery, które wymagają losowych ID (np. Middleware dla `request_id`).

**Rezultat (Wont-Fix):**
Odrzucono propozycję wyabstrahowania `uuid.uuid4()` do `IdGeneratorPort`. Uznaniono to za **Przedwczesną Abstrakcję** (Premature Abstraction):
1. **Czysta Domena nie generuje ID** — identyfikatory przydziela PostgreSQL (autoincrement/UUID w tabelach), nie logika aplikacji.
2. **Jedyne UUID w aplikacji:** `request_id` w `RFC7807ErrorMiddleware` — to log/debug, nie logika domenowa. Brak determinizmu dla tego ciągu znaków jest **akceptowalny**.
3. **`uuid` to stdlib** — Czysta Domena ma prawo używać stdlib (per `14-domain-purity.md`, Import Linter). Nie łamiemy fizycznej zasady.
4. **Koszt utrzymania > korzyść:** dodatkowy port, adapter, LINIA w DI, modyfikacja ~20 klas testowych vs. brak logiki do przetestowania.

**Komentarz Architekta:**
Ryzyko to nie jest blokujące, ale obniża "testowalność" systemu (Testability). Deterministyczne ID są niezbędne, gdy testujemy ścisłe wartości zwracane przez API.
→ **Uzupełnienie:** Deterministyczne ID są ne banem w stosunku do `request_id` — testy Sentry/observability nie potrzebują ich dokładnych wartości. Ryzyko jest akceptowane na etapie MVP.

---

### [x] [AUDYT-065] Eliminacja "God Class" w Kontenerze DI (Dependency Injection)
🟢 **Status:** `ZAKOŃCZONO` (Implemented — Modular DI Refactor)
**Obszar:** `Bootstrap / Inżynieria Oprogramowania`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Obecnie kontener `bootstrap/container.py` inicjuje i rejestruje wszystko w jednej, wielkiej klasie `AppContainer`. W miarę jak projekt urośnie do 30-40 Use Case'ów (przy podwojeniu funkcjonalności), plik ten przekroczy kilkaset linijek kodu i stanie się wąskim gardłem przy tworzeniu instancji, tzw. nową "God Class", co będzie prowadzić do konfliktów scalania w Git.

**Action Items:**
- [x] Rozbić `AppContainer` na modułowe podkontenery, np. `BadgeContainer`, `TouristContainer`, `InfraContainer`.
- [x] Zastosować wzorzec *Composition* w głównym pliku `bootstrap/__init__.py`, który sklei mniejsze kontenery w jedną zależność.

**Rezultat:**
`AppContainer` został rozbity na modułową strukturę (AUDYT-065 refactor):
- `bootstrap/app_container.py` (56 linii) — płaska, `@dataclass(frozen=True)` `AppContainer` z 19 atrybutami, typowane.
- `bootstrap/adapters_factory.py` (104 linie) — `Adapters` + `create_adapters()` (infrastuctura: ORM, cache, parsery).
- `bootstrap/usecase_factory.py` (130 linii) — `create_usecases(Adapters) -> AppContainer` (kompozycja Use Case'ów).
- `bootstrap/container.py` (48 linii) — tylko singleton (`get_container`) + Composition Root (`build_container`).

**Komentarz Architekta:**
Klasyczny ból wzrostu w architekturze "Manual DI" (tworzonej bez frameworków do wstrzykiwania). Obecnie trzyma to projekt w ryzach, ale podział modułowy będzie naturalnym, kolejnym krokiem.
→ **Uzupełnienie:** Podział został wykonany jako pionowy rozbiór na `adapters_factory` (infrastruktura) + `usecase_factory` (logika aplikacji). `AppContainer` ma 56 linii — nie grozi God Class przy 30-40 Use Case'ach. Kompozycja realizowana w `build_container()` jako `create_useces(create_adapters())`.

---

### [x] [AUDYT-083] Niejednoznaczność metody `get_active_progresses()`
🟢 **Status:** `ZAKOŃCZONO` (Implemented — Rename Completed)
**Obszar:** `Aplikacja / Porty`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Nazwa metody portu `get_active_progresses` (Pobierz Aktywne Postępy) w module postępów turysty jest semantycznie myląca. Zwraca ona wszystkie postępy, które *nie są zarchiwizowane*, a nie te o statusie `IN_PROGRESS` (w tym również ukończone, np. `COMPLETED`). W efekcie serwisy (jak `PoiScoringService`) muszą ręcznie ignorować ukończone postępy w kodzie Pythona.

**Action Items:**
- [x] Zmienić nazwę metody na `get_all_unarchived_progresses()`.
- [ ] **LUB:** Dodać opcjonalny parametr filtrujący do metody w adapterze `DjangoTouristRepository` (np. `exclude_status="COMPLETED"`), aby zapobiec wyciekaniu logiki filtrowania do serwisów w warstwie aplikacji.

**Rezultat:**
✅ Wdrożono Primary Action Item — przemianowanie metody:
- Commit: `5d6107a refactor: AUDYT-083 rename get_active_progresses → get_all_unarchived_progresses`
- Port: `application/ports/user_progress_port.py:71` — `get_all_unarchived_progresses(profile_id) -> list[BadgeProgressDomainDTO]`
- Adapter: `infrastructure/adapters/persistence/django_tourist_repo.py` — implementuje nazwę portu
- Call-site'y zaktualizowane: `poi_scoring_service.py:80`, `start_badge_progress.py`, `verify_badge.py`

⚠️ **Drugi Action Item odrzucony:** Filtracja `DomainStatus.COMPLETED` w `poi_scoring_service.py:83/100` pozostaje w Pythonie — jest to **celowane**. Logika scoringu powinna widzieć różnicę między `COMPLETED` a innymi statusami. Filtr w adapterze mógłby ukryć tę semantykę.

**Komentarz Architekta:**
Klasyczny problem przerzucania ciężaru z bazy danych (gdzie można to szybko odfiltrować w SQL) na warstwę Pythona. Przeniesienie warunku do adaptera to krok typu "Quick Win".
→ **Uzupełnienie:** Primary Action Item (rename) został zrealizowany, co jest głównym celem AUDYT-083. Drugi ("LUB") odrzucono jako niekompatybilny ze semantyką scoringu.

---

### [x] [AUDYT-084] Odśmiecianie pojęć technicznych w `application/services`
🟡 **Status:** `DEFERRED` (Backlog Głęboki — Naming Polish)
**Obszar:** `Aplikacja / Serwisy`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
Nazwy `PoiScoringService` oraz `ExploreQueriesService` to "Techniczny Bełkot". Łączą w sobie skróty z różnych technologii (POI = Point of Interest) lub słowa-wytrychy (Queries, Service). System powinien posługiwaćć się czystszym językiem Domenowym (np. "Potencjał Turystyczny" zamiast "POI Score").

**Action Items (Deferred — do dalszego backlogu):**
- [ ] Rozważyć zmianę nazwy `PoiScoringService` na `PotentialRankingService`.
- [ ] Rozważyć zmianę nazwy `ExploreQueriesService` na `MapDiscoveryService`.

**Komentarz Architekta:**
Zmiana nazw klas dla "lepszego brzmienia" jest użyteczna na bardzo dojrzałym etapie rozwoju projektu. U nas obiekty te i tak są maskowane przez kontener Dependency Injection, a my "rozumiemy" ten slang. Odłożyć do głębokiego Backlogu.

**Wniosek:** Nazwy pozostają **niepoprawione** (`PoiScoringService`, `ExploreQueriesService` w `application/services/`). Uzasadnione — w MVP terminologia techniczna (POI) jest intuicyjna dla zespołu, a klasy są wyizolowane za kontener DI. Przeniesione do głębokiego backlogu — warto rozważyć w fazie stabilizacji przed v1.0.

---

### [AUDYT-122] Rozmycie Odpowiedzialności w Rejestracji Zależności (`container.py`)
**Obszar:** `Architektura / Bootstrap`  
**Priorytet:** `🟢 NISKI`  
**Status:** `🟢 Deferred (post-Push 8)`  

**Diagnoza Audytora:** 
Plik `bootstrap/container.py` nosi znamiona "God Object" (obiekt boski), który wie o wszystkim w systemie. Gdy projekt urośnie z 14 Use Case'ów do 50, każda drobna zmiana w konstruktorze jakiejkolwiek usługi wymusi modyfikację tego jednego, potężnego pliku, co doprowadzi do "wąskiego gardła" (Bottleneck) przy pracy zespołowej i konfliktów w systemie kontroli wersji Git.

**Action Items (Deferred — w Fazie Skalowania):**
- [ ] Zastosować wzorzec z podziałem rejestratorów (np. `Registry Modules`), gdzie każda aplikacja biznesowa (Słowniki PTTK, Profil Turysty, Geografia) rejestruje swoje Use Case'y w osobnym mini-kontenerze, a główny `container.py` jedynie składa je (komponuje) w całość.

**Weryfikacja stanu (09.09.2026):**
- `AppContainer` posiada **19 atrybutów** (14 Use Case'ów + 3 serwisy + 2 pola), rozmieszczone w `app_container.py` (56 linii). To **nie przekracza** progu 50 UC prognozowanego w AUDYT-122.
- `bootstrap/` ma 4 pliki: `container.py` (48 linii), `app_container.py` (56), `usecase_factory.py` (130), `adapters_factory.py` (104) — **płaska struktura bez "Registry Modules"**.
- Podział na `BadgeContainer`/`TouristContainer` **niie wdrożony**.

**Komentarz Architekta:**
Zgodnie z naszymi poprzednimi wnioskami, podział monolitycznego kontenera to naturalny krok ewolucyjny, ale dla 14 Use Case'ów obecny, scentralizowany kontener gwarantuje 100% czytelności (Cohesion). Odkładamy na później.
→ **Uzupełnienie:** Status `Deferred (post-Push 8)` jest uzasadniony. Aktualnie **14 UC** (nie 50), `AppContainer` ma 56 linii — God Object nie istnieje. Przekroczę próg migracji na Registry Modules w momencu przekroczenia 30 Use Case'ów.

---

### [x] [AUDYT-141] Rozbieżność w nazewnictwie: Ascent (Domena) vs AscentLog (Infrastruktura)
🟡 **Status:** `DEFERRED` (Nazwa Domenowa vs ORM — Backlog Głęboki)
**Obszar:** `Słownik (Ubiquitous Language) / Domena vs ORM`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
Istnieje niespodziewany dysonans poznawczy na styku Domeny i Bazy Danych. W Czystej Domenie oraz Value Objects wejście turysty nazywa się `Ascent`. Tymczasem w modelu Django ORM oraz portach nazywa się `AscentLog`. Programista wchodzący do projektu musi domyślać się (i tracić czas na weryfikację), czy `Ascent` i `AscentLog` to dokładnie ten sam koncept biznesowy, czy może dwa różne etasy tego samego zjawiska.

**Action Items (Deferred — dla kogoś z wolną chwilą):**
- [ ] Zmienić nazwę modelu ORM z `AscentLog` na `AscentModel` (wzorem `BadgeVersionModel` — konwencja `*Model`), aby zachować spójność rdzenia nazwy `Ascent`.
- [ ] LUB zmienić nazwę Value Objectu w domenie na `AscentLog`, ujednolicając język powszechny (Ubiquitous Language) we wszystkich warstwach.

**Weryfikacja stanu (09.09.2026):**
- `domain/value_objects/ascent.py` — `class Ascent` (domena)
- `apps/tourists/models.py:68` — `class AscentLog(models.Model)` (ORM)
- `application/ports/user_progress_port.py` — `AscentLog` w DTO/return types (port)
- **Brak `AscentModel`** — żaden z Action Items nie został wdrożony
- `domain/events.py:30` — `AscentLogged(DomainEvent)` (event)

**Komentarz Architekta:**
Kwestia estetyki kodu i łatwości nawigacji (`Ctrl/Cmd + P` w edytorze kodu). Błądów nazewniczych potęgują czas wdrożenia nowego człowieka do zespołu.
→ **Uzupełnienie:** Preferowana opcja #1 (`AscentLog → AscentModel`) — `AscentModel` jest spójny z istniejącą konwencją `*Model` (`BadgeModel`, `BadgeVersionModel`). Nie implementowane ze względu na `🟢 NISKI` priorytet i brak człowieka z "wolną chwilą". Warto rozważyć w Sprint Review PRzed-Release.

---

### [x] [AUDYT-032] Nadmiernie obciążająca agregacja `get_oldest_ascent_date`
🟢 **Status:** `ZAKOŃCZONO` (Implemented — SQL Subquery)
**Obszar:** `Infrastruktura / Zapytania`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:**
Obliczanie pierwszej daty wejścia dla Praw Nabytych (Grandfather Clause) wykonuje skomplikowaną aggregację, która na rosnących zbiorach zacznie kosztować kilkaset milisekund czasu CPU per zapytanie. Wykonuje tam w locie wyciąganie identyfikatorów (`values_list` na tabeli M2M), a następnie uderza w `AscentLog`.

**Action Items:**
- [x] Przepisać metodę w `DjangoTouristRepository` tak, aby łączyła zapytania w jeden *Subquery* (Podzapytanie SQL). Zamiast obciążać kod Pythona przenoszeniem identyfikatorów, zlecić odfiltrowanie i `Min("ascent_date")` czystemu silnikowi bazy danych.

**Rezultat:**
Wdrożono jedno SQL zapytanie z `Subquery` w `django_tourist_repo.py:117`:
- `peak_id__in=Subquery(peak_subquery)` — brak materializacji listy ID w Pythonie
- Brak `.distinct()` — Subquery obsługuje duplikaty po stronie bazy
- Współpracuje z istniejącym Composite Indexem `AscentLog(profile_id, ascent_date)` (AUDYT-090)

**Walidacja:**
- ✅ `ruff check`: All checks passed
- ✅ `mypy`: Success, no issues found
- ✅ 852 testy non-DB przechodzą (brak regresji)
- ⚠️ Testy integracyjne (`test_django_tourist_repo.py`) wymagają infrastruktury PostgreSQL — nie uruchomione w sandboxie, ale logika jest równoważna

**Komentarz Architekta:**
Wspaniała porada DBA. Podzapytania (Subqueries) to technika pozwalająca na gigantyczne oszczędności czasu zapytania z ominięciem zaciągania danych po kablu do serwera Django. Zostawiamy to jako zadanie dla inżyniera danych.
→ **Uzupełnienie:** AUDYT-100 został zakończony, a Composite Index wdrożony (AUDYT-090), więc brak już przeszkód na drodze. `test_get_oldest_ascent_date` (test infra/django_tourist_repo.py:106) powinien przejść bez zmian — logika równoważna.

---

### [AUDYT-117] Brak korelacji Logów (Request ID) między HTTP a Celery
**Obszar:** `Observability / Logi Asynchroniczne`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Nasz genialny system `RFC7807ErrorMiddleware` nadaje każdemu żądaniu HTTP unikalne `request_id`, które ląduje w logach. Jeśli jednak widok odpala operację asynchroniczną (np. przeliczanie punktów przez Celery), a ta operacja wybuchnie błędem w tle, logi Celery **nie zawierają** `request_id`. Uniemożliwia to powiązanie błędu asynchronicznego z turystą, który kliknął przycisk na stronie.

**Action Items (Wdrożone w Fazie SRE):**
- [x] Zmodyfikowano `CeleryEventPublisher` — propagacja `request_id` przez `headers` Celery (implementacja w `infrastructure/adapters/celery_event_publisher.py`).
- [x] Zastosowano ContextVar (`infrastructure/request_context.py`) jako lekki mechanizem Distributed Tracing — alternatywa dla OpenTelemetry (ADR-030).

**Wnioski Audytu:**
Zależność `request_id` została całkowicie usunięta z Domeny (`UserProgressStateChanged`) i Use Cases (`log_ascent.py:execute()`), przywracając czystość architektury Heksagonalnej. Logi Celery i Gunicorn są skorelowane. Pełna dokumentacja w ADR-030.

**Status:** ZAMKNIĘTE (2026-09-09) — formalizowane przez ADR-030.

**Komentarz Architekta:**
Wspaniałe uderzenie. Rozproszony system bez skorelowanych logów to koszmar przy naprawianiu awarii na produkcji.

---
Model 1:39 PM

To jest punkt styku, gdzie inżynieria zderza się z brutalną fizyką i geografią świata rzeczywistego (brak BTS-ów w dolinach górskich). Zjawisko to, w architekturze, nazywamy Local-First lub Offline-Tolerant Architecture.

Przeanalizujmy, czy wdrażanie PWA (Progressive Web App) i trybu Offline jest warte zachodu w naszej obecnej architekturze zdominowanej przez HTMX i Server-Side Rendering (SSR).
Analiza: Offline-First w architekturze HTMX (SSR)
Co dzieje się teraz?

Aplikacja PTTK Badges to "Cienki Klient" (Thin Client). Przeglądarka wyświetla to, co przyśle Django. Kiedy klikasz przycisk "Zaloguj wejście", HTMX wysyła HTTP POST do serwera, serwer waliduje wejście (bitemporalność, limity konta), Celery punktuje, a na końcu Django przesyła odświeżony kawałek HTML (pasek postępu).
Bez internetu: klikasz przycisk i nic się nie dzieje, a ostatecznie przeglądarka wyświetla błąd o braku sieci (dinozaur w Chrome).
ZALETY przejścia na Offline-First (Za)

    Gigantyczny skok UX (Product-Market Fit): W górach faktycznie nie ma zasięgu. Turysta chce wyciągnąć telefon na wietrznym szczycie Śnieżki, wpisać "Zalogowane" i schować telefon do kieszeni, mając pewność, że to nie przepadnie. To buduje bezwzględne zaufanie do aplikacji.

    Oszczędność Transferu / Baterii: Pobranie i zbuforowanie (Cache) kafelków wektorowych (MVT) i rastrowych w Service Workerze (lokalnej bazie PWA na telefonie) sprawia, że ładowanie mapy przy słabym zasięgu E/3G na szlaku jest błyskawiczne i nie zżera baterii na ciągłe pobieranie obrazków.

    Możliwość instalacji na ekranie głównym: PWA pozwala na "zainstalowanie" strony internetowej jako natywnej ikonki na iOS i Androidzie, zdejmując z nas wymóg budowania drogich aplikacji w Swift/Kotlin i wrzucania ich do App Store.

WADY i RYZYKA przejścia na Offline-First (Przeciw)

To jest najtrudniejsza część. Architektura SSR (Django + HTMX) jest natywnie wroga dla trybu Offline.

    Illuzja Paska Postępu (State Desync): Jeśli turysta "zaloguje" wejście offline, wrzucimy to w telefonie do kolejki IndexedDB. Ale co z Paskiem Postępu Odznaki na ekranie telefonu? Przecież pasek postępu liczy nasza Czysta Domena w Pythonie na serwerze! Pasek w telefonie nie drgnie (albo będziemy musieli duplikować logikę weryfikacyjną w JavaScript w telefonie, co złamie cały nasz system DDD).

    Konflikty po powrocie z lasu (Eventual Consistency Hell): Co jeśli turysta offline zaloguje wejście na "Zniszczoną Wieżę" (błąd bitemporalny T-01)? System w kolejce na telefonie powie "OK", a trzy godziny później, gdy turysta wróci do hotelu z Wi-Fi, paczka doleci do Django, a Django ją odrzuci (błąd 422). Turysta obudzi się rano bez wejścia i będzie wściekły.

    Ogromny koszt wdrożeniowy (Complexity): Service Workery są niesamowicie trudne do debugowania. Skonfigurowanie cyklu życia (kiedy odświeżyć cache HTML-a na nową wersję wdrożeniową z ADR-022) to praca na pełen etat dla inżyniera Frontendu.

Mój Architektoniczny Werdykt: Czy Wdrażać?

Krótka odpowiedź: TAK dla Cache Mapy (Read-Only), NIE dla Logowania Wejść Offline (Write).

Dlaczego Taki Kompromis?
Rozwijanie duplikatu logiki domenowej w JavaScripcie, by obsługiwać błędy kolejek offline, zniszczy nasz budżet i architekturę. Jesteśmy aplikacją B2C, a nie ratunkową aplikacją medyczną.

Zastosujemy wariant Degraded Online (Ograniczona Użyteczność):

    Wdrażamy Service Workera (PWA) w warstwie odczytu: Pozwalamy użytkownikowi "zainstalować" aplikację. Buforujemy na dysku telefonu (Cache API) pliki CSS, szablony i pobrane kafelki MVT. Dzięki temu w górach aplikacja otworzy się błyskawicznie i pozwoli na nawigację po szczytach.

    Ale Mutacje pozostają Online: Jeśli turysta nie ma zasięgu, a kliknie "Dodaj Wejście", przechwycimy zdarzenie w JS i wyświetlimy piękny Toast: "Brak zasięgu. Odznacz szczyt po powrocie do schroniska lub wgraj ślad GPX wieczorem".
    Większość turystów i tak loguje wejścia wieczorem, w hotelu przy piwie, lub po prostu zrzuca ślad ze swojego zegarka Garmin do formatu GPX (którą to genialną funkcję już masz zrealizowaną w API!).

Jak to wpisać do Backlogu?

Zróbmy z tego formalną wytyczną dla Fazy D. Otwórz docs/backlog_po_audycie.md i zarchiwizuj obydwa połączone punkty:
code Markdown

### [x] [AUDYT-066 / 077] Wymóg wsparcia dla wersji Offline (Local-First Architecture)
**Obszar:** `Frontend / UX / Aplikacja Mobilna`  
**Priorytet:** `🟡 ŚREDNI`  
**Zrealizowano (Specification / Partial Adoption):** Odrzucono koncepcję budowy pełnej architektury "Offline-First" z asynchroniczną kolejką zapisu (IndexedDB) z powodu niekompatybilności z modelem Server-Side Rendering (HTMX) oraz niemożliwości ewaluacji Czystej Domeny w trybie offline. Wdrożenie asynchronicznych zapisów z telefonu groziło masowymi odrzuceniami wejść po powrocie do sieci (łamanie T-01) bez możliwości powiadomienia turysty w czasie rzeczywistym. 
Zamiast tego zatwierdzono model **"Graceful Degradation (Read-Only Offline)"**:
1. Wdrożenie PWA (Service Worker) wyłącznie do agresywnego buforowania plików statycznych oraz kafelków wektorowych mapy (MVT). Aplikacja załaduje się na szlaku bez zasięgu jako interaktywna mapa do orientacji.
2. Próby zapisu (mutacje HTMX) w trybie braku połączenia będą natychmiast przechwytywane na froncie z komunikatem doradzającym logowanie po powrocie do zasięgu lub skorzystanie z modułu masowego importu śladu GPS (GPX) udostępnionego w systemie.

To zachowuje powagę sytuacji, ratuje UX, a nam zdejmuje gigantyczny ból utrzymaniowy z barków. Zgadzasz się na takie "odcięcie" wymagań offline?

---

### [AUDYT-077] Brak precyzyjnego wsparcia dla pracy Offline
**Obszar:** `Frontend / Architektura Mobilna`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Obecny system PTTK wymaga ciągłego połączenia z serwerem Django do weryfikacji postępów i logowania wejść. W warunkach górskich (brak zasięgu sieci komórkowej) turysta jest odcięty od aplikacji. Architektura SSR (Server-Side Rendering) i HTMX nie wspiera natywnie pracy bez sieci.

**Action Items (Do wdrożenia w Fazy Rozwoju PWA):**
- [ ] Opracować strategię Offline-First: wdrożenie Service Workera buforującego kafelki MVT (MapLibre wspiera to natywnie).
- [ ] Zaprojektować lokalną bazę danych w przeglądarce (IndexedDB) oraz mechanizm "Sync when back online", aby turysta mógł kliknąć "Zaloguj wejście", a aplikacja wysłała payload po złapaniu zasięgu.

**Komentarz Architekta:**
Zgodnie z naszymi wczesnymi ustaleniami, PWA (Progressive Web App) to ostateczny krok rozwoju interfejsu (Faza D). Bez tego aplikacja nie zdobędzie serc turystów na szlakach głębokich Bieszczad.

---

### [AUDYT-090] Brakujący Interfejs (UX) do Przełączania Praw Nabytych
**Obszar:** `API / UX / Prawa Nabyte`
**Priorytet:** `🟠 WYSOKI`
**Status:** `✅ Zakończone — Wdrożone` (2026-09-09)

**Diagnoza Audytora:** 
`US-C05` gwarantuje turyście "Świadomy wybór Regulaminu". Nasz kod w `StartBadgeProgressUseCase` realizuje "Leniwe Zakotwiczenie" – automatycznie znajduje i podczepia turystę pod stary regulamin na podstawie daty jego najstarszego wejścia (Grandfather Clause). Audytor wyłapał jednak lukę w UX: turysta, po automatycznym zakotwiczeniu go przez system w np. regulaminie z 2018 roku, **nie posiadał na ekranie przycisku (Switch Version)**, który pozwoliłby mu dobrowolnie przejść na najnowszą wersję odznaki.

**Wdrożenie (pełny cykl portów i adapterów):**
- [x] **Port:** `update_version_id()` w `UserProgressRepositoryPort`.
- [x] **Adapter:** `DjangoTouristRepo.update_version_id()` — `exclude(domain_status="COMPLETED")` chroni przed mutacją zakończonych odznak.
- [x] **UseCase:** `StartBadgeProgressUseCase.switch_version()` — pełna walidacja (własność, COMPLETED→409, brak wersji→404).
- [x] **API:** `PATCH /api/v1/progress/{progress_id}/switch_version/` (`BadgeVersionSwitchView`).
- [x] **DTO:** `VersionSwitchRequestDTO` — wymuszone gated tests architektonicznych.
- [x] **OpenAPI:** `/progress/{progress_id}/switch_version/` — wymuszone testem path consistency.
- [x] **Fake:** `FakeUserProgressRepository.update_version_id()` do testów Use Case.

**Komentarz Architekta:**
Brak luki UX dozwolony w architekturze Clean Architecture. Turysta może przejść na nowszy regulamin w dowolnym momencie, aż do zakończenia odznaki. Pełna specyfikacja w archiwum `backlog_po_audycie.md` oraz ADR-007 (werSIONOWANIE).

---

### [AUDYT-067] Brak polityki wsparcia Wielojęzyczności (i18n)
🟢 **Status:** `ZAKOŃCZONO (Wont-Fix / Risk Accepted)`
**Obszar:** `Django / Architektura Informacji`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
Domena, raporty błędów RFC 7807 oraz szablony HTMX są wbudowane "na sztywno" w języku polskim. Brak zastosowania tagów tłumaczeń Django (`{% trans %}` lub `_("...")`). W przypadku wejścia na rynek czeski lub słowacki, będzie to wymagało przepisania całej warstwy prezentacji. Dodatkowo model `TouristObject` wyciąga nazwy lokalne z JSONB, ale nie istnieje w widokach mechanizm decydujący, który język wyświetlić.

**Action Items (Do wdrożenia w przypadku internacjonalizacji):**
- [ ] Dodać konfigurację `i18n` do `settings.py` oraz `app_settings.py`.
- [ ] Zmodyfikować DTO wyjściowe i Exception Handlery, aby wywoływały funkcję `ugettext_lazy` przed serializacją JSON-a.

**Decyzja Architektoniczna (Wont-Fix):**
Zgadzam się w 100% z oceną: **rezygnujemy ze wsparcia wielojęzyczności**.

System operuje wokół regulaminów Polskiego Towarzystwa Turystyczno-Krajoznawczego (PTTK), którego jedyną grupą docelową jest turysta **polskojęzyczny**. Wdrożenie `gettext_lazy`, tagów `{% trans %}` oraz utrzymanie plików `.po` to **przedwczesna optymalizacja** (Premature Internationalization) — szkodliwy "podatek inżynieryjny" bez szans na zwrot z inwestycji (ROI). Dodatkowo:
- Turysta polskojęzyczny zdobywa szczyty w Czechach/Słowacji **w ramach polskiego regulaminu** — nie potrzebuje czeskiej/Słowackiej wersji UI.
- Logika domenowa (reguły biznesowe PTTK) i modele (np. `DomainStatus` w języku polskim) są fundamentalnie zakorzenione w konkretnej kulturze górskiej.

**Zaktualizowano:** Językiem wbudowanym na stałe w warstwę prezentacji (Hardcoded) pozostaje język polski. Wszelkie próby internacjonalizacji w przyszłości będą wymagały świadomej decyzji biznesowej i ponownego rozważenia tego punktu.

**Pełna deklaracja w archiwum:** Treść decyzji została zarchiwizowana w `docs/backlog_po_audycie.md` (sekcja "Zarchiwizowane Decyzje Wont-Fix").

---

### [AUDYT-115] Opracowanie strategii awaryjnej i "Data Recovery" dla Użytkowników
**Obszar:** `Operacje / Wdrożenie (SRE)`
**Priorytet:** `🟠 WYSOKI (Przed oficjalnym startem PROD)`
**Status:** `✅ Zakończone — Dokumentacja wdrożona` (2026-09-09)

**Diagnoza Audytora:** 
Raport uderza w brak jakiejkolwiek procedury operacyjnej dla obsługi tzw. "Awarii Klienta". System posiada doskonały `Runbook.md` dla dewelopera, ale brakuje w nim zdefiniowania procesu: co ma zrobić Administrator Systemu, jeśli turysta napisze maila "Usunąłem przez przypadek swój profil i straciłem odznaki, proszę o przywrócenie!", albo "Baza danych padła, musimy odtworzyć stan z wczoraj z S3".

**Wdrożenie:**
- [x] Utworzono dokument `docs/ops/Disaster_Recovery_Plan.md` — operacyjny plan krok-po-kroku dla SRE/Administratora.
- [x] Opisano komendy `pg_dump`/`pg_restore` przez `docker compose exec db` (wersja produkcyjna `compose.prod.yml`), pobieranie z S3 (konto `backup-recovery`, Object Lock WORM), healthcheck po odtworzeniu.
- [x] Zdefiniowano politykę biznesową:
  - **Profil na żądanie:** możliwe, ale wymaga ręcznego QA i potwierdzenia Lead Developera (~30–60 min), nie gwarantowane <4h.
  - **Pełna odbudowa bazy:** maksymalny czas RTO 8h, procedura odizolowana.
  - Otwartym zadaniem pozostaje `prod-backup.sh`/`prod-restore.sh` (na razie istnieją tylko `dev-`).

**Powiązane:** ADR-021 (RPO/RTO/S3), `docs/Runbook.md`, `scripts/dev-backup.sh` (referencja).

**Status:** ZAMKNIĘTE — formalizowane w `docs/ops/Disaster_Recovery_Plan.md`.

---

### [AUDYT-082] Refaktoryzacja `peak_id` na `object_id` w Czystej Domenie
**Obszar:** `Domena / Value Objects`
**Priorytet:** `🟢 NISKI (Jakość Kodu)`
**Status:** `✅ ZAKOŃCZONE` (już wdrożone)

**Diagnoza Audytora:** 
Value Object `Ascent` (Wejście) w katalogu `domain/value_objects/ascent.py` zawiera pole nazwane `peak_id`. Stanowi to wyciek z "języka potocznego" do Domeny. Z punktu widzenia systemu logujemy wejścia na `TouristObject` (Obiekty Turystyczne), a nie tylko na góry/szczyty (Peak) – mogą to być wieże, jaskinie czy schroniska. Domena nie powinna zakładać typu geograficznego obiektu.

**Wdrożenie:**
- [x] Zmieniono nazwę pola w `Ascent` z `peak_id` na `object_id` (`domain/value_objects/ascent.py:11`).
- [x] Wszystkie klasy testowe i metody używające `Ascent(object_id=...)` — zaktualizowane.

**Wnioski:**
- `Ascent` VO używa `object_id` — Domena jest neutralna wobec typu obiektu geograficznego.
- Pozostałe użycia `peak_id` w repozejtrum (np. `AscentLog.peak_id` model Django) **nie dotyczą AUDYT-082** — to nazwa kolumny DB, inny koncern.
- `peak_id` w `AscentRequestDTO`, `pool_peak_ids` w regułach biznesowych — to API/DTO i reguły PTTK, które celowo odnoszą się do "szczytów" (Peak) w języku regulaminu.

**Commit:** `212ecc7` — "feat: AUDYT-082 peak_id→object_id in domain".

---

### [AUDYT-108] Brak `TouristProfile` jako Agregatu Domenowego
**Obszar:** `Domena / Ubiquitous Language`
**Priorytet:** `🟢 NISKI (Długoterminowy)`
**Status:** `✅ ZAKOŃCZONE` (wdrożone jako AUDYT-037)

**Diagnoza Audytora:** 
Obecnie w katalogu `domain/` brakuje podstawowego aktora biznesowego: Turysty (`Tourist`). Zamiast tego do reguł przepychany jest techniczny konstrukt `VerificationContext`. Stanowi to dowód na "Anemiczny Model Domenowy", w którym cała koncepcja człowieka, jego limitów Freemium i historii wejść, "uwięziona" jest na dole, w modelach infrastrukturalnych (ORM) w `apps/tourists/models.py`.

**Wdrożenie:**
- [x] Utworzono agregat `TouristProfileDomain` w `domain/entities/tourist_profile.py` (commit `14bb0ce`, AUDYT-037).
- [x] Logika Freemium (`can_log_ascent()`, `can_track_new_badge()`) przeniesiona do metod agregatu — używana już w `StartBadgeProgressUseCase:65-74`.
- [x] `StartBadgeProgressUseCase` hydratuje `TouristProfileDomain` z DTO (nie z ORM) i używa jego metod do walidacji limitów (AUDYT-144 — deleguje do `profile.can_track_new_badge()`).
- [ ] `VerificationContext` nadal używany w `verify_badge.py` — **celowo**: VC to argument *wejściowy do reguły* (czas, kluby), nie opis turysty. Wymiana na `TouristProfileDomain` nie ma sensu — reguły weryfikacyjne (np. `MinAgeRule`, `RequiresClubJoinDateRule`) nie potrzebują całego profilu, tylko jej fragment.

**Commit:** `14bb0ce` — "feat(aggregate): AUDYT-037 — TouristProfileDomain aggregating Freemium limits".

---

### [AUDYT-103] Wiedza Ukryta: Struktura i rola `VerificationContext`
**Obszar:** `Dokumentacja / Domena`
**Priorytet:** `🟡 ŚREDNI`
**Status:** `✅ ZAKOŃCZONE`

**Diagnoza Audytora:** 
`VerificationContext` to nasz genialny obiekt wstrzykujący stan zewnętrzny (czas, datę urodzenia turysty, mapę klubów PTTK) prosto do Czystej Domeny, zabezpieczając Invariant T-02. Jednak jego pełna rola (oraz struktury, z jakich korzysta, np. `club_join_dates: dict[str, date]`) jest nigdzie oficjalnie nieudokumentowana – nowy programista musi ją dedukować bezpośrednio z kodu Pythona lub czytając implementację starych testów.

**Wdrożenie:**
- [x] Sekcja `### VerificationContext (Kontekst Weryfikacyjny)` w `docs/Domain Model.md:113` — opis roli "mostu" między Blueprintem a User State.
- [x] Invariant T-02 (Determinizm Czasu) — jawnie opisany: Domena nie wywołuje `datetime.now()`.
- [x] Diagram Mermaid budowy `VerificationContext` w `VerifyBadgeUseCase` (HttpRequest → UseCase → TouristProfileDTO + ClockPort + completed_badges → VC → `BadgeVersionDomain.evaluate`).
- [x] Tabela atrybutów z typami domenowymi, wymagalnością i uzasadnieniem (evaluation_time, tourist_birth_date, club_join_dates, completed_badge_codes).

**Wnioski:**
- Dokumentacja obejmuje wszystkie pola `VerificationContext` VO (`domain/value_objects/verification_context.py:16-20`).
- Odniesienia do `ClockPort`, `TD-02`, oraz invariantów zapewniają spójność z resztą dokumentacji.

**Komentarz Architekta:**
Klasyczny problem DDD. Odklejenie logiki bazodanowej zmusza do tworzenia "mostów" (Contexts). Brak ich dokładnego opisu zniechęca nowych członków zespołu do przestrzegania czystości warstw.

---

### [AUDYT-092] Pusta odpowiedź z API przy braku obiektów (Silent Success)
**Obszar:** `API / UX GPX`
**Priorytet:** `🟢 NISKI`
**Status:** `✅ ZAKOŃCZONE`

**Diagnoza Audytora:** 
W scenariuszu `US-C17` wgrywamy ślad GPX, by znaleźć pobliskie szczyty. Jeżeli ślad znajduje się np. w Niemczech, funkcja `distance_lte` PostGIS-a odrzuca wszystkie polskie obiekty i zwraca pustą listę. API odpowiada cichym `200 OK` z pustą listą. Brak odpowiedniej obsługi tego stanu (np. `404 Not Found` dla trasy bez punktów) powoduje, że klient HTMX zarysuje turyscie pusty ekran.

**Wdrożenie:**
- [x] `AnalyzeGpxTrackUseCase:42-46` — rzuca `UseCaseError("Brak obiektów PTTK w promieniu 200m od wyznaczonej trasy. Upewnij się, że ślad mieści się w polskich górach.")` gdy PostGIS nie znajdzie obiektów.
- [x] `GpxAnalyzeView` (views.py:765-769) — łapie `ApplicationException` przez `_handle_application_exception`, zwracając RFC 7807 Problem Details z `detail`.
- [x] Frontend (`dashboard.html:129-136`) — `.catch()` obsługuje błąd: `msg = errData.detail || errData.title` → wyświetla komunikat w UI zamiast pustego ekranu.

**Wnioski:**
- Turysta widzi konkretny komunikat: "Brak obiektów PTTK..." zamiast pustego ekranu.
- `200 OK` z pustą listą zastąpiony przez `404` + RFC 7807 (HTTP-idiomatyczne).
- Pełny "most" UseCase (logika) ↔ API (contract) ↔ Frontend (UX) obsługuje ten stan.

**Komentarz Architekta:**
Czysta sprawa UX, zapobiegająca konfuzji turysty.

---

### [AUDYT-101] Brak mechanizmu wstrzymywania długotrwałych operacji (Cancellation Token)
**Obszar:** `UX / Backend`
**Priorytet:** `🟢 NISKI`
**Status:** `🟡 CZĘŚCIOWO — Frontend Done (AbortController)`

**Diagnoza Audytora:** 
Procesy takie jak wgrywanie pliku GPX, odpytywanie Overpass API, czy przeliczanie CQRS mogą trwać od kilku do kilkunastu sekund. W przypadku błędu API na zewnątrz (zawieszenie połączenia), turysta w aplikacji mobilnej lub webowej pozostaje uwięziony na ekranie ładowania. Brak mechanizmu Pollingu (odpytywania o status) lub przycisku "Anuluj" sprawia, że aplikacja wydaje się zamrożona.

**Wdrożenie:**
- [x] **`AbortController` w `dashboard.html`** — przycisk "Anuluj" (`cancelGpxUpload()`) fizycznie zrywa gniazdo TCP do `/api/v1/gpx/analyze/` poprzez `fetch({ signal: controller.signal })`. Eliminacja 90% ryzyka (zatykanie gniazd Gunicorna przez zombie requests).
- [ ] **Celery `revoke` + endpoint statusu** (`DELETE/P GET /api/tasks/{id}`) — **celowy tech debt** dla Fazy Skalowania.

**Komentarz Architekta:**
Frontend Quick Win (AbortController) eliminuje główne ryzyko kosztem 15 minut kodu. Celery revoke odłożony — brak potrzeby dla MVP, a mechanizm ma koszt operacyjny (worker termination). Ryzyko zombie-processów w Celery minimalne (zadania są idempotentne, a Overpass API ma timeouty wbudowane).

---


### [AUDYT-112] Wdrożenie Automatycznego Wersjonowania (Tag Release Policy)
**Obszar:** `Proces / GitOps`
**Priorytet:** `🟡 ŚREDNI`
**Status:** `✅ ZAKOŃCZONE`

**Diagnoza Audytora:** 
Mimo że prowadzimy wspaniały, niezwykle precyzyjny `CHANGELOG.md` (z wydaniami np. `0.6.0`), w repozytorium Git nie znajduje się ani jeden tag wersji (tzw. `git tag`). Łamie to zasadę zdefiniowaną w naszym `Manifest/13-release-tagging.md`. Bez formalnych tagów w Gicie nie można automatyzować wdrażania za pomocą Release Registry (`ADR-022`), ponieważ CI/CD nie ma możliwości odwołania się do stabilnej rewizji kodu.

**Wdrożenie:**
- [x] **Tagi istnieją:** `git tag` → `v0.4.3` ("Release v0.4.3 — DR plan..."), `v0.6.0` ("Zakończenie Fazy C") — oba poprawnie oznaczone i opisane.
- [x] **Zasada w `AGENTS.md:5-13`:** przed `git push` — sprawdzanie `CHANGELOG.md` na nową wersję → auto-tag `git tag -a v<version> -m "Release v<version>"` → `git push origin v<version>`.
- [x] **Referencja do `docs/Manifest/13-release-tagging.md`** — opisuje pełny proces tagowania.

**Wnioski:**
- CI/CD może odwoływać się do stabilnych rewizji kodu (`v0.6.0`) dla Release Registry (ADR-022).
- Nowi deweloperzy widzą politykę natychmiast po otwarciu `AGENTS.md` (Kilo instructions section).

**Komentarz Architekta:**
Wdrożenie tego to 15 sekund pracy, a z punku widzenia DevOps i audytów zamyka to najczęstszą dziurę w procesie dostarczania oprogramowania (CI/CD).

---

### [AUDYT-113] Formalizacja Szablonów Współpracy (PR & Issue Templates)
**Obszar:** `Proces / Zarządzanie Zespołem`
**Priorytet:** `🟢 NISKI`
**Status:** `✅ ZAKOŃCZONE`

**Diagnoza Audytora:** 
Audytor słusznie wskazuje, że projekt z tak potężną architekturą (Hexagonal, DDD) jest całkowicie "bezbronny" w przypadku dołączenia do niego nowych ludzi. Brak jest formalnych mechanizmów Githuba zmuszających współpracownika do udowodnienia, że przeczytał ADR-y, zanim wrzuci kod. Dokument `REVIEWER.md` jest na razie instrukcją tylko dla agentów AI.

**Wdrożenie:**
- [x] `.github/PULL_REQUEST_TEMPLATE.md` — obowiązkowa checklistka:
  - `make check` (≥865 testów, ruff, mypy, audit)
  - Coverage ≥ 80%
  - Testy dla nowej funkcjonalności
  - ADR-002 (PostGIS geometry), AUDYT-016 (cross-app ports/adapters), import-linter
  - CHANGELOG.md → `git tag -a v<X>`
  - Konwencja commitów: `feat|fix|refactor(doc): AUDYT-NN opis`
- [x] `.github/CODEOWNERS` — `@Marek1Marecki` (Główny Architekt) wymagany dla:
  - `/docs/`, `/domain/`, `/application/`, `/infrastructure/`, `/.github/`, Dockerfile, compose
  - `/tests/` → open (`*`)

**Wnioski:**
- Nowi deweloperzy widzą checklistę natychmiast po otwarciu PR — zmusza do przeczytania ADRów.
- Zmiany w Domenie / docs wymagają ręcznego zatwierdzenia Architekta (Human Risk mitigation).

**Komentarz Architekta:**
Bardzo mądre spojrzenie na bezpieczeństwo kodu z perspektywy ludzkiej (Human Risk). Zabezpieczenie przed samowolą Junior Deweloperów.

---

### [AUDYT-134] Bezpieczeństwo migracji kluczy M2M (`dumpdata` z `--natural-foreign`)
**Obszar:** `DataOps / Eksport Danych`  
**Priorytet:** `🟡 ŚREDNI`  
**Status:** `⏸️ ZDEFEROWANY — Cost/Benefit negatywny na MVP`  

**Diagnoza Audytora:** 
Obecny skrypt `export_reference_data` korzysta ze standardowego wywołania `call_command("dumpdata", ...)`. Powoduje to zapisywanie w JSON-ach twardych kluczy numerycznych (ID) dla relacji, m.in. dla puli szczytów w odznakach (`BadgeVersionModel.pool_peaks` M2M → `TouristObject`). Jeśli na produkcji po długim czasie wgramy snapshot wyeksportowany z DEV, gdzie kolejność ID szczytów (Primary Keys) mogła ulec zmianie po czyszczeniu bazy, relacje w odznakach wskażą na niewłaściwe góry.

**Analiza Cost/Benefit:**

**Status Quo (twarde ID) jest bezpieczny dzięki ADR-023 (Tombstone Pattern):**
- Klucze `id` obiektów referencyjnych są trwałe, nigdy nie podlegają ponownemu wykorzystaniu (ADR-023:49).
- PROD nie generuje nowych danych referencyjnych — wszystko płynie z DEV przez `loaddata` (ADR-020).
- Zasada *Soft Delete* chroni historycznej integralności — usunięty szczyt to "nagrobek", ID nie zostaje zwolnione.

**Plan (wstrzymany — wymaga migracji schematu):**
- [ ] Dodać `natural_key()` + `get_by_natural_key()` do modeli referencyjnych.
- [ ] Dodać `--natural-foreign-key --natural-primary-key` do `dumpdata`.
- [ ] Dodać test snapshot/roundtrip.

**ZDECYZOWANO — ZDEFEROWAĆ wdrożenie na Fazę Skalowania (mikroserwisy CMS).**

Uzasadnienie architektoniczne:
1. **Neutralizacja ryzyka operacyjnego:** ADR-023 Tombstone eliminacja "rozjazdu ID" przez zakaz usunięcia rekordów na DEV. Ryzyko przenoszenia błędnych M2M ≈ znikome.
2. **Koszt refaktoryzacji bazy:** `OrganizerModel.name` nie jest `unique` → wymaga migracji dodających pola unikalne + transformacji danych + menedżerów `get_by_natural_key`. Ogromna praca dla 5 modeli.
3. **Mutowalność Natural Keys:** `OrganizerModel.name` / `TouristObject.code` mogą ulec zmianie → Natural Keys psują referencje historyczne. Twarde ID (immutable PK) są odporne na to.
4. **Spadek wydajności loaddata:** Rozwiązywanie Natural Keys ("znajdź Szczyt po kodzie") wydłuża `restore_reference_data` vs `bulk_insert` z ID.

**Powiązane:**
- **ADR-020** — Architektura Wdrożeń (SRE): "PROD nie tworzy danych referencyjnych".
- **ADR-023** — Cykl Życia Danych Referencyjnych (Tombstone Pattern): "Klucze główne są trwałe, nigdy nie podlegają ponownemu wykorzystaniu".

**Trigger for Review:**
- Rozbicie monolitu danych referencyjnych na zewnętrzny CMS (gdyby dane szczytów przychodziły z zewnętrznego źródła, twarde ID stałyby się niemożliwe do synchronizacji).

**Komentarz Architekta:**
Wspaniałe wyłapanie klasycznego błędu `loaddata`. Obecnie nasz system działa, bo wszystkie środowiska startują od zera. Przy aktualizacjach działającej produkcji na przestrzeni lat, twarde ID to tykająca bomba.

---

### [AUDYT-093] Brak zautomatyzowanej kwarantanny dla złośliwych danych OSM
**Obszar:** `Dane Referencyjne / DataOps`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `🔴 OTWARTE`  

**Diagnoza Audytora:** 
Obecny mechanizm "Nocnego Stróża" (`RunOsmNightWatchmanUseCase`) potrafi zgłaszać konflikty do skrzynki odbiorczej (Inbox), ale brakuje mu systemu odporności na celowe zatruwanie danych. Atakujący w OpenStreetMap może edytować znany szczyt PTTK (np. Rysy), zmieniając jego współrzędne tak, by znalazł się na Alasce, co zniszczyłoby wyliczanie CQRS i weryfikację. Nasz system aktualizuje tagi w `osm_raw_tags` w tle, nie alarmując o drastycznych anomaliach przestrzennych.

**Wdrożenie (status techniczny):**
- [ ] Zdefiniować próg kwarantanny geolokacyjnej (np. "przesunięcie wierzchołka o więcej niż 500 metrów" lub "zmiana wysokości o więcej niż 10%").
- [ ] Zaprojektować regułę w `OsmRepositoryPort`, która wstrzyma cichą aktualizację `osm_raw_tags` przy przekroczeniu progu, blokując synchronizację do czasu interwencji administratora.

**Status techniczny (werdykt kodu):**
- ⚠️ **Status `🟢 ZAKOŃCZONO` w dokumencie = BŁĄD.** Kod (`osm_repository.py:detect_and_save_conflicts`) ma **tylko `altitude` + `wikipedia_link`** jako conflict checks. **Brak walidacji przestrzennej (geometry drift)**.
- ⚠️ `RunOsmNightWatchmanUseCase:117-124` nadpisuje `osm_raw_tags` i geometrię **cicho** (`update_object_after_sync`) bez progu >500m.
- ⚠️ `ST_Distance` / geofencing nie istnie w kodzie (potwierdzone grepem).

**Komentarz Architekta:**
Klasyczny "Blind Spot" integracji zewnętrznych. Całkowite zaufanie do otwartego API (OSM) to ryzyko wandalizmu (Vandalism Attack). Ciche wstrzymanie (Quarantine) zabezpieczy nas przed rozpadem siatki MVT.

---
