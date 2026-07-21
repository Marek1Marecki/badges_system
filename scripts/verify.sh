#!/bin/bash
set -e

# ==============================================================================
# scripts/verify.sh — pełna lokalna weryfikacja przed `git push` / Pull Requestem
#
# CELOWO NIE duplikuje logiki `make check` (ruff, mypy, lint-imports, audit,
# szybkie testy jednostkowe) — ten skrypt tylko ją WYWOŁUJE, a potem dokłada
# wyłącznie to, czego `make check` z definicji nie robi, bo wymaga
# prawdziwej infrastruktury (PostgreSQL/PostGIS, Redis). Wasz własny
# kontrakt (01-makefile-contract.md) mówi wprost: "`make check` jest
# bezstanowy... może być uruchamiany gdy baza danych jest niedostępna" —
# gdyby ten skrypt powtarzał ruff/mypy, mielibyście dwa źródła prawdy dla
# tej samej kontroli.
#
# Kolejność: najtańsze i najszybsze kontrole pierwsze (Fail-Fast,
# architecture-principles.md, Zasada 3) — sens ma przerwać na literówce
# wykrytej przez ruff w 2 sekundy, zanim zaczniemy budować i podnosić
# całą efemeryczną infrastrukturę Dockera.
#
# Użycie:
#   ./scripts/verify.sh            (lub: make verify)
# ==============================================================================

echo "=== [1/2] make check — ruff, mypy, lint-imports, audit, szybkie testy ==="
make check

echo ""
echo "=== [2/2] Środowisko TEST — release scripts + pełny zestaw testów ==="
./scripts/test-run.sh --full

echo ""
echo "=== VERIFY: wszystko przeszło. Bezpiecznie wypychaj zmiany / otwieraj PR. ==="
