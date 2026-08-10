# Test Strategy — strategia testowania

> **Wersja:** 1.1  
> **Data:** 2026-05-28  
> **Właściciel:** Dominik / AI Architect  

---

## Piramida testów systemu PTTK Badges

| Poziom | Cel | Narzędzie | Czas | Uruchamiane |
|--------|-----|-----------|------|-------------|
| **Property/Fuzz** | Testowanie krawędzi matematyki domenowej milionami wygenerowanych wariacji danych. | `pytest` + `Hypothesis` | < 10s | Każdy commit (`make check`) |
| **Unit** | Czysta logika biznesowa, Wzorzec Strategii (Reguły), Invarianty | `pytest` + `Fake` repozytoria | < 5s | Każdy commit (`make check`) |
| **Integration** | Adaptery bazodanowe (GeoDjango), weryfikacja zapytań HTTP do OSM | `pytest` + `@pytest.mark.django_db` | < 30s | W CI Pipeline (`test-run.sh --full`) |
| **SecOps (SAST)** | Skanowanie kodu Pythona i konfiguracji w poszukiwaniu znanych wzorców podatności (OWASP, wycieki haseł). | `Semgrep` | < 10s | Każdy commit (`make security-audit`) |
| **E2E** | Złożone przepływy GUI turysty | `Playwright` | > 1m | Przed wydaniem na PRE-PROD |

### Zautomatyzowany Potok CI/CD (GitHub Actions)

System wykorzystuje dwie równoległe ścieżki weryfikacji (Quality Pipeline i Security Pipeline), aby szybko wychwytywać błędy bez blokowania się na długich testach:

```text
                         PUSH / PR
                             │
             ┌───────────────┴────────────────┐
             │                                │
             ▼                                ▼
       QUALITY PIPELINE                 SECURITY PIPELINE
             │                                │
             ▼                                │
    Static Analysis / Ruff / Mypy            │
             │                                │
        Unit Tests                           │
             │                                │
   Integration Tests                         │
             │                                │
             ▼                                ▼
        E2E / Playwright                 CodeQL (security-extended)
                                           + schedule (weekly)
```

| Ścieżka | Cel i Środowisko | Mechanika i Wymogi |
|---------|------------------|--------------------|
| **Quality Pipeline** | Szybka weryfikacja kodu (Lintery, Mypy, Import-Linter) oraz testów Jednostkowych, Integracyjnych i E2E. | Uruchamiana na self-hosted runnerze. Czysty Python z pakietami w grupie `dev`. **Wymagane pokrycie 80% (`fail-under`).** Testy E2E wyłączają coverage przez `--override-ini="addopts="`. |
| **Security Pipeline** | Skanowanie statyczne przepłyfu danych (Semgrep) oraz semantyczna analiza kodu (CodeQL). | Uruchamiana równolegle na self-hosted runnerze. CodeQL używa zestawu zapytań `security-extended`. Dodatkowo skan cykliczny uruchamiany jest co poniedziałek o 02:30 (`schedule`). Wyniki trafiają do **Code scanning alerts** w GitHub Security Dashboard. |

---

## Pokrycie kodu (Coverage)

Minimalny próg globalny dla tego projektu wynosi **80%** (skonfigurowany w `pyproject.toml` w sekcji pytest).

| Moduł | Cel pokrycia | Priorytet i Uzasadnienie |
|-------|-------------|--------------------------|
| `domain/` | 95% | **Krytyczny** — tu żyją regulaminy PTTK i logika walidacji. |
| `application/` | 90% | **Wysoki** — Orkiestracja przepływów danych i weryfikacja. |
| `infrastructure/` | 70% | **Średni** — Adaptery trudne do testowania bez wstawania z ciężką bazą danych lub zewnętrznym API OSM. |
| `apps/` | 60% | **Niski** — Kod interfejsu (Admin UI), deklaracje ORM. Wymuszone testami E2E, pliki migracji całkowicie wykluczone z coverage. |

---

## Co jest testowane — zakres

