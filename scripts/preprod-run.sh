#!/bin/bash
set -euo pipefail

# ==============================================================================
# scripts/preprod-run.sh — wrapper wymuszający osobną przestrzeń nazw PRE-PROD
#
# PROBLEM, który ten skrypt rozwiązuje: gdy PRE-PROD uruchamiane jest z tego
# samego katalogu repo co DEV (ten sam host, ta sama maszyna), samo
# `docker compose -f compose.yml -f compose.preprod.yml up` BEZ jawnej nazwy
# projektu dostaje DOMYŚLNĄ nazwę projektu Compose — nazwę katalogu (np.
# `badges_system`) — DOKŁADNIE TĘ SAMĄ, której używa zwykłe `docker compose up`
# dla DEV. Efekt: kontenery PRE-PROD (`db`, `redis`) nazywałyby się
# identycznie jak kontenery DEV (`badges_system-db-1`) — Compose operowałoby
# na TYM SAMYM kontenerze/procesie, nie tylko tym samym wolumenie (to jest
# poważniejsze i bardziej bezpośrednie ryzyko niż kolizja nazw wolumenów
# naprawiona w Rundzie 10 — tu kolidowałaby sama TOŻSAMOŚĆ procesu bazy).
#
# ROZWIĄZANIE: nazwa projektu jest wymuszana jako zmienna POWŁOKI w tym
# skrypcie, NIE wpisana do współdzielonego pliku `.env` w katalogu głównym
# — gdyby `COMPOSE_PROJECT_NAME=badges_preprod` trafiło do `.env`, zmieniłoby
# to też domyślną nazwę projektu dla zwykłego `docker compose up` (DEV),
# bo Docker Compose auto-ładuje ten sam plik `.env` dla KAŻDEGO wywołania
# z tego katalogu, niezależnie od tego, które pliki compose*.yml są użyte.
#
# Ten skrypt jest jedynym miejscem, gdzie ta nazwa jest zdefiniowana — jeśli
# kiedykolwiek trzeba ją zmienić, zmienia się w jednym miejscu, nie w każdej
# komendzie z osobna.
#
# Użycie — dowolna komenda docker compose, z automatycznie wstrzykniętą
# nazwą projektu i plikami compose.yml + compose.preprod.yml:
#   ./scripts/preprod-run.sh up -d
#   ./scripts/preprod-run.sh run --rm web ./scripts/release-database.sh
#   ./scripts/preprod-run.sh run --rm web ./scripts/release-application.sh
#   ./scripts/preprod-run.sh exec web ./scripts/bootstrap.sh <snapshot_id>
#   ./scripts/preprod-run.sh logs -f
#   ./scripts/preprod-run.sh ps
#   ./scripts/preprod-run.sh down          (BEZ -v — patrz ostrzeżenie niżej)
# ==============================================================================

PROJECT_NAME="badges_preprod"

if [ "$#" -eq 0 ]; then
    echo "Użycie: ./scripts/preprod-run.sh <dowolna komenda docker compose>"
    echo "Przykłady:"
    echo "  ./scripts/preprod-run.sh up -d"
    echo "  ./scripts/preprod-run.sh run --rm web ./scripts/release-database.sh"
    echo "  ./scripts/preprod-run.sh ps"
    exit 1
fi

# Ostrzeżenie widoczne przy każdym wywołaniu 'down' z '-v' — na PRE-PROD nie
# ma automatycznego backupu jak w dev-reset.sh (to środowisko nie jest
# efemeryczne z założenia), więc '-v' tutaj jest w pełni świadomą decyzją
# operatora, nie czymś co ten skrypt powinien ułatwiać przez milczenie.
for arg in "$@"; do
    if [ "$arg" = "down" ]; then
        for check_arg in "$@"; do
            if [ "$check_arg" = "-v" ] || [ "$check_arg" = "--volumes" ]; then
                echo "UWAGA: 'down -v' na PRE-PROD usunie wolumeny"
                echo "  badges_system_preprod_postgis_data / ..._redis_data."
                echo "  To NIE jest srodowisko efemeryczne - upewnij sie, ze to zamierzone."
                read -r -p "Kontynuowac? [t/N]: " confirm
                if [ "$confirm" != "t" ] && [ "$confirm" != "T" ]; then
                    echo "Anulowano."
                    exit 1
                fi
            fi
        done
        break
    fi
done

# ==============================================================================
# Ładowanie lokalnych sekretów (tylko na czas manualnych testów)
# Na produkcji wartości te będą pochodzić bezpośrednio z systemu CI/CD (GitHub Secrets)
# ==============================================================================
if [ -f .env.preprod.secrets ]; then
    set -a
    source .env.preprod.secrets
    set +a
fi

exec docker compose -p "${PROJECT_NAME}" -f compose.yml -f compose.preprod.yml "$@"
