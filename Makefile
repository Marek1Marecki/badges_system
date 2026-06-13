# ===============================
# CONFIG
# ===============================
PY_DIRS := domain application infrastructure apps bootstrap scripts
TEST_DIRS := tests
MIN_COVERAGE ?= 80

# ===============================
# CORE
# ===============================
.PHONY: help setup format lint type-check test test-all audit secrets-check graph check clean

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
	uv run pytest $(TEST_DIRS) -m "not integration and not ml"

test-all:
	uv run pytest $(TEST_DIRS) --create-db --nomigrations \
		--cov=, --cov-report=term-missing \
		--cov-fail-under=$(MIN_COVERAGE)

audit:
	uv run python scripts/audit_contracts.py

secrets-check:
	uv run python scripts/check_secrets.py

graph:
	uv run python scripts/audit_contracts.py
	@if command -v dot >/dev/null 2>&1; then dot -Tpng dependencies.dot -o dependencies.png; echo "Rendered dependencies.png"; else echo "Graphviz dot not installed - kept dependencies.dot"; fi

check:
	uv run ruff format --check $(PY_DIRS)
	uv run ruff check $(PY_DIRS)
	uv run mypy $(PY_DIRS)
	uv run lint-imports
	uv run pytest $(TEST_DIRS) -m "not integration"
	uv run python scripts/audit_contracts.py

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -not -path "./.venv/*" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/ coverage.xml .ruff_cache/
