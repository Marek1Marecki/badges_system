# ===============================
# CONFIG
# ===============================
PY_DIRS := domain application infrastructure apps bootstrap scripts
DOCFORMATTER_EXCLUDE := --exclude application/exceptions.py --exclude domain/exceptions.py --exclude infrastructure/exceptions.py
TEST_DIRS := tests
MIN_COVERAGE ?= 80
export PATH := /home/dominik/.local/bin:$(PATH)

# ===============================
# CORE
# ===============================
.PHONY: help setup format lint type-check test test-all audit secrets-check graph graph-modules graph-classes graph-all arch-docs api-docs doc-format doc-check check clean hadolint checkov infra-check dev-up dev-down dev-reset dev-status dev-logs dev-backup dev-restore test-run verify preprod preprod-deploy preprod-status preprod-logs preprod-down e2e security-audit complexity-check complexity-trend lock

help:
	@echo "CORE targets:"
	@echo "  setup        - instalacja zależności i pre-commit"
	@echo "  format       - formatowanie kodu (ruff)"
	@echo "  doc-format    - formatowanie docstringow (docformatter)"
	@echo "  doc-check    - sprawdzanie formatowania docstringow (docformatter --check)"
	@echo "  lint         - linting kodu"
	@echo "  type-check   - mypy + lint-imports"
	@echo "  test         - szybkie testy jednostkowe"
	@echo "  test-all     - wszystkie testy (jednostkowe + integracyjne) używane w CI/CD"
	@echo "  audit        - audit architektoniczny (AST)"
	@echo "  graph        - eksport grafu zaleznosci (DOT + SVG, opcjonalnie PNG)"
	@echo "  graph-modules - graf zaleznosci modulow (pydeps -> SVG)"
	@echo "  graph-classes - diagramy klas UML (pyreverse -> PNG)"
	@echo "  graph-all    - wszystkie diagramy architektury"
	@echo "  arch-docs    - generowanie diagramów PlantUML (C4)"
	@echo "  api-docs     - generowanie dokumentacji API (pdoc)"
	@echo "  check        - lokalne CI: format --check + lint + type-check + test + audit + complexity-check + security-audit + infra-check"
	@echo "  clean        - usuwa cache, artefakty"
	@echo "  security-audit - semgrep + osv-scanner + trivy"
	@echo "  complexity-check - radon + xenon (complexity + maintainability metrics)"
	@echo "  complexity-trend - wily (complexity trends over git history)"
	@echo "  lock           - regeneruje uv.lock z 7-dniowym cooldownem zależności"

setup:
	uv sync --group dev
	uv run pre-commit install

format:
	uv run ruff format $(PY_DIRS)

doc-format:
	find $(PY_DIRS) -name '*.py' ! -name 'exceptions.py' | xargs uv run docformatter --in-place --wrap-summaries 120 --wrap-descriptions 120 --style sphinx

doc-check:
	find $(PY_DIRS) -name '*.py' ! -name 'exceptions.py' | xargs uv run docformatter --check --wrap-summaries 120 --wrap-descriptions 120 --style sphinx

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

graph-modules:
	mkdir -p docs/architecture
	uv run pydeps . \
		--only domain,application,infrastructure,apps,bootstrap \
		--cluster \
		--no-show \
		-o docs/architecture/dependencies-pydeps.svg

graph-classes:
	mkdir -p docs/architecture /tmp/pyreverse-domain /tmp/pyreverse-application /tmp/pyreverse-infrastructure /tmp/pyreverse-apps
	uv run pyreverse domain \
		-o png \
		-p badges_system \
		--output-directory /tmp/pyreverse-domain \
		--source-roots .
	uv run pyreverse application \
		-o png \
		-p badges_system \
		--output-directory /tmp/pyreverse-application \
		--source-roots .
	uv run pyreverse infrastructure \
		-o png \
		-p badges_system \
		--output-directory /tmp/pyreverse-infrastructure \
		--source-roots .
	uv run pyreverse apps \
		-o png \
		-p badges_system \
		--output-directory /tmp/pyreverse-apps \
		--source-roots .
	cp /tmp/pyreverse-domain/classes_badges_system.png docs/architecture/classes-domain.png
	cp /tmp/pyreverse-application/classes_badges_system.png docs/architecture/classes-application.png
	cp /tmp/pyreverse-infrastructure/classes_badges_system.png docs/architecture/classes-infrastructure.png
	cp /tmp/pyreverse-apps/classes_badges_system.png docs/architecture/classes-apps.png
	rm -rf /tmp/pyreverse-*

graph-all: graph graph-modules graph-classes

arch-docs:
	mkdir -p docs/architecture
	docker run --rm -v "$(CURDIR)/docs/architecture:/data" plantuml/plantuml:latest /data/context.puml /data/containers.puml /data/components.puml

api-docs:
	mkdir -p docs/api
	uv run pdoc --output-dir docs/api domain application


complexity-trend:
	uv run wily build $(PY_DIRS) -n 20 -a filesystem
	@for dir in $(PY_DIRS); do \
		echo "=== $$dir ==="; \
		uv run wily report $$dir || true; \
	done

complexity-check:
	uv run radon cc $(PY_DIRS) -a -n B
	uv run radon mi $(PY_DIRS) -n C
	uv run xenon . --config xenon.ini

security-audit:
	@echo "=== ROZPOCZYNANIE SKANOWANIA SEMGREP ==="
	uv run semgrep scan \
	  --config "p/python" \
	  --config "p/django" \
	  --config "p/owasp-top-ten" \
	  --config "p/secrets" \
	  --error --skip-unknown-extensions \
	  --exclude="tests/*" --exclude=".venv/*" --exclude="node_modules/*" --exclude="staticfiles/*" \
	  --exclude-rule=package_managers.uv.uv-missing-dependency-cooldown.uv-missing-dependency-cooldown
	@echo "\n=== ROZPOCZYNANIE SKANOWANIA GOOGLE OSV-SCANNER ==="
	osv-scanner --lockfile=uv.lock --config=osv-scanner.toml
	@echo "\n=== ROZPOCZYNANIE SKANOWANIA OBRAZU KONTENEROWEGO (Trivy) ==="
	trivy image --severity HIGH,CRITICAL --exit-code 1 badges-system:latest || echo "Trivy: obraz badges-system:latest nie istnieje lokalnie — pominięto"

hadolint:
	@echo "=== ROZPOCZYNANIE SKANOWANIA DOCKERFILE (Hadolint) ==="
	hadolint --failure-threshold error Dockerfile

checkov:
	@echo "=== ROZPOCZYNANIE SKANOWANIA COMPOSE (Checkov) ==="
	checkov -f compose.yml -f compose.prod.yml -f compose.test.yml -f compose.e2e.yml -f compose.preprod.yml -f compose.override.yml --framework yaml --compact

infra-check: hadolint checkov

check:
	uv run ruff format --check $(PY_DIRS)
	uv run ruff check $(PY_DIRS)
	uv run mypy $(PY_DIRS)
	uv run lint-imports
	ENV_FILE=.env.test uv run pytest $(TEST_DIRS) -m "not integration and not e2e"
	uv run python scripts/audit_contracts.py
	make complexity-check
	make security-audit
	make infra-check

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -not -path "./.venv/*" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/ coverage.xml .ruff_cache/ .wily/
	rm -rf docs/api/

lock:
	uv lock --exclude-newer "7 days"

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
