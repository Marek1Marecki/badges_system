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
PYTEST_ARGS=()

for arg in "$@"; do
    if [ "$arg" = "--full" ]; then
        FULL=true
    else
        PYTEST_ARGS+=("$arg")
    fi
done

# Nazwa projektu unikalna per uruchomienie — ta sama izolacja co w README
# (zapobiega też kolizji tagów obrazów opisanej w historii zmian, Runda 6).
PROJECT="ci-$(date +%s)-$$"
COMPOSE=(docker compose -p "${PROJECT}" -f compose.yml -f compose.test.yml)

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

# Widoczne potwierdzenie izolacji — nie tylko deklaracja w komentarzu.
# Po incydencie z Rundy 9 (TEST po cichu dzielił nazwane wolumeny z DEV)
# wolimy to jawnie widzieć w logu każdego uruchomienia, niż zakładać, że
# konfiguracja compose zadziałała tak, jak zamierzono.
echo ""
echo "Wolumeny użyte przez ten przebieg TEST (muszą zawierać '${PROJECT}' lub '_test',"
echo "NIGDY nie mogą to być 'badges_system_postgis_data'/'badges_system_redis_data'):"
docker volume ls --filter "name=${PROJECT}" --format "  {{.Name}}"
docker volume ls --filter "name=_test_" --format "  {{.Name}}"

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
        "${COMPOSE[@]}" run --rm web -v
    else
        "${COMPOSE[@]}" run --rm web "${PYTEST_ARGS[@]}"
    fi
else
    echo ""
    echo "=== TEST: szybkie testy jednostkowe ==="
    if [ ${#PYTEST_ARGS[@]} -eq 0 ]; then
        "${COMPOSE[@]}" run --rm web
    else
        "${COMPOSE[@]}" run --rm web "${PYTEST_ARGS[@]}"
    fi
fi

echo ""
echo "=== TEST zakończony pomyślnie ==="
