#!/bin/bash
set -e

# ==============================================================================
# scripts/preprod-deploy.sh — bezpieczna kolejność wdrożenia na PRE-PROD
#
# Analogon dev-up.sh, ale dla PRE-PROD: zamiast pamiętać 3 osobne komendy
# (release-database.sh -> release-application.sh -> up -d) w poprawnej
# kolejności (ADR-020, Zasada Kolejności Wdrożeń), ten skrypt robi to
# za Ciebie, zawsze przez preprod-run.sh (izolacja nazwy projektu).
#
# CELOWO NIE buduje obrazu — Build Once, Deploy Many (ADR-020, pkt 5)
# wymaga, żeby obraz był zbudowany i otagowany W OSOBNYM, wcześniejszym
# kroku CI (docker build --target production ...). Ten skrypt zakłada,
# że IMAGE_NAME:IMAGE_TAG już istnieje.
#
# Użycie:
#   ./scripts/preprod-deploy.sh          (lub: make preprod-deploy)
# ==============================================================================

echo "=== PRE-PROD: Deploy (Database Release -> Application Release -> start) ==="

echo "[1/3] Database Release..."
./scripts/preprod-run.sh run --rm web ./scripts/release-database.sh

echo "[2/3] Application Release..."
./scripts/preprod-run.sh run --rm web ./scripts/release-application.sh

echo "[3/3] Start usług..."
./scripts/preprod-run.sh up -d

echo ""
echo "=== PRE-PROD: deploy zakończony. Sprawdź stan: make preprod-status ==="
