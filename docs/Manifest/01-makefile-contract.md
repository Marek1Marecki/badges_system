# Makefile Contract

**Status:** Egzekwowalny  
**Zakres:** Wszystkie projekty Python

---

## Filozofia

Makefile to cienka warstwa orkiestracyjna. Nie zawiera logiki biznesowej, nie maskuje narzędzi, nie ma złożonej logiki warunkowej.

**Zasada kluczowa:** `make check = CI quality-gate`, `pre-commit ⊆ make check`

Pre-commit uruchamia `make check` w całości lub jego szybki podzbiór (projekty ML) — ale nigdy nic czego nie ma w `make check`. CI uruchamia dokładnie `make check`. Brak rozbieżności. `check` jest bezstanowy — zero efektów ubocznych, brak modyfikacji bazy danych ani systemu plików.

---

## CORE — obowiązkowe w każdym repo

| Target | Opis |
|--------|------|
| `help` | Lista dostępnych komend |
| `setup` | Instalacja zależności i pre-commit (idempotentne) |
| `run` | Uruchomienie aplikacji w trybie dev (bez infrastruktury) |
| `format` | Formatowanie kodu |
| `lint` | Linting kodu |
| `type-check` | Statyczna analiza typów (mypy + lint-imports) |
| `test` | Szybkie testy jednostkowe (bez integration, bez ml) |
| `audit` | Audyt kontraktów architektonicznych (AST) |
| `check` | Lokalne CI: format --check + lint + type-check + test + audit |
| `clean` | Usunięcie cache i artefaktów |
| `secrets-check` | Walidacja obecności sekretów z `.env.example` w środowisku |

### Zasady CORE

CORE jest identyczny w każdym repo — bez wyjątków. `setup` jest idempotentne: tylko `uv sync` + `pre-commit install`. `setup` nie uruchamia usług, nie wykonuje migracji, nie seeduje danych.

### Definicja `check`

```
format --check
lint
type-check      (mypy + lint-imports)
test
audit           (audit_contracts.py — AST scan)
```

W tej kolejności — szybkie operacje przed wolnymi. `audit` jest ostatni bo jest szybki, ale raportuje inną kategorię błędów niż ruff/mypy. `check` jest idempotentny i może być uruchamiany gdy baza danych jest niedostępna.

`type-check` zawiera dwa narzędzia: mypy weryfikuje typy per-warstwa, lint-imports weryfikuje kierunek zależności między warstwami. Razem tworzą kompletną weryfikację architektury — mypy nie wykryje że `domain/` importuje z `infrastructure/` jeśli typy są poprawne, import-linter wykryje to zawsze.

`audit` uzupełnia powyższe o naruszenia których nie wykrywa żadne inne narzędzie: `datetime.now()` w domenie, `logging` w domenie, `os.getenv` w `application/`, importy ukryte w bloku `TYPE_CHECKING`.

**Dlaczego `secrets-check` nie jest w `check`:** `make check` jest bezstanowy — nie wymaga środowiska, zdalnych usług ani zmiennych `.env`. `secrets-check` weryfikuje *obecność* sekretów w środowisku uruchomieniowym (CI lub dev), dlatego jest osobnym krokiem w pipeline (`09-ci-enforcement.md`), nie częścią `check`.

### `clean` usuwa

`*.pyc`, `__pycache__`, `.coverage`, `.coverage.*`, `htmlcov/`, `.pytest_cache/`, `.mypy_cache/`, `coverage.xml`, `.ruff_cache/` — **nigdy** `.venv/`

---

## Wyjątek: projekty ML — setup-slim

Projekty z ciężkimi zależnościami ML (Torch, WhisperX) definiują dwa warianty:

| Target | Opis |
|--------|------|
| `setup-slim` | Tylko narzędzia dev (ruff, mypy, pytest) — bez Torch/WhisperX |
| `setup` | Pełna instalacja z Torch |

`setup-slim` jest punktem wejścia dla dewelopera pracującego na logice biznesowej. CI quality-gate używa `setup-slim` by uniknąć pobierania ~864MB Torch — pełny obraz budowany jest dopiero w security-gate.

---

## INFRA — modułowe, prefiksowane

Dodawaj tylko w projektach które mają infrastrukturę.

| Prefiks | Odpowiedzialność |
|---------|-----------------|
| `docker-*` | Runtime i infrastruktura Docker |
| `db-*` | Baza danych |
| `redis-*` | Redis |
| `model-*` | Modele ML |
| `gpu-*` | Operacje GPU |
| `test-*` | Wyspecjalizowane zestawy testów |

### Standardowe targety db-*

```makefile
db-migrate:
	docker compose run --rm web python manage.py migrate

db-shell:
	docker compose exec db psql -U $${POSTGRES_USER} -d $${POSTGRES_DB}

db-backup:
	docker compose exec db pg_dump -U $${POSTGRES_USER} $${POSTGRES_DB} > backup_$(shell date +%Y%m%d_%H%M%S).sql
```

**Dlaczego `run --rm` zamiast `exec` dla migracji?** `docker compose exec` wymaga działającego kontenera `web`. Jeśli aplikacja crashuje przy starcie z powodu brakującej migracji — `exec` się nie powiedzie, tworząc deadlock: nie można uruchomić aplikacji bez migracji, nie można wykonać migracji bez działającej aplikacji. `run --rm` tworzy jednorazowy kontener który startuje niezależnie od stanu aplikacji, ma dostęp do tej samej sieci co `web`, i usuwa się po zakończeniu.

`db-shell` używa `exec` (nie `run --rm`) — shell bazodanowy ma sens tylko gdy kontenery działają, to interaktywna sesja diagnostyczna a nie operacja administracyjna.

### Targety Sphinx

