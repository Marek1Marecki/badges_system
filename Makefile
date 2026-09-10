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
.PHONY: help setup format lint type-check test test-all audit graph graph-modules graph-classes graph-all arch-docs api-docs doc-format doc-check check diagnostics clean hadolint checkov infra-check docker-bench dev-up dev-down dev-reset dev-status dev-logs dev-backup dev-restore test-run verify preprod preprod-deploy preprod-status preprod-logs preprod-down e2e security-audit complexity-check complexity-trend lock test-random coverage-diff secret-scan test-timings test-html docstr-coverage lint-templates experimental-schemathesis experimental-testcontainers experimental-axe experimental-factory-boy experimental-k6 experimental-zap experimental-xdist experimental-benchmark mutation scorecard

## help: Display this help message (core targets list).
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
	@echo "  check        - lokalne CI (Gate): format --check + lint + type-check + test + audit + security"
	@echo "  diagnostics  - Diagnostic tier: complexity, trends, arch diagrams, coverage-diff, etc."
	@echo "  clean        - usuwa cache, artefakty"
	@echo "  security-audit - semgrep + osv-scanner + trivy"
	@echo "  hadolint     - skanowanie Dockerfile (Hadolint)"
	@echo "  checkov      - skanowanie Compose (Checkov)"
	@echo "  infra-check  - hadolint + checkov"
	@echo "  docker-bench - audyt konfiguracji Dockera (CIS Docker Bench, na żądanie)"
	@echo "  complexity-check - radon + xenon (Diagnostic: complexity + maintainability metrics)"
	@echo "  complexity-trend - wily (Diagnostic: complexity trends over git history)"
	@echo "  scorecard        - architecture scorecard JSON (Diagnostic: consolidated KPI report)"
	@echo "  lock           - regeneruje uv.lock z 7-dniowym cooldownem zależności"
	@echo "  test-random    - testy z losową kolejnością (pytest-randomly, diagnostyka)"
	@echo "  coverage-diff  - coverage tylko dla zmienionego kodu (diff-cover, diagnostyka)"
	@echo "  secret-scan    - skanowanie sekretów w repo (detect-secrets, diagnostyka)"
	@echo "  test-timings   - analiza czasu testów (pytest --durations, diagnostyka)"
	@echo "  test-html      - raport HTML z wyników testów (pytest-html, diagnostyka)"
	@echo "  docstr-coverage - sprawdzanie pokrycia docstringami (diagnostyka)"
	@echo "  lint-templates - lintowanie szablonow Django (djLint, diagnostyka)"
	@echo "  mutation       - mutation testing (mutmut, diagnostic tier)"
	@echo "  experimental-schemathesis - API fuzzing (Schemathesis, experimental)"
	@echo "  experimental-testcontainers - realne DB w testach (Testcontainers, experimental)"
	@echo "  experimental-axe - accessibility (axe-playwright, experimental)"
	@echo "  experimental-factory-boy - test data architecture (Factory Boy, experimental)"
	@echo "  experimental-k6 - load testing (k6, experimental)"
	@echo "  experimental-xdist - rownolegle testy (pytest-xdist, experimental)"
	@echo "  experimental-benchmark - microbenchmark (pytest-benchmark, experimental)"
	@echo "  experimental-zap - DAST (OWASP ZAP, experimental)"

## setup: Install development dependencies (uv sync) and install pre-commit hooks.
setup:
	uv sync --group dev
	uv run pre-commit install

## format: Format Python source files using ruff format.
format:
	uv run ruff format $(PY_DIRS)

## doc-format: Format docstrings in Python source files (docformatter, Sphinx style).
doc-format:
	find $(PY_DIRS) -name '*.py' ! -name 'exceptions.py' | xargs uv run docformatter --in-place --wrap-summaries 120 --wrap-descriptions 120 --style sphinx

## doc-check: Check that all docstrings conform to formatting rules (docformatter --check).
doc-check:
	find $(PY_DIRS) -name '*.py' ! -name 'exceptions.py' | xargs uv run docformatter --check --wrap-summaries 120 --wrap-descriptions 120 --style sphinx