### ✅ Testujemy ZAWSZE
- **Każdy Invariant z `INVARIANTS.md`** ma test, który celowo go narusza (np. podanie błędnego wieku do `MinAgeRule`).
- **Logikę domenową bez bazy danych:** `VerifyBadgeUseCase` testowany z użyciem szybkich narzędzi `FakeBadgeRepository`.
- **Ekstraktory:** Działanie `OsmDataExtractor` (wyciąganie nazw, wysokości, języków granicznych) na suchych słownikach JSON z OSM.
- **Idempotentność Danych Referencyjnych (DataOps):** Wymagane jest pokrycie procesu `restore_reference_data` testem integracyjnym weryfikującym jego idempotentność. Test musi wykonać operację dwukrotnie na tym samym snapshocie referencyjnym, na końcu wykonując asercję potwierdzającą brak zmian w bazie i brak duplikacji obiektów/relacji podczas drugiego przebiegu. Jest to jedyny dopuszczalny dowód na bezpieczeństwo uruchamiania tej komendy na środowisku produkcyjnym.
- **Ograniczenia Reguł Biznesowych (Property-Based Testing):** Silnik domenowy, w szczególności twarda matematyka i kalendarz (`TimeLimitRule`, `MandatoryObjectsRule`, Algebra Zbiorów), testowany jest za pomocą biblioteki `Hypothesis`. Testy te uderzają w silnik losowo modyfikowanymi tablicami wejść i listami wymogów, aby udowodnić brak awarii typu `KeyError`, `IndexError` czy załamań logiki przy braku danych (Empty Sets).

### ❌ Nie testujemy (i dlaczego)
- **Live Overpass API w testach Unit:** Testy adaptera OSM (`test_osm_adapter.py`) używają mocków HTTP (`@patch`). Nie obciążamy publicznych, zewnętrznych serwerów w pipeline CI, zapobiegając fałszywym awariom (Flaky Tests) wynikającym z błędów 504.
- **Geometrii w Czystej Domenie:** Domena operuje na `frozenset[int]`. Nie testujemy funkcji przestrzennych `PostGIS` w logice walidacji odznak (zgodnie z ADR-009).

---

## Testy Integracyjne (Uruchamianie i Markery)

Logika PostGIS oraz widoków Django wymaga podniesienia środowiska. 

1. **Markery:** Testy integracyjne muszą być zawsze oznaczane dekoratorem:
   ```python
   @pytest.mark.integration
   @pytest.mark.django_db
   def test_region_cache_populated_after_calculate(): ...
   ```
2. **Wymogi Bazy Danych:** Testy integracyjne uruchamiają wbudowany mechanizm bazy testowej Django, jednak z uwagi na rozszerzenia GeoDjango, wymagają działającej instancji PostGIS. Przed ich uruchomieniem należy upewnić się, że kontenery deweloperskie działają (`docker compose -f docker-compose.dev.yml up -d`).
3. **Filtrowanie w CI i Makefile:** 
   - Komenda `make check` uruchamia wyłącznie testy Domeny i Aplikacji (`pytest -m "not integration"`), by gwarantować czas wykonania `< 15s`.
   - Pełen zbiór testów wraz z integracyjnymi odpalany jest komendą `make test-all` (lub w docelowym pełnym środowisku CI przed mergem).

---

## Fakes (Narzędzia Testowe)

Zamiast mockować bazę danych narzędziami takimi jak `unittest.mock` w warstwie Aplikacji, budujemy dedykowane, in-memory implementacje Portów.

**Konwencja Strukturalna:** Wszystkie Test Doubles mieszkają w katalogu `tests/fakes/` i implementują porty z `application/ports/` — nigdy nie importują z `infrastructure/`.

1.  **`FakeClock`:** Wstrzykiwany do Use Case'ów. Rozwiązuje problem niedeterminizmu testów zależnych od czasu (Limit Czasu na Odznakę, Prawa Nabyte po konkretnym roku). Posiada dedykowaną metodę `advance()`.
2.  **`FakeBadgeRepository`:** Odtwarza stan bazy z pamięci RAM. Zwraca instancje `BadgeVersionDomain` bez żadnego zapytania SQL, co przyspiesza testy. Zawsze weryfikuj interfejs Fake'a z oryginalnym Portem!

---

## Wzorzec Testowania API (Izolacja Kontrolerów)

W testach integracyjnych dla widoków REST API (`apps/api/views.py`) obowiązuje rygorystyczny wzorzec odcinania logiki biznesowej od warstwy HTTP. 
Celem testu widoku jest sprawdzenie **wyłącznie**: 
1. Parsowania parametrów wejściowych (Pydantic DTO).
2. Autoryzacji (`_require_auth`).
3. Formatyzacji błędów do standardu RFC 7807 (`_handle_application_exception`).

**Jak testujemy:**
- Używamy `django.test.RequestFactory` (uwaga: omija to globalne Middleware, zgodnie z EC-042).
- Zamiast podnosić bazę danych, **mockujemy globalny kontener DI**.

