#!/bin/bash
set -e

# ==============================================================================
# dev-down.sh — zatrzymanie środowiska DEV
#
# CELOWO nie przyjmuje żadnych flag/argumentów zwiększających destrukcyjność
# (np. przekazywanego "-v"). Jedyne miejsce w tym projekcie, gdzie wolumeny
# DEV mogą zostać usunięte, to `dev-reset.sh` — z jawnym, wpisywanym z
# klawiatury potwierdzeniem. Rozdzielenie na dwie różne nazwy komend (nie
# jedną komendę z flagą) eliminuje ryzyko pomyłki typu "chciałem dev-down,
# doleciał mi --force z automatycznym -v".
# ==============================================================================

echo "Zatrzymywanie środowiska DEV (bez usuwania wolumenów)..."
docker compose down
echo "Zatrzymano. Wolumeny (dane) pozostały nietknięte."
echo "Usunięcie danych wyłącznie przez: ./scripts/dev-reset.sh (lub: make dev-reset)"