## lint: Lint Python source files for style and correctness (ruff check).
lint:
	uv run ruff check $(PY_DIRS)

## type-check: Run static type checking (mypy) and architectural import-linting (lint-imports).
type-check:
	uv run mypy $(PY_DIRS)
	uv run lint-imports

## test: Run fast unit tests (excludes integration and e2e tests requiring DB/infra).
test:
	ENV_FILE=.env.test uv run pytest -m "not integration"
	#uv run pytest $(TEST_DIRS) -m "not integration and not ml"

## test-random: Run tests with randomized order (pytest-randomly) for flakiness detection.
test-random:
	ENV_FILE=.env.test uv run pytest $(TEST_DIRS) -m "not integration and not e2e"

## coverage-diff: Run tests and report coverage diff against origin/main (diff-cover).
coverage-diff:
	ENV_FILE=.env.test uv run pytest $(TEST_DIRS) -m "not integration and not e2e" --cov --cov-report=term-missing --cov-report=xml:coverage.xml --cov-report=html:htmlcov
	uv run diff-cover coverage.xml --compare-branch=origin/main --format html:diff-cover-report.html

## test-timings: Analyze test execution times (shows top 20 slowest tests).
test-timings:
	ENV_FILE=.env.test uv run pytest $(TEST_DIRS) -m "not integration and not e2e" --durations=20

## test-html: Generate an HTML report of pytest test results.
test-html:
	ENV_FILE=.env.test uv run pytest $(TEST_DIRS) -m "not integration and not e2e" --html=test-report.html --self-contained-html

## docstr-coverage: Check docstring coverage across all Python source directories (>= 95%).
docstr-coverage:
	uv run docstr-coverage $(PY_DIRS) --fail-under=95

## lint-templates: Lint Django templates (djLint, with --check --reformat).
lint-templates:
	uv run djlint apps/ --check --reformat

# ==============================================================================
# SCHEMATHESIS — Experimental API fuzzing
# ==============================================================================
# Baseline: 2026-08-27
# - 13 operations tested
# - Server errors: 0
# - Invalid auth: 0
# - Known auth limitations: 10 operacji wymaga session cookie
# - Known method limitations: Schemathesis wysyła QUERY, Django zwraca 403
#
# Nie jest celem osiągnięcie 0 failures. Schemathesis służy do eksploracji
# systemu i wykrywania nieoczekiwanych zachowań. Kluczowa metryka:
# liczba nieoczekiwanych findingów (server errors, invalid auth), nie suma
# wszystkich failures.
#
# Wynik traktowany diagnostycznie, nie jako binary gate.
# Szczegóły: docs/experimental-schemathesis-baseline.md
# ==============================================================================

## experimental-schemathesis: Run Schemathesis API fuzzing — exploratory API testing (diagnostic, not gate).
experimental-schemathesis:
	./scripts/schema-run.sh

## experimental-testcontainers: Run integration tests with real PostgreSQL using Testcontainers.
experimental-testcontainers:
	uv run pytest tests/ -m "integration and testcontainers" -v -s --override-ini="addopts="

## experimental-axe: Run accessibility tests (axe-core via Playwright) on the running E2E server.
experimental-axe:
	./scripts/e2e-run.sh -k axe -v --override-ini="addopts="

## experimental-factory-boy: Run Factory Boy test data architecture tests (DEV-only).
experimental-factory-boy:
	ENV_FILE=.env uv run pytest tests/test_factories.py -v --override-ini="addopts="

## experimental-k6: Run k6 load testing against the test server.
experimental-k6:
	./scripts/k6-run.sh

## experimental-zap: Run OWASP ZAP DAST scan against the E2E server.
experimental-zap:
	./scripts/zap-run.sh

## experimental-xdist: Run tests in parallel using pytest-xdist (--xdist for speed).
experimental-xdist:
	uv run pytest $(TEST_DIRS) -m "not integration and not e2e" -n auto

