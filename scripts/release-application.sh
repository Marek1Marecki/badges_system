#!/bin/bash
set -e

# ==============================================================================
# release-application.sh — APPLICATION RELEASE (ADR-020, punkt 3)
#
# Zakłada, że DATABASE RELEASE został już wykonany i potwierdzony dla tego
# środowiska (Zasada Kolejności Wdrożeń). Ten skrypt to WERYFIKUJE — brak
# zgodności BLOKUJE wdrożenie, to nie jest krok wyłącznie diagnostyczny.
#
# Wywołanie (przykład CI/CD, PRZED przełączeniem ruchu na nowe instancje):
#   docker compose run --rm web ./scripts/release-application.sh
# ==============================================================================

echo "=== APPLICATION RELEASE ==="

# Kolejność celowa: operacje WYŁĄCZNIE ODCZYTUJĄCE / walidujące najpierw,
# zapis (collectstatic) dopiero po ich pomyślnym przejściu — zasada
# "fail fast before mutation". Poprzednia kolejność (collectstatic przed
# walidacją migracji) niepotrzebnie mutowała wolumen statyków nawet wtedy,
# gdy release i tak kończył się błędem na kroku migracji.

echo "[1/3] Walidacja zgodności migracji (gating)..."
# `migrate --check` to wbudowana flaga Django (od 3.1): zwraca kod wyjścia != 0
# i NIE APLIKUJE żadnej migracji, jeśli istnieją niezastosowane migracje.
# Celowo NIE parsujemy tekstu `showmigrations --plan` przez grep — format
# tego wyjścia jest szczegółem implementacyjnym Django i może się zmienić
# między wersjami, podczas gdy kod wyjścia `--check` jest stabilnym kontraktem.
if ! uv run python manage.py migrate --check; then
    echo "BŁĄD: wykryto niezastosowane migracje."
    echo "Database Release musi zostać wykonany PRZED Application Release."
    uv run python manage.py showmigrations --plan
    exit 1
fi
echo "Migracje zgodne — kontynuuję."

echo "[2/3] Zbieranie plików statycznych..."
uv run python manage.py collectstatic --noinput --clear

echo "[3/3] Kontrola wdrożeniowa Django (check --deploy)..."
uv run python manage.py check --deploy

echo "=== APPLICATION RELEASE ZAKOŃCZONY ==="
