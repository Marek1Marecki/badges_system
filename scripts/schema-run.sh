#!/bin/bash
set -euo pipefail

# ==============================================================================
# scripts/schema-run.sh — wrapper na środowisko E2E dla Schemathesis (API Fuzzing)
#
# Uruchamia efemeryczne środowisko E2E (compose.e2e.yml), czeka na gotowość
# serwera na porcie 8009, uruchamia Schemathesis fuzzer i sprząta po sobie.
#
# Użycie:
#   ./scripts/schema-run.sh                    # domyślny fuzz
#   ./scripts/schema-run.sh --with-pg-restore  # szybkie uruchomienie z pg_restore
#   ./scripts/schema-run.sh --scenario all     # pełny fuzz (domyślnie)
#
# Wszystko działa w izolowanym projekcie Compose i sprząta po sobie (down -v --remove-orphans).
# NIGDY nie łączy się z DEV (localhost:8005) ani PRE-PROD!
# ==============================================================================

SCHEMATHES_ARGS=()
WITH_PG_RESTORE=false

for arg in "$@"; do
    case "$arg" in
        --with-pg-restore)
            WITH_PG_RESTORE=true
            ;;
        *)
            SCHEMATHES_ARGS+=("$arg")
            ;;
    esac
done

PROJECT="schema-$(date +%s)-$$"
COMPOSE=(docker compose -p "${PROJECT}" -f compose.yml -f compose.test.yml -f compose.e2e.yml)

cleanup() {
    local exit_code=$?
    echo ""
    echo "=== Sprzątanie środowiska Schemathesis (projekt: ${PROJECT}) ==="
    "${COMPOSE[@]}" down -v --remove-orphans 2>/dev/null || true
    exit $exit_code
}
trap cleanup EXIT

echo "=== Schemathesis: budowa obrazu web-e2e (${PROJECT}) ==="
"${COMPOSE[@]}" build web-e2e

echo ""
echo "=== Schemathesis: uruchamianie infrastruktury (${PROJECT}) ==="
"${COMPOSE[@]}" up -d --wait db redis web-e2e

echo ""
echo "Wolumeny użyte przez ten przebieg:"
docker volume ls --filter "name=${PROJECT}" --format "  {{.Name}}"
docker volume ls --filter "name=_test_" --format "  {{.Name}}"

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
        echo "BŁĄD: Brak pliku data/reference/postgis_dump.custom. Uruchom export_reference_data --with-pg-dump na DEV."
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
echo "[3/3] Tworzenie konta admin i profilu turystycznego..."
"${COMPOSE[@]}" exec -T web-e2e python manage.py shell -c \
    "from django.contrib.auth import get_user_model; \
      User = get_user_model(); \
      user, _ = User.objects.get_or_create(username='admin', defaults={'email': 'admin@example.com', 'is_staff': True, 'is_superuser': True}); \
      user.set_password('admin'); \
      user.save(); \
      print('Admin user ready')"
"${COMPOSE[@]}" exec -T web-e2e python manage.py shell -c \
    "from apps.tourists.models import TouristProfile; \
      profile, _ = TouristProfile.objects.get_or_create(user_id=1, defaults={'nickname': 'admin_1', 'is_main_profile': True}); \
      print('Profile ready:', profile)"

echo ""
echo "[4/4] Oczekiwanie na gotowość serwera na http://localhost:8009/..."
for i in {1..60}; do
    if curl -s http://localhost:8009/ > /dev/null 2>&1; then
        break
    fi
    echo "Oczekiwanie na serwer (próba $i/60)..."
    sleep 2
done

echo ""
echo "=== Schemathesis: uruchamianie fuzzowania ==="
export BASE_URL=http://localhost:8009
if [ ${#SCHEMATHES_ARGS[@]} -eq 0 ]; then
    uv run schemathesis run http://localhost:8009/api/openapi.json --url=http://localhost:8009
else
    uv run schemathesis run "${SCHEMATHES_ARGS[@]}" --url=http://localhost:8009
fi

echo ""
echo "=== Schemathesis zakończony pomyślnie ==="