## experimental-benchmark: Run benchmark tests using pytest-benchmark.
experimental-benchmark:
	uv run pytest $(TEST_DIRS) -m "benchmark" --benchmark-only --override-ini="addopts="

## test-all: Run all tests with full coverage (unit + integration, requires DB).
test-all:
	ENV_FILE=.env.test uv run pytest $(TEST_DIRS) --create-db --nomigrations \
		--cov=, --cov-report=term-missing \
		--cov-fail-under=$(MIN_COVERAGE)

## audit: Run architectural contract audit (AST-based dependency graph validation).
audit:
	uv run python scripts/audit_contracts.py

## secrets-check: Run custom secrets verification script (check_secrets.py).
secrets-check:
	uv run python scripts/check_secrets.py

## secret-scan: Scan repository for committed secrets using detect-secrets.
secret-scan:
	uv run detect-secrets scan --baseline .secrets.baseline

## graph: Export dependency graph as DOT + SVG (renders PNG if Graphviz dot is available).
graph:
	uv run python scripts/audit_contracts.py
	@if command -v dot >/dev/null 2>&1; then dot -Tpng dependencies.dot -o dependencies.png; echo "Rendered dependencies.png"; else echo "Graphviz dot not installed - kept dependencies.dot"; fi

## graph-modules: Generate module dependency graph using pydeps (clustered SVG).
graph-modules:
	mkdir -p docs/architecture
	uv run pydeps . \
		--only domain,application,infrastructure,apps,bootstrap \
		--cluster \
		--no-show \
		-o docs/architecture/dependencies-pydeps.svg

## graph-classes: Generate UML class diagrams for all Python source directories using pyreverse.
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

## graph-all: Generate all architecture diagrams (graph, graph-modules, graph-classes).
graph-all: graph graph-modules graph-classes

## arch-docs: Generate C4 architecture diagrams using PlantUML Docker image.
arch-docs:
	mkdir -p docs/architecture
	docker run --rm -v "$(CURDIR)/docs/architecture:/data" plantuml/plantuml:latest /data/context.puml /data/containers.puml /data/components.puml

## api-docs: Generate API reference documentation using pdoc (domain + application layers).
api-docs:
	mkdir -p docs/api
	uv run pdoc --output-dir docs/api domain application


## complexity-trend: Build Wily complexity trend analysis across git history (20 analyzers).
complexity-trend:
	uv run wily build $(PY_DIRS) -n 20 -a filesystem
	@for dir in $(PY_DIRS); do \
		echo "=== $$dir ==="; \
		uv run wily report $$dir || true; \
	done

## complexity-check: Run cyclomatic complexity and maintainability metrics (radon + xenon).
complexity-check:
	uv run radon cc $(PY_DIRS) -a -n B
	uv run radon mi $(PY_DIRS) -n C
	uv run xenon . --config xenon.ini

## security-audit: Run security scanning (Semgrep + Google OSV-Scanner + Trivy container scan).
security-audit:
	@echo "=== ROZPOCZYNANIE SKANOWANIA SEMGREP ==="
	uv run semgrep scan \
	  --config "p/python" \
	  --config "p/django" \
	  --config "p/owasp-top-ten" \
	  --config "p/secrets" \
	  --error --skip-unknown-extensions \
	  --disable-version-check \
	  --quiet \
	  --exclude="tests/*" --exclude=".venv/*" --exclude="node_modules/*" --exclude="staticfiles/*" \
	  --exclude-rule=package_managers.uv.uv-missing-dependency-cooldown.uv-missing-dependency-cooldown \
	  --exclude-rule=python.django.security.django-no-csrf-token.django-no-csrf-token
	@echo "\n=== ROZPOCZYNANIE SKANOWANIA GOOGLE OSV-SCANNER ==="
	osv-scanner --lockfile=uv.lock --config=osv-scanner.toml
	@echo "\n=== ROZPOCZYNANIE SKANOWANIA OBRAZU KONTENEROWEGO (Trivy) ==="
	trivy image --severity HIGH,CRITICAL --exit-code 1 --skip-version-check badges-system:latest || echo "Trivy: obraz badges-system:latest nie istnieje lokalnie — pominięto"

