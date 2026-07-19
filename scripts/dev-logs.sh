#!/bin/bash
set -e

# ==============================================================================
# dev-logs.sh — podgląd logów wszystkich usług DEV
#
# Opcjonalny argument: liczba linii historii (domyślnie 100).
#   ./scripts/dev-logs.sh        -> ostatnie 100 linii + follow
#   ./scripts/dev-logs.sh 500    -> ostatnie 500 linii + follow
# ==============================================================================

TAIL="${1:-100}"
docker compose logs -f --tail="${TAIL}"