```makefile
docs-html:  ## Buduje dokumentację HTML (Sphinx)
	PYTHONPATH=$(PYTHONPATH) uv run sphinx-build -W --keep-going -b html docs_sphinx/source docs_sphinx/build/html

docs-clean:  ## Usuwa zbudowaną dokumentację
	rm -rf docs_sphinx/build/
```

`docs-html` musi kończyć się bez błędów. `--strict` włączamy po pełnym pokryciu docstringów w `domain/` i `application/`. `docs-html` nie jest częścią `make check` — jest opcjonalnym krokiem jakości.

---

## RUNTIME — tylko dla projektów usługowych

| Target | Opis |
|--------|------|
| `up` | Uruchomienie aplikacji w trybie runtime/produkcyjnym |
| `down` | Zatrzymanie runtime |
| `restart` | Restart runtime |

**Kluczowa zasada:** `run` ≠ `up`

- `run` → tryb developerski, lokalny, bez infrastruktury
- `up` → tryb runtime/produkcyjny, docker compose

---

## Wariant A — projekty lokalne (jednoosobowe)

```makefile
# ===============================
# CONFIG
# ===============================
PY_DIRS := .
TEST_DIRS := tests

# ===============================
# CORE
# ===============================
.PHONY: help setup format lint type-check test audit check clean run

help:
	@echo "CORE targets:"
	@echo "  setup        - instalacja zależności i pre-commit"
	@echo "  format       - formatowanie kodu (ruff)"
	@echo "  lint         - linting kodu"
	@echo "  type-check   - mypy + lint-imports"
	@echo "  test         - szybkie testy jednostkowe"
	@echo "  audit        - audit architektoniczny (AST)"
	@echo "  check        - lokalne CI: format --check + lint + type-check + test + audit"
	@echo "  clean        - usuwa cache, artefakty, pliki pyc"
	@echo "  run          - uruchomienie aplikacji lokalnie"

setup:
	uv sync --extra dev
	uv run pre-commit install

format:
	uv run ruff format $(PY_DIRS)

lint:
	uv run ruff check $(PY_DIRS)

type-check:
	uv run mypy $(PY_DIRS)
	uv run lint-imports

test:
	uv run pytest $(TEST_DIRS) -m "not integration and not ml"

audit:
	uv run python scripts/audit_contracts.py

check:
	uv run ruff format --check $(PY_DIRS)
	uv run ruff check $(PY_DIRS)
	uv run mypy $(PY_DIRS)
	uv run lint-imports
	uv run pytest $(TEST_DIRS) -m "not integration and not ml"
	uv run python scripts/audit_contracts.py

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -not -path "./.venv/*" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/ coverage.xml .ruff_cache/

run:
	uv run python -m app
```

---

## Wariant B — projekty produkcyjne (z ENV)

```makefile
# ===============================
# CONFIG
# ===============================
PY_DIRS := .
TEST_DIRS := tests
MIN_COVERAGE ?= 80
ENV ?= dev

# ===============================
# CORE — identyczny jak w wariancie A
# ===============================
.PHONY: help setup format lint type-check test test-all check clean run

setup:
	uv sync --group dev
	uv run pre-commit install

format:
	uv run ruff format $(PY_DIRS)

lint:
	uv run ruff check $(PY_DIRS)

type-check:
	uv run mypy $(PY_DIRS)
	uv run lint-imports

test:
	uv run pytest $(TEST_DIRS) -m "not integration" \
		--cov=$(PY_DIRS) --cov-report=term-missing \
		--cov-fail-under=$(MIN_COVERAGE)

test-all:
	uv run pytest $(TEST_DIRS) \
		--cov=$(PY_DIRS) --cov-report=term-missing \
		--cov-fail-under=$(MIN_COVERAGE)

audit:
	uv run python scripts/audit_contracts.py

check:
	uv run ruff format --check $(PY_DIRS)
	uv run ruff check $(PY_DIRS)
	uv run mypy $(PY_DIRS)
	uv run lint-imports
	uv run pytest $(TEST_DIRS) -m "not integration" \
		--cov=$(PY_DIRS) --cov-report=term-missing \
		--cov-fail-under=$(MIN_COVERAGE)
	uv run python scripts/audit_contracts.py

secrets-check:
	uv run python scripts/check_secrets.py

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -not -path "./.venv/*" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/ coverage.xml .ruff_cache/

run:
	uv run python -m app

# ===============================
# INFRA
# ===============================
.PHONY: docker-build docker-up docker-down db-migrate db-backup

docker-build:
	docker compose -f docker-compose.$(ENV).yml build

docker-up:
	docker compose -f docker-compose.$(ENV).yml up -d

docker-down:
	docker compose -f docker-compose.$(ENV).yml down

db-migrate:
	docker compose run --rm web python manage.py migrate

db-backup:
	docker compose exec db pg_dump -U $${POSTGRES_USER} $${POSTGRES_DB} \
		> backup_$(shell date +%Y%m%d_%H%M%S).sql
```

---

## Czego NIE robić

- Nie twórz targetów zależnych od zmiennych środowiskowych typu `jeśli ENV=prod`
- Nie twórz logiki warunkowej w Makefile
- Nie mieszaj dev i runtime w jednym targecie
- Nie twórz uniwersalnego super-Makefile dla wszystkich repo

---

## Dodatek: lint-docker (hadolint)

Linting Dockerfile jest oddzielnym targetem — nie wchodzi do `make check` który sprawdza kod aplikacji. Dockerfile to infrastruktura.

```makefile
.PHONY: lint-docker

lint-docker:
	hadolint Dockerfile
```

Uruchamiany jako osobny job w CI (`lint_docker`), równolegle z `quality-gate`.