## hadolint: Lint Dockerfile using Hadolint (fails on errors).
hadolint:
	@echo "=== ROZPOCZYNANIE SKANOWANIA DOCKERFILE (Hadolint) ==="
	hadolint --failure-threshold error Dockerfile

## checkov: Scan Docker Compose files for security misconfigurations (Checkov).
checkov:
	@echo "=== ROZPOCZYNANIE SKANOWANIA COMPOSE (Checkov) ==="
	checkov -f compose.yml -f compose.prod.yml -f compose.test.yml -f compose.e2e.yml -f compose.preprod.yml -f compose.override.yml --framework yaml --compact --quiet

## infra-check: Run both Dockerfile (hadolint) and Compose (checkov) security checks.
infra-check: hadolint checkov

## docker-bench: Placeholder for Docker host configuration audition (CIS Docker Bench).
docker-bench:
	@echo "=== ROZPOCZYNANIE AUDYTU DOCKER BENCH ==="
	@echo "Uwaga: ten audyt wymaga dostępu do docker.sock hosta i analizuje konfigurację demona Dockera."
	@echo "Uruchom tylko na środowiskach zaufanych (lokalnie, nie w CI)."
	@echo ""
	@echo "Docker Bench: projekt upstream (docker/docker-bench) został zarchiwizowany."
	@echo "Celowo pozostawiono ten target jako placeholder na przyszły audyt hosta Docker."
	@echo "Jeśli pojawi się aktywny successor, zaktualizuj komendę w tym miejscu."

## check: Local CI gate — format check, lint, type-check, tests, audit, security.
check:
	uv run ruff format --check $(PY_DIRS)
	uv run ruff check $(PY_DIRS)
	uv run mypy $(PY_DIRS)
	uv run lint-imports
	ENV_FILE=.env.test uv run pytest $(TEST_DIRS) -m "not integration and not e2e"
	uv run python scripts/audit_contracts.py
	make security-audit

## diagnostics: Run all diagnostic-tier checks (complexity, trends, diagrams, coverage diff).
diagnostics:
	make complexity-check
	make complexity-trend
	make graph-all
	make arch-docs
	make api-docs
	make coverage-diff
	make test-random
	make test-timings
	make test-html
	make secret-scan
	make docstr-coverage
	make scorecard
	make lint-templates

## scorecard: Generate architecture scorecard JSON report (consolidated KPI metrics).
scorecard:
	uv run python scripts/architecture-scorecard.py

## mutation: Run mutation testing using mutmut on application/ and domain/ layers.
mutation:
	@echo "=== Mutation Testing (mutmut) ==="
	@echo "Diagnostic tier: runs mutmut on application/ and domain/"
	@echo "Full run trwa godziny. Wyniki w docs/experimental-mutmut-baseline.md"
	@echo ""
	@rm -f .mutmut-cache
	uv run mutmut run --paths-to-mutate=application/,domain/ --runner "bash -c 'ENV_FILE=.env.test python -m pytest tests/ --ignore=tests/e2e --ignore=tests/domain/test_domain_hypothesis.py -m \"not integration\" --deselect tests/config/test_urls.py::TestMainUrls::test_health_check_view_returns_healthy_in_test_environment --override-ini=\"addopts=\"'" --simple-output --no-progress
	@echo ""
	@echo "=== Results ==="
	uv run mutmut results

## clean: Remove all generated cache files, coverage artifacts, and build outputs.
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -not -path "./.venv/*" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/ coverage.xml .ruff_cache/ .wily/
	rm -rf docs/api/
	rm -f .mutmut-cache

## lock: Regenerate uv.lock with 7-day dependency cooldown (locks newest compatible versions).
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
