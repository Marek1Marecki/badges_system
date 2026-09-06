#!/usr/bin/env bash
# AUDYT-151: Monitorowanie zajętości dysku na Self-Hosted Runnerze.
# Alertuje gdy dysk używany jest powyżej 80%.
set -euo pipefail

# Katalog monitorowany (domyślnie /). Przekaż ścieżkę jako $1.
TARGET="${1:-/}"
THRESHOLD="${DISK_THRESHOLD:-80}"  # %

usage_pct=$(df "${TARGET}" | awk 'NR==2 {gsub(/%/,""); print $5}')
usage_pct=${usage_pct:-0}

if [ "${usage_pct}" -gt "${THRESHOLD}" ]; then
    echo "DISK_ALERT: ${TARGET} at ${usage_pct}% (threshold ${THRESHOLD}%)"
    # Opcjonalny webhook Slacka: export SLACK_WEBHOOK_URL=...
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🚨 Self-host runner: dysk ${TARGET} wykorzystany na ${usage_pct}% (limit ${THRESHOLD}%)\"}" \
            "${SLACK_WEBHOOK_URL}" || true
    fi
    return 1 2>/dev/null || exit 1
fi

echo "DISK_OK: ${TARGET} at ${usage_pct}% (threshold ${THRESHOLD}%)"
