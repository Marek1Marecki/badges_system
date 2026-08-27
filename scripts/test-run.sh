#!/bin/bash
set -euo pipefail

# ==============================================================================
# scripts/test-run.sh — wrapper na środowisko TEST (efemeryczne, ADR-020)
#
# Domyślnie: szybkie testy jednostkowe (`pytest -m "not integration"` —
# domyślny CMD obrazu `testing`).
#
# --full: dodatkowo weryfikuje sam PROCES WDROŻENIA (nie tylko kod aplikacji)
#   przez uruchomienie release-database.sh i release-application.sh
#   przeciwko świeżej, efemerycznej bazie TEST, a potem odpala PEŁNY zestaw
#   testów (bez filtra markerów — łącznie z integracyjnymi). To jest
#   dokładnie ta sama para skryptów, której używacie w PRE-PROD/PROD —
#   TEST staje się miejscem, w którym sprawdzacie, że one w ogóle działają,
#   zanim ktokolwiek je uruchomi na środowisku z prawdziwymi danymi.
#
# Argumenty spoza `--full` trafiają bezpośrednio do pytest (nadpisują
# domyślny CMD obrazu — np. `-k nazwa_testu`, konkretna ścieżka pliku).
#
# ZAWSZE sprząta po sobie (down -v --remove-orphans) — również gdy testy
# lub release scripts zawiodą (trap na EXIT, nie tylko "happy path").
#
# Użycie:
#   ./scripts/test-run.sh                     # szybkie testy jednostkowe
#   ./scripts/test-run.sh --full              # + release scripts + pełny suite
#   ./scripts/test-run.sh -k test_poi_scoring  # dowolne argumenty pytest
#   ./scripts/test-run.sh --full -v            # pełny suite, verbose
# ==============================================================================

FULL=false
EXPORT_PG_DUMP=false
PYTEST_ARGS=()

for arg in "$@"; do
    if [ "$arg" = "--full" ]; then
        FULL=true
    elif [ "$arg" = "--export-pg-dump" ]; then
        EXPORT_PG_DUMP=true
    else
        PYTEST_ARGS+=("$arg")
    fi
done

# Nazwa projektu unikalna per uruchomienie — ta sama izolacja co w README
# (zapobiega też kolizji tagów obrazów opisanej w historii zmian, Runda 6).
PROJECT="ci-$(date +%s)-$$"
COMPOSE=(docker compose --env-file .env -p "${PROJECT}" -f compose.yml -f compose.test.yml)

cleanup() {
    local exit_code=$?
    echo ""
    echo "Sprzątanie środowiska TEST (projekt: ${PROJECT})..."
    "${COMPOSE[@]}" down -v --remove-orphans
    exit $exit_code
}
trap cleanup EXIT

echo "=== TEST: uruchamianie efemerycznej infrastruktury (${PROJECT}) ==="
"${COMPOSE[@]}" up -d --wait db redis

echo ""
echo "Oczekiwanie na gotowość bazy danych..."
for i in {1..30}; do
    if "${COMPOSE[@]}" exec -T db pg_isready -U "${POSTGRES_USER:-postgres}" >/dev/null 2>&1; then
        echo "✅ Baza danych jest gotowa po ${i} próbach"
        break
    fi
    echo "  próba ${i}/30: baza jeszcze niedostępna..."
    sleep 2
done

# Widoczne potwierdzenie izolacji — nie tylko deklaracja w komentarzu.
# Po incydencie z Rundy 9 (TEST po cichu dzielił nazwane wolumeny z DEV)
# wolimy to jawnie widzieć w logu każdego uruchomienia, niż zakładać, że
# konfiguracja compose zadziałała tak, jak zamierzono.
echo ""
echo "Wolumeny użyte przez ten przebieg TEST (muszą zawierać '${PROJECT}' lub '_test',"
echo "NIGDY nie mogą to być 'badges_system_postgis_data'/'badges_system_redis_data'):"
docker volume ls --filter "name=${PROJECT}" --format "  {{.Name}}"
docker volume ls --filter "name=_test_" --format "  {{.Name}}"

echo ""
echo "=== DIAGNOSTYKA: stan kontenerów i sieci Compose ==="
"${COMPOSE[@]}" ps || true
echo ""
echo "--- Sieci Compose ---"
"${COMPOSE[@]}" network ls || true
echo ""
echo "--- Szczegóły sieci projektu ---"
"${COMPOSE[@]}" network inspect "${PROJECT}_default" 2>/dev/null || "${COMPOSE[@]}" network inspect "badges_system_test_default" 2>/dev/null || true

if [ "$FULL" = true ]; then
    echo ""
    echo "=== TEST --full: weryfikacja PROCESU WDROŻENIA (nie tylko kodu) ==="

    echo "[1/2] Database Release (lint_migrations + migrate) na świeżej bazie TEST..."
    "${COMPOSE[@]}" run --rm web ./scripts/release-database.sh

    echo "[2/2] Application Release (migrate --check + collectstatic + check --deploy)..."
    "${COMPOSE[@]}" run --rm web ./scripts/release-application.sh

    echo ""
    echo "=== TEST --full: pełny zestaw testów (bez filtra markerów) ==="
    # Bez jawnego argumentu `run --rm web` użyłby domyślnego CMD obrazu
    # (`-m "not integration"`) — w trybie --full chcemy WSZYSTKO, więc
    # zawsze przekazujemy jawny argument, nawet gdy użytkownik nic nie podał.
    if [ ${#PYTEST_ARGS[@]} -eq 0 ]; then
        "${COMPOSE[@]}" run --rm web uv run pytest -v
    else
        "${COMPOSE[@]}" run --rm web uv run pytest "${PYTEST_ARGS[@]}"
    fi
else
    echo ""
    echo "=== TEST: szybkie testy jednostkowe ==="
    if [ ${#PYTEST_ARGS[@]} -eq 0 ]; then
        "${COMPOSE[@]}" run --rm web
    else
        "${COMPOSE[@]}" run --rm web uv run pytest "${PYTEST_ARGS[@]}"
    fi
fi

echo ""
echo "[3/3] Wgrywanie Danych Referencyjnych (Golden Set)..."
for fixture in 01_regions.json.gz 02_tourist_objects.json.gz 03_badges.json.gz 04_osm_mappings.json.gz 05_badge_news.json.gz; do
    "${COMPOSE[@]}" run --rm web python manage.py loaddata "data/reference/${fixture}"
done

if [ "$EXPORT_PG_DUMP" = true ]; then
    echo ""
    echo "=== EKSPORT DUMPA POSTGRESQL ==="
    set -a
    source .env
    set +a
    mkdir -p /tmp/ci-artifacts
    "${COMPOSE[@]}" exec -T db sh -c "mkdir -p /tmp/ci-artifacts"
    "${COMPOSE[@]}" exec -T db pg_dump -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-badges_system_db}" -Fc -f /tmp/ci-artifacts/postgis_dump.custom
    "${COMPOSE[@]}" cp db:/tmp/ci-artifacts/postgis_dump.custom "$PWD/postgis_dump.custom"
    echo "✅ Dump zapisany: $PWD/postgis_dump.custom"
fi

echo ""
echo "=== TEST zakończony pomyślnie ==="
