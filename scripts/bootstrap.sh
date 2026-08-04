#!/bin/bash
set -e

# ==============================================================================
# bootstrap.sh — jednorazowa inicjalizacja środowiska DEV/TEST/PRE-PROD
#
# NIE jest częścią entrypoint.sh ani release.sh — wywoływany RĘCZNIE, tylko
# przy zakładaniu nowego środowiska (ADR-020: Reference Data Release nie może
# być automatyczny/bezwarunkowy).
#
# WAŻNE (ADR-024): ten skrypt wywołuje `migrate` bezpośrednio, co na pierwszy
# rzut oka wygląda jak obejście zasady "migracje wyłącznie przez Database
# Release". To ŚWIADOMY, WĄSKI WYJĄTEK — dotyczy WYŁĄCZNIE nowego, PUSTEGO
# środowiska, na którym nie ma jeszcze żadnej wersji schematu ani żadnych
# działających instancji aplikacji, więc ryzyko rolling-deployment (dla
# którego istnieje Zasada Kolejności Wdrożeń) tu nie występuje. Ten skrypt
# NIGDY nie powinien być używany jako skrót zastępujący
# `release-database.sh` na środowisku, które już działa i ma dane.
#
# Guard: odmawia importu snapshotu, jeśli baza już zawiera dane referencyjne,
# chyba że podano --force. Chroni przed przypadkowym nadpisaniem "Złotej Bazy".
#
# Wywołanie:
#   docker compose exec web ./scripts/bootstrap.sh <snapshot_id> [--force]
# ==============================================================================

SNAPSHOT_ID="${1:?Użycie: bootstrap.sh <snapshot_id> [--force]}"
FORCE_FLAG=""
if [ "${2:-}" = "--force" ]; then
    FORCE_FLAG="--force"
fi

echo "=== BOOTSTRAP ŚRODOWISKA (snapshot: ${SNAPSHOT_ID}) ==="

echo "[1/4] Migracje bazy danych..."
python manage.py migrate --noinput

echo "[2/4] Walidacja i wgrywanie Danych Referencyjnych..."
# python manage.py validate_reference_manifest --snapshot="${SNAPSHOT_ID}" # TODO: wdrożyć w kodzie (znana luka)
python manage.py restore_reference_data ${FORCE_FLAG}

echo "[3/4] Przeliczanie sąsiadów geograficznych..."
python manage.py calculate_neighbors

echo "[4/4] Tworzenie superużytkownika (pomijane, jeśli już istnieje)..."
# UWAGA: celowo NIE używamy `|| true` wokół createsuperuser — to maskowałoby
# każdy błąd (np. brak połączenia z bazą, złą konfigurację), nie tylko
# "użytkownik już istnieje". Sprawdzamy istnienie jawnie i pomijamy krok tylko
# w tym jednym, oczekiwanym przypadku; każdy inny błąd przerywa skrypt (set -e).
SUPERUSER_EXISTS=$(python manage.py shell -c "
from django.contrib.auth import get_user_model
print(get_user_model().objects.filter(is_superuser=True).exists())
" 2>/dev/null | tail -n 1)

if [ "$SUPERUSER_EXISTS" = "True" ]; then
    echo "Superużytkownik już istnieje — pomijam."
else
    python manage.py createsuperuser --noinput
fi

echo "=== BOOTSTRAP ZAKOŃCZONY ==="
