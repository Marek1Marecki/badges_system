#!/usr/bin/env bash
# AUDYT-151: Jednorazowy skrypt czyszczący Docker po nieudanych testach.
# Używa aggressive GC: -a (wszystkie nieużywane obrazy), --volumes, filtr until=24h.
#
# UŻYCIE:
#   ./scripts/cleanup_docker.sh           # dry-run najpierw, potem cleanup
#   FORCE=1 ./scripts/cleanup_docker.sh   # bezpytnie
set -euo pipefail

DRY_RUN="${DRY_RUN:-0}"
FORCE="${FORCE:-0}"

if [ "${DRY_RUN}" = "1" ]; then
    echo "=== DRY RUN ==="
    docker system df
    docker images --filter "dangling=true" -q | wc -l | xargs echo "Dangling images:"
    docker volume ls --filter "dangling=true" -q | wc -l | xargs echo "Dangling volumes:"
    exit 0
fi

echo "=== Przed czyszczeniem ==="
docker system df

if [ "${FORCE}" != "1" ]; then
    read -r -p "Usunąć nieużywane obrazy, wolumeny i sieci (until=24h)? [y/N] " resp
    [[ "${resp}" =~ ^[Yy]$ ]] || { echo "Anulowano."; exit 1; }
fi

# Przerywamy tylko jeśli nie ma uruchomionych kontenerów CI
running=$(docker ps -q | wc -l)
if [ "${running}" -gt 0 ]; then
    echo "OSTRZEŻENIE: ${running} kontenerów jest aktualnie uruchomionych:"
    docker ps --format "  {{.ID}} {{.Image}} {{.Status}}"
    if [ "${FORCE}" != "1" ]; then
        read -r -p "Mimo to wyczyścić? [y/N] " resp2
        [[ "${resp2}" =~ ^[Yy]$ ]] || { echo "Anulowano."; exit 1; }
    fi
fi

echo "=== Czyszczenie ==="
docker system prune -a -f --volumes --filter "until=24h" || true

echo "=== Po czyszczeniu ==="
docker system df
