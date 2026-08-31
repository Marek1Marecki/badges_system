#!/bin/bash
set -euo pipefail

# ==============================================================================
# scripts/k6-run.sh — wrapper na środowisko E2E dla k6 Load Testing
#
# Uruchamia efemeryczne środowisko E2E (compose.e2e.yml), czeka na gotowość
# serwera na porcie 8009, uruchamia testy obciążeniowe k6 i sprząta po sobie.
#
# Użycie:
#   ./scripts/k6-run.sh                      # domyślny scenariusz (50 VUs, 4 min)
#   ./scripts/k6-run.sh --vus 100            # zmień liczbę VUs
#   ./scripts/k6-run.sh --duration 10m       # zmień całkowitą długość
#
# Wszystko działa w izolowanym projekcie Compose i sprząta po sobie (down -v --remove-orphans).
# NIGDY nie łączy się z DEV (localhost:8005) ani PRE-PROD!
# ==============================================================================

PYTEST_ARGS=()
K6_VUS=""
K6_DURATION=""
WITH_PG_RESTORE=false

for arg in "$@"; do
    case "$arg" in
        --vus=*)
            K6_VUS="${arg#*=}"
            ;;
        --duration=*)
            K6_DURATION="${arg#*=}"
            ;;
        --with-pg-restore)
            WITH_PG_RESTORE=true
            ;;
        *)
            PYTEST_ARGS+=("$arg")
            ;;
    esac
done

PROJECT="k6-$(date +%s)-$$"
COMPOSE=(docker compose -p "${PROJECT}" -f compose.yml -f compose.test.yml -f compose.e2e.yml)

cleanup() {
    local exit_code=$?
    echo ""
    echo "=== Sprzątanie środowiska k6 (projekt: ${PROJECT}) ==="
    "${COMPOSE[@]}" down -v --remove-orphans 2>/dev/null || true
    exit $exit_code
}
trap cleanup EXIT

echo "=== k6: budowa obrazu web-e2e (${PROJECT}) ==="
"${COMPOSE[@]}" build web-e2e

echo ""
echo "=== k6: uruchamianie infrastruktury (${PROJECT}) ==="
"${COMPOSE[@]}" up -d --wait db redis web-e2e

echo ""
echo "[1/3] Migracje bazy danych..."
for i in {1..30}; do
    if "${COMPOSE[@]}" exec -T web-e2e python manage.py migrate; then
        break
    fi
    echo "Migracja nieudana (próba $i/30), ponawiam za 2s..."
    sleep 2
done

echo ""
echo "[2/3] Wgrywanie Danych Referencyjnych (Golden Set)..."
if [ "$WITH_PG_RESTORE" = true ]; then
    if [ ! -f "data/reference/postgis_dump.custom" ]; then
        echo "BŁĄD: Brak pliku data/reference/postgis_dump.custom."
        exit 1
    fi
    POSTGRES_USER="${POSTGRES_USER:-postgres}"
    POSTGRES_DB="${POSTGRES_DB:-badges_system_db}"
    "${COMPOSE[@]}" exec -T db mkdir -p /dumps
    "${COMPOSE[@]}" cp data/reference/postgis_dump.custom db:/dumps/postgis_dump.custom
    "${COMPOSE[@]}" exec -T db pg_restore -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --no-owner -c --if-exists -1 /dumps/postgis_dump.custom
else
    "${COMPOSE[@]}" exec -T web-e2e python manage.py validate_reference_manifest
    for fixture in 01_regions.json.gz 02_tourist_objects.json.gz 03_badges.json.gz 04_osm_mappings.json.gz 05_badge_news.json.gz; do
        "${COMPOSE[@]}" exec -T web-e2e python manage.py loaddata "data/reference/${fixture}"
    done
fi

echo ""
echo "[3/3] Oczekiwanie na gotowość serwera na http://localhost:8009/..."
for i in {1..60}; do
    if curl -s http://localhost:8009/ > /dev/null 2>&1; then
        break
    fi
    echo "Oczekiwanie na serwer (próba $i/60)..."
    sleep 2
done

echo ""
echo "=== k6: uruchamianie testów obciążeniowych ==="
K6_ARGS=()
if [ -n "$K6_VUS" ]; then
    K6_ARGS+=("--vus" "$K6_VUS")
fi
if [ -n "$K6_DURATION" ]; then
    K6_ARGS+=("--duration" "$K6_DURATION")
fi

if [ ${#K6_ARGS[@]} -eq 0 ]; then
    EUIE_BASE_URL=http://localhost:8009 k6 run scripts/k6/load-test.js
else
    EUIE_BASE_URL=http://localhost:8009 k6 run "${K6_ARGS[@]}" scripts/k6/load-test.js
fi

echo ""
echo "=== k6 zakończony pomyślnie ==="
