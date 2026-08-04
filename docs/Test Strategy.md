# Test Strategy — strategia testowania

> **Wersja:** 1.1  
> **Data:** 2026-05-28  
> **Właściciel:** Dominik / AI Architect  

---

## Piramida testów systemu PTTK Badges

```text
         /\
        /e2e\        ← Faza C: Przepływy logistyki książeczek [Playwright — planowane]
       /──────\
      /integr. \     ← Średnio: Django Admin, PostGIS (ST_DWithin), OSM Adapter
     /────────── \
    /   unit      \  ← Dużo: Reguły w `domain/`, Use Cases w `application/`
   /______________\
```

| Poziom | Cel | Narzędzie | Czas | Uruchamiane |
|--------|-----|-----------|------|-------------|
| **Unit** | Czysta logika biznesowa, Wzorzec Strategii (Reguły), Invarianty | `pytest` + `Fake` repozytoria | < 5s | Każdy commit (`make check`) |
| **Integration** | Adaptery bazodanowe (GeoDjango), weryfikacja zapytań HTTP do OSM | `pytest` + `@pytest.mark.django_db` | < 30s | W CI Pipeline (`make test-all`) |
| **E2E** | Złożone przepływy GUI turysty | `Playwright` | > 1m | Przed wydaniem (Release) |

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
   def test_region_cache_populated_after_calculate():
       ...
   ```
2. **Wymogi Bazy Danych:** Testy integracyjne uruchamiają wbudowany mechanizm bazy testowej Django, jednak z uwagi na rozszerzenia GeoDjango, wymagają działającej instancji PostGIS. Przed ich uruchomieniem należy upewnić się, że kontenery deweloperskie działają (`docker compose -f docker-compose.dev.yml up -d`).
3. **Filtrowanie w CI i Makefile:** 
   - Komenda `make check` uruchamia wyłącznie testy jednostkowe (`pytest -m "not integration"`), by gwarantować czas wykonania `< 10s`.
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

### Co jest testowane — zakres", ❌ Nie testujemy (i dlaczego)

- **Banałów ORM-a w testach jednostkowych (ORM Wrappers):** Nie piszemy testów jednostkowych, których jedynym celem jest mockowanie bazy po to, by sprawdzić, czy metoda `get_or_create` w adapterze repozytorium faktycznie wykonuje `get_or_create`. Jest to testowanie kodu twórców frameworka Django, a nie naszego. Niski poziom pokrycia (Coverage) rzędu 20-30% w katalogu `infrastructure/adapters/persistence/` jest zjawiskiem **w pełni akceptowalnym i pożądanym**. Weryfikację tych metod delegujemy do wyższych warstw testowych (Integration / E2E Playwright).

---

## Środowiska Testowe i Zarządzanie Danymi (Data Stewardship)

Zgodnie z koncepcją "Bazy jako Odtwarzacza", kategorycznie rozdzielamy dane użytkowników (Runtime) od danych systemowych PTTK (Reference Data).

**Wymogi dla środowisk integracyjnych i E2E (Pre-Prod / Playwright):**
1. **Pojedyncze Źródło Prawdy:** Środowisko testowe NIE MOŻE być repliką bazy deweloperskiej ani polegać na ręcznie stworzonych szczytach w panelu Admina.
2. **Kolejność Odtwarzania:** Przed każdym przebiegiem testów E2E należy wykonać w 100% zautomatyzowany reset bazy, a następnie wywołać skrypt `uv run python manage.py restore_reference_data`. Gwarantuje to, że skrypty testujące (np. klikające w Babią Górę) pracują na identycznym, zmanifestowanym zestawie węzłów topograficznych i regulaminów odznak, jaki znajduje się aktualnie w repozytorium Git.
3. **Integralność Snapshotu:** Pakiet danych z `data/reference/*.json.gz` to spójny graf (Aggregate). Zawsze musi być wgrywany w całości. Próba wgrania tylko np. regionów z pominięciem odznak skończy się błędami referencyjnymi.

---

## Strategia Testów End-to-End (E2E / Playwright)

Testy te pełnią rolę ostatecznego weryfikatora dla ścieżek krytycznych systemu (Happy Paths), testując w 100% zmontowane środowisko (`PRE-PROD`). Z racji wysokiego kosztu utrzymania i czasu wykonywania, w testach E2E nie sprawdzamy skomplikowanych krawędzi matematyki domenowej (od tego są testy jednostkowe z atrapą czasu).

**Wzorzec Bypass Authentication (Omijanie OAuth):**
W środowiskach zintegrowanych logowanie Google OAuth wymagałoby rozwiązywania Captcha lub odbierania SMS-ów przez robota, co czyni testy kruchymi (Flaky). 
- **Zabrania się:** Modyfikowania kodu produkcyjnego (wyłączania warunków logowania dla testów).
- **Zasada działania:** W pliku `tests/e2e/conftest.py` wykorzystywana jest fiktura (np. `logged_in_context`), która za pomocą komendy administracyjnej Django (`create_test_session.py`) generuje i zatwierdza w bazie danych ważne ciastko sesji (Session Cookie). Ciasteczko to jest bezpośrednio wstrzykiwane do silnika Chromium w Playwright. Dzięki temu robot porusza się po systemie jako pełnoprawny, uwierzytelniony "Testowy Turysta" omijając zewnętrzny ekran logowania.

---
