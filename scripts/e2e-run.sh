#!/bin/bash
set -euo pipefail

# ==============================================================================
# scripts/e2e-run.sh — wrapper na środowisko E2E (Playwright, efemeryczne)
#
# Uruchamia serwer Django wewnątrz kontenera `web-e2e` (compose.e2e.yml),
# tworzy konto admin, czeka na gotowość na porcie 8009 i odpala testy e2e.
# Wszystko działa w izolowanym projekcie Compose i sprząta po sobie.
#
# Argumenty trafiają bezpośrednio do pytest (np. `-k nazwa_testu`, `-v`).
#
# ZAWSZE sprząta po sobie (down -v --remove-orphans) — również gdy coś
# zawiedzie (trap na EXIT).
#
# Użycie:
#   ./scripts/e2e-run.sh                           # wszystkie testy e2e (loaddata z JSON)
#   ./scripts/e2e-run.sh --with-pg-restore         # szybkie uruchomienie z pg_restore
#   ./scripts/e2e-run.sh -v                        # verbose
#   ./scripts/e2e-run.sh -k test_homepage          # konkretny test
# ==============================================================================

PYTEST_ARGS=()
WITH_PG_RESTORE=false

for arg in "$@"; do
    if [ "$arg" = "--with-pg-restore" ]; then
        WITH_PG_RESTORE=true
    else
        PYTEST_ARGS+=("$arg")
    fi
done

PROJECT="ci-$(date +%s)-$$"
COMPOSE=(docker compose -p "${PROJECT}" -f compose.yml -f compose.test.yml -f compose.e2e.yml)

cleanup() {
    local exit_code=$?
    echo ""
    echo "Sprzątanie środowiska E2E (projekt: ${PROJECT})..."
    "${COMPOSE[@]}" down -v --remove-orphans
    exit $exit_code
}
trap cleanup EXIT

echo "=== E2E: budowa obrazu web-e2e (${PROJECT}) ==="
"${COMPOSE[@]}" build web-e2e

echo ""
echo "=== E2E: uruchamianie infrastruktury i serwera Django (${PROJECT}) ==="
"${COMPOSE[@]}" up -d --wait db redis web-e2e

echo ""
echo "Wolumeny użyte przez ten przebieg E2E:"
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
    
    # Odczytaj dane dostępowe z .env (fallback na wartości domyślne)
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

echo "[4/4] Oczekiwanie na gotowość serwera na http://localhost:8009/..."
for i in {1..60}; do
    if curl -s http://localhost:8009/ > /dev/null; then
        break
    fi
    echo "Oczekiwanie na serwer (próba $i/60)..."
    sleep 2
done

echo ""
echo "=== E2E: uruchamianie testów Playwright ==="
if [ ${#PYTEST_ARGS[@]} -eq 0 ]; then
    "${COMPOSE[@]}" exec -T web-e2e uv run pytest tests/e2e -m e2e --no-header -q --override-ini="addopts="
else
    "${COMPOSE[@]}" exec -T web-e2e uv run pytest tests/e2e -m e2e "${PYTEST_ARGS[@]}" --override-ini="addopts="
fi

echo ""
echo "=== E2E zakończony pomyślnie ==="
