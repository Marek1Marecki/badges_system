# Twarde zasady kontekstowe dla agentów AI w projekcie PTTK Badges

Zanim odpowiesz na JAKIEKOLWIEK pytanie lub wygenerujesz jakikolwiek kod w tym projekcie, musisz bezwzględnie przeczytać plik `SYSTEM_PROMPT.md` oraz `INVARIANTS.md` w katalogu głównym lub w `docs/`.

**ZASADA BLAST RADIUS:**
Każda zmiana sygnatury w `application/ports/` wymaga aktualizacji WSZYSTKICH implementacji (adapterów w `infrastructure/` i Fake'ów w `tests/fakes/`) w tym samym commicie. Przed zmianą użyj `grep` (lub wbudowanego narzędzia szukającego) na całym repozytorium.

Jeśli Twoje działanie lub zapytanie użytkownika dotyczy konkretnych katalogów, postępuj zgodnie z tą matrycą kontekstową:

1. **Jeśli modyfikujesz pliki w katalogu `domain/`:**
   - Przeczytaj sekcję "AGENT-DOMAIN-CODE" w pliku `AGENT_SPEC.md`.
   - Zastosuj ścisły zakaz importów bibliotek zewnętrznych (w tym Django, Pydantic, Dateutil). Używaj wyłącznie `stdlib`.
   - Czas musi być wstrzykiwany przez kontekst. Absolutny zakaz użycia `datetime.now()`.

2. **Jeśli modyfikujesz pliki w katalogu `application/use_cases/` lub `application/dto/`:**
   - Przeczytaj sekcję "AGENT-USECASE-CODE" w pliku `AGENT_SPEC.md`.
   - Przeczytaj `SCENARIOS.md` dla powiązanego scenariusza (np. SCN-001, SCN-010).
   - Zależności zewnętrzne (repozytoria, ClockPort) wstrzykuj wyłącznie przez konstruktor `__init__`.
   - Zakaz bezpośredniego importu modeli Django ORM (`apps/badges/models.py`).

3. **Jeśli modyfikujesz pliki w katalogu `infrastructure/adapters/` lub `apps/badges/tasks.py`:**
   - Przeczytaj sekcję "AGENT-INFRA-CODE" w pliku `AGENT_SPEC.md`.
   - Przeczytaj `DATAFLOW.md` dla kontekstu zdarzeń.
   - Pamiętaj o ochronie przed wyjątkami zapytań API (wymóg użycia `urllib` zamiast `httpx` do łączenia z OSM).
   - Nie używaj rzutowania `ST_DistanceSpheroid` w pętli, używaj `ST_DWithin` z indeksem.
   - Dla adapterów budujących `AscentContextDTO` — przeczytaj w całości `ADR-012`.

4. **Jeśli modyfikujesz REST API (`apps/api/`, `apps/badges/views.py`):**
   - Przeczytaj `API_CONTRACTS.md` oraz `ERROR_HANDLING.md`.
   - Błędy zwracaj bezwzględnie w standardzie `RFC 7807 Problem Details`.
   - Upewnij się, że widoki mają dekoratory lub blokady uprawnień zdefiniowane w `SECURITY_MATRIX.md`.

5. **Jeśli modyfikujesz Frontend (`apps/templates/`, pliki `.js`):**
   - Przeczytaj `UI_GUIDELINES.md`.
   - Bezwzględnie używaj Vanilla JS, HTMX oraz MapLibre GL JS.
   - Pamiętaj o stosowaniu minimum 300ms Debounce przy zapytaniach BBox z mapy.

6. **Jeśli modyfikujesz pliki w katalogu `tests/` lub `tests/fakes/`:**
   - Przeczytaj sekcję "Fakes" w pliku `TEST_STRATEGY.md`.
   - Jeśli modyfikujesz `tests/fakes/` — sprawdź, czy Fake bezbłędnie i aktualnie implementuje interfejs z `application/ports/`.
   - Każda nowa klasa reguły domenowej wymaga minimum dwóch testów: `success` i `failure`.
   - Testy naprawione przez zmianę asercji zamiast przez modyfikację kodu domenowego są zakazane (Test Failure Protocol).

*Uwaga ogólna:* Modyfikacje pliku wstrzykiwania zależności `bootstrap/container.py` zawsze wymagają przeczytania `MODULES.md` (sekcja `bootstrap/`).

**PROTOKÓŁ ZAKOŃCZENIA:**
1. Przed wykonaniem komitu sprawdź `EDGE_CASES.md` — jeśli modyfikowany przez Ciebie obszar ma tam wpis ze statusem `open`, musi on zostać zaadresowany (`resolved` / `wont-fix`) lub Pull Request musi zawierać uzasadnienie, dlaczego Edge Case nie dotyczy tej zmiany.
2. Każda sesja kodowania musi być walidowalna poleceniem `make check`. Wygenerowany kod nie ma prawa złamać linterów (`mypy --strict`, `ruff format`, `import-linter`) ani testów jednostkowych.
3. Nigdy nie modyfikuj plików konfiguracyjnych linterów (np. `pyproject.toml`, `.importlinter`), aby obejść błędy – napraw kod.
