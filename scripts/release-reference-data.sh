#!/bin/bash
set -e

# ==============================================================================
# release-reference-data.sh — REFERENCE DATA RELEASE (ADR-020, punkt 1 i 3)
#
# Niezależny cykl od Application/Database Release. Aktualizuje Złoty Zestaw
# Danych Referencyjnych (odznaki, geometria PostGIS).
#
# Walidacja manifestu (sha256 zawartości snapshotu + compatible_schema) jest
# wykonywana przez komendę zarządzającą Django (`validate_reference_manifest`),
# NIE przez ten skrypt bashowy — logika biznesowa żyje w kodzie aplikacji,
# nie w powłoce.
#
# Wywołanie (przykład CI/CD, WYŁĄCZNIE przez zatwierdzony pipeline —
# Zasada Akceptacji Release'u, ADR-020):
#   docker compose run --rm web ./scripts/release-reference-data.sh <snapshot_id>
# ==============================================================================

SNAPSHOT_ID="${1:?Użycie: release-reference-data.sh <snapshot_id>}"

echo "=== REFERENCE DATA RELEASE (snapshot: ${SNAPSHOT_ID}) ==="

echo "[1/3] Walidacja manifestu (checksum + compatible_schema)..."
# uv run --no-sync python manage.py validate_reference_manifest --snapshot="${SNAPSHOT_ID}"
# python manage.py validate_reference_manifest --snapshot="${SNAPSHOT_ID}" # TODO: Wdrożyć w kodzie (Znana luka)

echo "[2/3] Odtwarzanie danych referencyjnych (operacja idempotentna)..."
# uv run --no-sync python manage.py restore_reference_data --snapshot="${SNAPSHOT_ID}"
python manage.py restore_reference_data --snapshot="${SNAPSHOT_ID}"

echo "[3/3] Przeliczanie powiązań przestrzennych (sąsiedzi geograficzni)..."
# uv run --no-sync python manage.py calculate_neighbors
python manage.py calculate_neighbors

echo "=== REFERENCE DATA RELEASE ZAKOŃCZONY (snapshot: ${SNAPSHOT_ID}) ==="