```python
# Wzorzec testowy (pytest):
@pytest.fixture
def use_cases():
    """Zwraca dict mocków Use Case'ów i izoluje widoki od prawdziwej domeny/bazy."""
    cases = {
        "log_ascent": MagicMock(),
        "start_badge_progress": MagicMock(),
    }
    with patch("apps.api.views.get_container", return_value=cases):
        yield cases


def test_conflict_error_returns_409_rfc7807(factory, mock_user, use_cases):
    use_cases["log_ascent"].execute.side_effect = ConflictError("Duplikat")
    # ... wykonanie żądania i asercja JSONa ...
```

---

## Protokół weryfikacji testu (Zasada Mutacji)

Zanim uznasz, że napisałeś poprawny test dla Invariantu (np. `TimeLimitRule`), **wykonaj test mutacyjny**:
1. Otwórz kod Pythona w `domain/rules/badge_rules.py`.
2. Zmień na chwilę znak `<` na `<=` (albo odwróć warunek logiczny).
3. Odpal test.
4. **Jeśli test PRZESZEDŁ, to jest bezwartościowy.** Oznacza, że asercja nie łapie rzeczywistej granicy błędu. Cofnij zmianę i napisz test od nowa z twardszą asercją.

---

## Zasady dla agentów LLM

- **Fakes vs Mocks (Granica Architektoniczna):** 
  - Do testowania Czystej Domeny (`domain/rules/`, `BadgeVersionDomain`) bezwzględnie używamy czystych obiektów Pythona.
  - Do testowania Orkiestratorów (`application/use_cases/`), które posiadają 3 lub więcej wstrzykiwanych Portów Repozytoriów, kategorycznie zezwala się na użycie `unittest.mock.MagicMock`. Pisanie i utrzymywanie rozbudowanych `FakeRepositories` dla skomplikowanych agregatów z relacjami jest antywzorcem (Over-engineering) i zaciemnia cel testu, którym w Use Case jest weryfikacja przepływu (Orchestration), a nie stanu danych.

### Zakazane
- **Mockowanie wewnętrznej logiki:** Nigdy nie mockuj klas wewnątrz tego samego modułu (np. nie mockuj `BadgeVersionDomain.evaluate` testując `VerifyBadgeUseCase`). W Use Case testujesz realne współdziałanie Domeny, używając Fake Adapterów z `tests/fakes/`.
- **`datetime.now()` w testach:** Zawsze używaj `FakeClock.DEFAULT_TIME` lub explicit zdefiniowanej daty statycznej z `tzinfo`. Test uruchomiony za 5 lat musi dać ten sam wynik co dziś.
- **Kruche asercje (Brittle Tests):** Przy testowaniu rozszerzalnych schematów lub list z konfiguracji (np. `RULES_SCHEMA`), kategorycznie zakazuje się używania asercji długości całkowitej (np. `assert len(choices) == 5`). Taki test psuje się przy dodaniu nowej funkcjonalności. Należy testować *obecność* konkretnego klucza (np. `assert "MinAgeRule" in [c["value"] for c in choices]`).

### Wymagane
- Każda nowa klasa dziedzicząca po `BadgeRule` musi mieć minimum dwa testy: `test_rule_name_success` oraz `test_rule_name_failure`.
- Jeśli łatana jest usterka zapisana w `EDGE_CASES.md`, test zapobiegający regresji musi nosić jej prefiks i numer, np. `def test_EC020_badge_tier_requires_explicit_choice_to_save():`.
- **BDD Mapping (Behavior-Driven Design):** Testy jednostkowe i integracyjne nie mogą opisywać technicznej implementacji (np. `test_badge_engine_resolves_json`), lecz muszą opisywać intencję biznesową i zachowanie systemu (np. `test_user_earns_badge_after_3_peaks_in_region_respecting_grandfather_clause`). Zgodnie z architekturą, testy te mapują się bezpośrednio z User Stories i służą jako "Living Documentation".

---

## Szybka Referencja: Uruchamianie Testów i Weryfikacji (Cheat Sheet)

Poniższe komendy (`make` i pod spodem odpowiadające im skrypty/wywołania `uv`) stanowią ujednolicony standard weryfikacji kodu na środowisku developerskim.

### 1. Szybkie testy jednostkowe (Lokalnie, bez Dockera)
Najszybsza pętla sprzężenia zwrotnego. Czysty kod Pythona.
```bash
make test
# Pod spodem wykonuje: ENV_FILE=.env.test uv run pytest -m "not integration and not e2e"
```

### 2. Wszystkie testy (Lokalnie, z bazą PostGIS, z wymogiem Coverage > 80%)
Wymaga włączonych kontenerów db i redis w tle.
```bash
make test-all
# Pod spodem wykonuje: ENV_FILE=.env.test uv run pytest tests --create-db --nomigrations --cov-fail-under=80
```

