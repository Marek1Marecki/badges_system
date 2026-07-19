#!/bin/bash
set -e

# ==============================================================================
# release-database.sh — DATABASE RELEASE (ADR-020, punkt 3 / ADR-024)
#
# Jedyna odpowiedzialność BIZNESOWA tego cyklu: migracje schematu bazy danych
# (w odróżnieniu od Application Release / Reference Data Release — patrz
# ADR-020, Release Separation). Krok lintera (niżej) nie jest wyjątkiem od
# tej zasady — to walidacja WEJŚCIOWA dla tej samej odpowiedzialności
# (sprawdzenie, że migracje które zaraz zostaną zastosowane są bezpieczne),
# analogicznie do tego, jak Application Release waliduje swoje wejście przez
# `migrate --check` przed właściwym działaniem (collectstatic).
# Musi zostać wykonany i POTWIERDZONY przed uruchomieniem nowych instancji
# Application Release korzystających ze zmienionego schematu
# (Zasada Kolejności Wdrożeń / rolling deployment safety).
#
# ADR-024 (Expand and Contract) wymaga statycznej introspekcji operacji
# migracji (whitelist: AddField(null=True)/AddIndexConcurrently/CreateModel
# dozwolone automatycznie; AlterField/RenameField/RunSQL/RunPython wymagają
# code review; RemoveField/DeleteModel są zablokowane). Podstawowe
# egzekwowanie tej reguły odbywa się w CI na etapie Pull Requestu — wywołanie
# lintera tutaj jest DRUGĄ linią obrony bezpośrednio przed zastosowaniem
# migracji na danym środowisku (defense in depth), nie zastępuje kontroli w PR.
# Linter musi być deterministyczny (ten sam wynik dla tych samych plików
# migracji niezależnie od środowiska) — nie może blokować release'u z powodów
# niezwiązanych z treścią migracji (np. losowość, zależność od czasu), żeby
# nie stać się przeszkodą dla uzasadnionych hotfixów.
#
# UWAGA: `manage.py lint_migrations` jest komendą zarządzającą Django, którą
# należy zaimplementować w kodzie aplikacji (poza zakresem tego repozytorium
# infrastruktury) — patrz ADR-024, punkt 6.
#
# Wywołanie (przykład CI/CD):
#   docker compose run --rm web ./scripts/release-database.sh
# ==============================================================================

echo "=== DATABASE RELEASE ==="

echo "[1/3] Linter migracji (ADR-024 — whitelist dozwolonych operacji)..."
# Pod `set -e` brak tej komendy w Django (Unknown command) i tak bezpiecznie
# przerwałby skrypt — poniższy warunek dodaje wyłącznie czytelniejszy
# komunikat diagnostyczny, żeby odróżnić "linter nie istnieje jeszcze w
# kodzie" od "linter istnieje i wykrył naruszenie whitelisty".
if ! uv run python manage.py lint_migrations; then
    echo "BŁĄD: 'manage.py lint_migrations' zakończył się niepowodzeniem."
    echo "Możliwe przyczyny: (a) komenda nie jest jeszcze zaimplementowana"
    echo "w kodzie aplikacji — patrz ADR-024 pkt 6 i README-infra.md, albo"
    echo "(b) wykryto migrację naruszającą whitelistę dozwolonych operacji."
    echo "W obu przypadkach: DATABASE RELEASE zatrzymany."
    exit 1
fi

echo "[2/3] Sprawdzanie zaległych migracji (plan)..."
uv run python manage.py showmigrations --plan

echo "[3/3] Wykonywanie migracji..."
uv run python manage.py migrate --noinput

echo "=== DATABASE RELEASE ZAKOŃCZONY ==="
