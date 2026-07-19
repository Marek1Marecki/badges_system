#!/bin/bash
set -e

# ==============================================================================
# entrypoint.sh — WYŁĄCZNIE start procesu. Zero migracji, zero collectstatic.
# Migracje/release są osobnymi, kontrolowanymi krokami CI/CD (ADR-020,
# Zasada Akceptacji Release'u). Ten skrypt tylko czeka na bazę i odpala CMD.
# ==============================================================================

wait_for_postgres() {
    echo "Oczekiwanie na gotowość PostgreSQL (${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432})..."
    local attempt=0
    local max_attempts=30

    # UWAGA: nie sprawdzamy samego otwarcia portu TCP (socket.connect) —
    # otwarty port nie oznacza, że Postgres już przyjmuje zapytania (np. w
    # trakcie własnej inicjalizacji `initdb` port bywa otwarty wcześniej niż
    # baza jest gotowa). Zamiast instalować dodatkowo `postgresql-client`
    # tylko dla `pg_isready`, wykonujemy realną próbę połączenia przez
    # psycopg — bibliotekę, którą aplikacja i tak ma w /opt/venv.
    until python -c "
import sys

# Projekt może używać psycopg (v3) lub psycopg2 — próbujemy obu, żeby ten
# skrypt nie wymagał ręcznej synchronizacji z wyborem sterownika w pyproject.toml.
try:
    import psycopg as pg_driver
except ImportError:
    import psycopg2 as pg_driver

try:
    conn = pg_driver.connect(
        host='${POSTGRES_HOST:-db}',
        port=${POSTGRES_PORT:-5432},
        user='${POSTGRES_USER}',
        password='${POSTGRES_PASSWORD}',
        dbname='${POSTGRES_DB}',
        connect_timeout=2,
    )
    conn.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
"; do
        attempt=$((attempt + 1))
        if [ "$attempt" -ge "$max_attempts" ]; then
            echo "Baza danych niedostępna po ${max_attempts} próbach. Przerywam start."
            exit 1
        fi
        echo "Baza jeszcze niegotowa, próba ${attempt}/${max_attempts}..."
        sleep 2
    done
    echo "PostgreSQL gotowy do przyjmowania zapytań."
}

wait_for_postgres

echo "Uruchamianie procesu głównego: $*"
exec "$@"
