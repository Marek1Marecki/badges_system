# ===============================
# CONFIG
# ===============================
PY_DIRS := domain application infrastructure apps bootstrap scripts
TEST_DIRS := tests
MIN_COVERAGE ?= 80
export PATH := /home/dominik/.local/bin:$(PATH)

# ===============================
# CORE
# ===============================
.PHONY: help setup format lint type-check test test-all audit secrets-check graph check clean dev-up dev-down dev-reset dev-status dev-logs dev-backup dev-restore test-run verify preprod preprod-deploy preprod-status preprod-logs preprod-down e2e security-audit

help:
	@echo "CORE targets:"
	@echo "  setup        - instalacja zależności i pre-commit"
	@echo "  format       - formatowanie kodu (ruff)"
	@echo "  lint         - linting kodu"
	@echo "  type-check   - mypy + lint-imports"
	@echo "  test         - szybkie testy jednostkowe"
	@echo "  test-all     - wszystkie testy (jednostkowe + integracyjne) używane w CI/CD"
	@echo "  audit        - audit architektoniczny (AST)"
	@echo "  graph        - eksport grafu zaleznosci (DOT + SVG, opcjonalnie PNG)"
	@echo "  check        - lokalne CI: format --check + lint + type-check + test + audit"
	@echo "  clean        - usuwa cache, artefakty"

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
	ENV_FILE=.env.test uv run pytest -m "not integration"
	#uv run pytest $(TEST_DIRS) -m "not integration and not ml"

test-all:
	ENV_FILE=.env.test uv run pytest $(TEST_DIRS) --create-db --nomigrations \
		--cov=, --cov-report=term-missing \
		--cov-fail-under=$(MIN_COVERAGE)

audit:
	uv run python scripts/audit_contracts.py

secrets-check:
	uv run python scripts/check_secrets.py

graph:
	uv run python scripts/audit_contracts.py
	@if command -v dot >/dev/null 2>&1; then dot -Tpng dependencies.dot -o dependencies.png; echo "Rendered dependencies.png"; else echo "Graphviz dot not installed - kept dependencies.dot"; fi

security-audit:
	@echo "=== ROZPOCZYNANIE SKANOWANIA SEMGREP ==="
	uv run semgrep scan \
	  --config "p/python" \
	  --config "p/django" \
	  --config "p/owasp-top-ten" \
	  --config "p/secrets" \
	  --error --skip-unknown-extensions \
	  --exclude="tests/*" --exclude=".venv/*" --exclude="node_modules/*" --exclude="staticfiles/*"
	@echo "\n=== ROZPOCZYNANIE SKANOWANIA GOOGLE OSV-SCANNER ==="
	osv-scanner --lockfile=uv.lock --config=osv-scanner.toml

check:
	uv run ruff format --check $(PY_DIRS)
	uv run ruff check $(PY_DIRS)
	uv run mypy $(PY_DIRS)
	uv run lint-imports
	ENV_FILE=.env.test uv run pytest $(TEST_DIRS) -m "not integration and not e2e"
	uv run python scripts/audit_contracts.py
	make security-audit

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -not -path "./.venv/*" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/ coverage.xml .ruff_cache/

dev-up:      ## Uruchom środowisko DEV (bezpieczne na świeżym i istniejącym wolumenie)
	./scripts/dev-up.sh

dev-down:    ## Zatrzymaj środowisko DEV — NIGDY nie usuwa wolumenów z danymi
	./scripts/dev-down.sh

dev-reset:   ## DESTRUKCYJNE: usuwa wolumeny DEV i odbudowuje środowisko od zera (wymaga potwierdzenia)
	./scripts/dev-reset.sh

dev-status:  ## Diagnostyka: kontenery, PostgreSQL, Redis, migracje, Celery
	./scripts/dev-status.sh

dev-logs:    ## Podgląd logów wszystkich usług (Ctrl+C aby wyjść; opcjonalny arg = liczba linii)
	./scripts/dev-logs.sh

dev-backup:  ## Backup bazy DEV do ./backups/ (zawsze przez kontener, nigdy lokalny pg_dump)
	./scripts/dev-backup.sh

dev-restore: ## Odtworzenie backupu: make dev-restore FILE=./backups/nazwa.dump
	./scripts/dev-restore.sh $(FILE)

test-run:    ## Środowisko TEST — szybkie testy jednostkowe (efemeryczne, sprząta po sobie)
	./scripts/test-run.sh

e2e:         ## Środowisko E2E — testy Playwright (efemeryczne, sprząta po sobie)
	./scripts/e2e-run.sh

verify:      ## Pełna weryfikacja przed push/PR: make check + TEST (release scripts + pełny suite)
	./scripts/verify.sh

preprod:     ## Dowolna komenda compose na PRE-PROD z wymuszoną izolacją od DEV: make preprod ARGS="up -d"
	./scripts/preprod-run.sh $(ARGS)

preprod-deploy: ## PRE-PROD: bezpieczna kolejność (Database Release -> Application Release -> start)
	./scripts/preprod-deploy.sh

preprod-status: ## PRE-PROD: diagnostyka (kontenery, PostgreSQL, Redis, migracje, Celery, wolumen ADR-025)
	./scripts/preprod-status.sh

preprod-logs:   ## PRE-PROD: podgląd logów (Ctrl+C aby wyjść)
	./scripts/preprod-run.sh logs -f --tail=100

preprod-down:   ## PRE-PROD: zatrzymanie (bez -v — sam skrypt ostrzega, jeśli dodasz ARGS="down -v")
	./scripts/preprod-run.sh down
