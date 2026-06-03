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

## Protokół weryfikacji testu (Zasada Mutacji)

Zanim uznasz, że napisałeś poprawny test dla Invariantu (np. `TimeLimitRule`), **wykonaj test mutacyjny**:
1. Otwórz kod Pythona w `domain/rules/badge_rules.py`.
2. Zmień na chwilę znak `<` na `<=` (albo odwróć warunek logiczny).
3. Odpal test.
4. **Jeśli test PRZESZEDŁ, to jest bezwartościowy.** Oznacza, że asercja nie łapie rzeczywistej granicy błędu. Cofnij zmianę i napisz test od nowa z twardszą asercją.

---

## Zasady dla agentów LLM

### Zakazane
- **Mockowanie wewnętrznej logiki:** Nigdy nie mockuj klas wewnątrz tego samego modułu (np. nie mockuj `BadgeVersionDomain.evaluate` testując `VerifyBadgeUseCase`). W Use Case testujesz realne współdziałanie Domeny, używając Fake Adapterów z `tests/fakes/`.
- **`datetime.now()` w testach:** Zawsze używaj `FakeClock.DEFAULT_TIME` lub explicit zdefiniowanej daty statycznej z `tzinfo`. Test uruchomiony za 5 lat musi dać ten sam wynik co dziś.
- **Kruche asercje (Brittle Tests):** Przy testowaniu rozszerzalnych schematów lub list z konfiguracji (np. `RULES_SCHEMA`), kategorycznie zakazuje się używania asercji długości całkowitej (np. `assert len(choices) == 5`). Taki test psuje się przy dodaniu nowej funkcjonalności. Należy testować *obecność* konkretnego klucza (np. `assert "MinAgeRule" in [c["value"] for c in choices]`).

### Wymagane
- Każda nowa klasa dziedzicząca po `BadgeRule` musi mieć minimum dwa testy: `test_rule_name_success` oraz `test_rule_name_failure`.
- Jeśli łatana jest usterka zapisana w `EDGE_CASES.md`, test zapobiegający regresji musi nosić jej prefiks i numer, np. `def test_EC020_badge_tier_requires_explicit_choice_to_save():`.

---

## Historia zmian

| Wersja | Data | Autor | Opis zmiany |
|--------|------|-------|-------------|
| 1.0 | 2026-05-28 | Dominik / AI Architect | Pierwsza wersja (Testowanie GeoDjango, FakeClock). |
| 1.1 | 2026-05-28 | AI Architect | Doprecyzowanie ról markerów integracyjnych, celów pokrycia per moduł (Coverage Table) i konwencji dla katalogu `fakes/`. |