### 3. Weryfikacja jakości przed commitem (Lintery + Typy + Kontrakty)
Komenda, którą należy uruchomić przed każdym `git push`.
```bash
make check
# Uruchamia: ruff (format + lint), mypy (strict), import-linter, audit_contracts.py, a na końcu `make test`.
```

### 4. Efemeryczne Środowisko TEST (Bezpieczna, odizolowana piaskownica)
Stawia własną, pustą bazę, odpala testy w kontenerze `testing` i usuwa ślady (`down -v`).
```bash
# Szybkie testy jednostkowe w izolacji:
make test-run

# Pełny suite z weryfikacją skryptów wdrożeniowych (release scripts)
# i prawdziwą bazą integracyjną:
make test-run ARGS="--full"

# Uruchomienie wybranego testu z dodatkowymi flagami (omija wymóg coverage):
make test-run ARGS="-k test_poi_scoring --no-cov"
```

### 5. Efemeryczne Środowisko E2E (Testy Przeglądarkowe Playwright)
Powołuje środowisko na porcie 8009, ładuje snapshot PTTK i uruchamia zrobotyzowaną przeglądarkę. Zawsze sprząta po sobie zasoby.
```bash
# Uruchomienie całego pakietu E2E:
make e2e

# Uruchomienie w trybie gadatliwym / debug:
make e2e ARGS="-v -k test_homepage"
```

### 6. Weryfikacja Krawędziowa Czystej Domeny (Hypothesis / Property-Based)
Jeśli testujesz skrajne matematyczne warianty reguł (np. logikę Praw Nabytych).
```bash
ENV_FILE=.env.test DEBUG=False uv run pytest tests/domain/rules/test_badge_rules_hypothesis.py -v --no-cov
```

---

## Strategia Testów End-to-End (E2E / Playwright)

Testy te pełnią rolę ostatecznego weryfikatora dla ścieżek krytycznych systemu (Happy Paths), testując w 100% zmontowane środowisko (`PRE-PROD`). Z racji wysokiego kosztu utrzymania i czasu wykonywania, w testach E2E nie sprawdzamy skomplikowanych krawędzi matematyki domenowej (od tego są testy jednostkowe z atrapą czasu).

**Wzorzec Bypass Authentication (Omijanie OAuth):**
W środowiskach zintegrowanych logowanie Google OAuth wymagałoby rozwiązywania Captcha lub odbierania SMS-ów przez robota, co czyni testy kruchymi (Flaky).
- **Zabrania się:** Modyfikowania kodu produkcyjnego (wyłączania warunków logowania dla testów).
- **Zasada działania:** W pliku `tests/e2e/conftest.py` wykorzystywana jest fiktura (np. `logged_in_context`), która za pomocą komendy administracyjnej Django (`create_test_session.py`) generuje i zatwierdza w bazie danych ważne ciastko sesji (Session Cookie). Ciasteczko to jest bezpośrednio wstrzykiwane do silnika Chromium w Playwright. Dzięki temu robot porusza się po systemie jako pełnoprawny, uwierzytelniony "Testowy Turysta" omijając zewnętrzny ekran logowania.

## Wzorce Testowania End-to-End (Playwright)

W środowisku PRE-PROD uruchamiany jest zrobotyzowany test weryfikujący ostateczny rendering HTML, silnik HTMX i mapy (MapLibre). Zgodnie z dobrymi praktykami QA:
- **Zasada Stabilności Selektorów:** Testy w Playwright nie mogą polegać na klasach CSS (np. `.btn-primary`) czy strukturze DOM (np. `div > ul > li`). Programista musi bezwzględnie wstrzykiwać dedykowane atrybuty **`data-testid`** w kodzie HTML i opierać asercje wyłącznie na nich (np. `page.locator("[data-testid='btn-subscribe-KGP']")`).
- **Oczekiwanie Asynchroniczne (Smart Waiting):** Zamiast używania sztywnego `time.sleep()`, robot testujący musi oczekiwać na asynchroniczną reakcję serwera za pomocą np. wbudowanych asercji `expect(locator).to_be_visible()` lub jawnego `expect_response` do kontrolowania ruchu AJAX/HTMX.
- **Odłączenie Obliczania Pokrycia:** Ponieważ test E2E weryfikuje głównie renderowanie po stronie serwera i w niewielkim stopniu dotyka Czystej Domeny, musi on zostać zignorowany przez system mierzący próg `coverage` (fail-under=80) na poziomie skryptu CI.
