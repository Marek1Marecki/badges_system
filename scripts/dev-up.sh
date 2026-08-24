#!/bin/bash
set -e

# ==============================================================================
# dev-up.sh — bezpieczne uruchomienie środowiska DEV
#
# Zasada: Declarative Infrastructure, Imperative Operations (patrz
# README-infra.md). compose*.yml opisuje WYŁĄCZNIE stan docelowy (kontenery,
# sieci, wolumeny, healthchecki) — nigdy kolejność akcji wdrożeniowych.
# Ten skrypt jest jedynym miejscem, które wie, w jakiej kolejności rzeczy
# mają się wydarzyć na DEV. `make dev-up` jest tylko cienkim aliasem do niego
# — dzięki temu CI, dokumentacja i deweloper lokalnie używają dokładnie tej
# samej ścieżki, nie trzech różnych wariantów tej samej logiki.
#
# Bezpieczne zarówno na świeżym wolumenie (brak tabel — Database Release
# tworzy schemat od zera), jak i na istniejącym (migracje są no-op, jeśli
# już zastosowane).
# ==============================================================================

echo "=== DEV: uruchamianie środowiska ==="

echo "[1/2] Database Release (migracje)..."
# `docker compose run` honoruje `depends_on: condition: service_healthy`
# zdefiniowane dla usługi `web` w compose.override.yml — samo wywołanie
# uruchomi (i poczeka na healthcheck) `db`/`redis`, jeśli jeszcze nie działają.
# Nie potrzebujemy osobnego `docker compose up -d db redis` przed tym krokiem.
docker compose run --rm web ./scripts/release-database.sh

echo "[2/2] Start pozostałych usług..."
# --force-recreate wymusza odtworzenie kontenerów aplikacji. Jest to celowe:
# po restarcie Docker Desktop istniejące kontenery mogą mieć przestarzałą
# konfigurację (np. brak restart: unless-stopped). W DEV bind-mount ./:/app
# zachowuje kod, a wolumeny db/redis pozostają nietknięte — zmienia się tylko
# warstwa kontenera.
docker compose up -d --force-recreate

echo ""
echo "=== DEV gotowy. Sprawdź stan: ./scripts/dev-status.sh (lub: make dev-status) ==="
