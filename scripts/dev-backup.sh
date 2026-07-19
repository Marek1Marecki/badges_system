#!/bin/bash
set -e

# ==============================================================================
# dev-backup.sh — backup bazy DEV do katalogu projektu (poza Dockerem)
#
# ZAWSZE przez `docker compose exec db pg_dump` (wersja pg_dump WEWNĄTRZ
# kontenera zawsze pasuje do wersji serwera) — NIGDY przez lokalnie
# zainstalowany pg_dump/pg_restore na hoście. Niedopasowanie wersji klienta
# i serwera (np. host ma 16.14, kontener ma 18.3) kończy się błędem
# "unsupported version" przy próbie odtworzenia.
#
# Format: custom (-Fc) — pozwala na selektywne/równoległe odtwarzanie przez
# pg_restore i jest zwykle mniejszy niż czysty SQL.
#
# Backupy trafiają do ./backups/ w katalogu projektu (dodaj do .gitignore —
# to są dane, nie kod) — NIGDY do wolumenu ani systemu plików kontenera,
# żeby przetrwały nawet `dev-reset`.
# ==============================================================================

mkdir -p ./backups

# UWAGA: ten skrypt działa NA HOŚCIE, nie w kontenerze — `.env` jest czytany
# automatycznie tylko przez `docker compose` (przy interpolacji ${VAR} w
# plikach compose*.yml), NIE trafia sam z siebie do zmiennych powłoki. Bez
# poniższego jawnego wczytania POSTGRES_USER/POSTGRES_DB byłyby tu zawsze
# puste (fallback na wartości domyślne poniżej, które mogą nie zgadzać się
# z rzeczywistą konfiguracją).
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
OUTFILE="./backups/badges_system_${TIMESTAMP}.dump"

echo "Tworzenie backupu: ${OUTFILE}"
docker compose exec -T db pg_dump \
    -U "${POSTGRES_USER:-postgres}" \
    -Fc \
    "${POSTGRES_DB:-badges_system_db}" \
    > "${OUTFILE}"

SIZE=$(du -h "${OUTFILE}" | cut -f1)
echo "Backup zapisany: ${OUTFILE} (${SIZE})"
echo "Odtworzenie: ./scripts/dev-restore.sh ${OUTFILE}"
