#!/bin/bash
set -e

# ==============================================================================
# dev-restore.sh — odtworzenie backupu DEV z pliku
#
# ZAWSZE przez `docker compose exec db pg_restore` — nigdy lokalny binarny
# pg_restore na hoście (niedopasowanie wersji klient/serwer kończy się
# błędem "unsupported version"). To NADPISUJE bieżącą zawartość bazy
# (--clean --if-exists) — wymaga jawnego potwierdzenia.
#
# Użycie:
#   ./scripts/dev-restore.sh ./backups/badges_system_20260719-120000.dump
# ==============================================================================

FILE="${1:?Użycie: dev-restore.sh <ścieżka_do_pliku.dump>}"

if [ ! -f "$FILE" ]; then
    echo "BŁĄD: plik nie istnieje: ${FILE}"
    exit 1
fi

# Patrz dev-backup.sh — to samo uzasadnienie: skrypt działa na hoście,
# .env trzeba wczytać jawnie.
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

echo "⚠️  To NADPISZE bieżącą zawartość bazy '${POSTGRES_DB:-badges_system_db}'"
echo "danymi z pliku: ${FILE}"
echo ""
read -r -p "Wpisz dokładnie 'odtworz-baze-dev' aby potwierdzić: " confirm

if [ "$confirm" != "odtworz-baze-dev" ]; then
    echo "Anulowano — baza nie została zmieniona."
    exit 1
fi

echo ""
echo "Odtwarzanie z ${FILE}..."
# --clean --if-exists: usuwa istniejące obiekty przed odtworzeniem, bez
# błędu jeśli czegoś jeszcze nie ma (świeża baza vs. już istniejąca).
docker compose exec -T db pg_restore \
    -U "${POSTGRES_USER:-postgres}" \
    -d "${POSTGRES_DB:-badges_system_db}" \
    --clean --if-exists --no-owner \
    < "$FILE"

echo "Odtworzono. Sprawdź stan: ./scripts/dev-status.sh"
