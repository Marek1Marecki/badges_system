#!/bin/bash
set -euo pipefail

# ==============================================================================
# scripts/zap-run.sh — wrapper na środowisko E2E dla OWASP ZAP DAST
#
# Uruchamia efemeryczne środowisko E2E (compose.e2e.yml), czeka na gotowość
# serwera na porcie 8009, uruchamia ZAP quick-scan i sprząta po sobie.
#
# Użycie:
#   ./scripts/zap-run.sh              # quick scan całej aplikacji
#   ./scripts/zap-run.sh -r /api/v1/  # skanuj tylko podany path
#
# Wszystko działa w izolowanym projekcie Compose i sprząta po sobie.
# NIGDY nie łączy się z DEV (localhost:8005) ani PRE-PROD!
# ==============================================================================

PROJECT="zap-$(date +%s)-$$"
COMPOSE=(docker compose -p "${PROJECT}" -f compose.yml -f compose.test.yml -f compose.e2e.yml)

cleanup() {
    local exit_code=$?
    echo ""
    echo "=== Sprzątanie środowiska ZAP (projekt: ${PROJECT}) ==="
    "${COMPOSE[@]}" down -v --remove-orphans 2>/dev/null || true
    exit $exit_code
}
trap cleanup EXIT

echo "=== ZAP: budowa obrazu web-e2e (${PROJECT}) ==="
"${COMPOSE[@]}" build web-e2e

echo ""
echo "=== ZAP: uruchamianie infrastruktury (${PROJECT}) ==="
"${COMPOSE[@]}" up -d --wait db redis web-e2e

echo ""
echo "[1/2] Migracje bazy danych..."
for i in {1..30}; do
    if "${COMPOSE[@]}" exec -T web-e2e python manage.py migrate; then
        break
    fi
    echo "Migracja nieudana (próba $i/30), ponawiam za 2s..."
    sleep 2
done

"${COMPOSE[@]}" exec -T web-e2e python manage.py validate_reference_manifest
for fixture in 01_regions.json.gz 02_tourist_objects.json.gz 03_badges.json.gz 04_osm_mappings.json.gz 05_badge_news.json.gz; do
    "${COMPOSE[@]}" exec -T web-e2e python manage.py loaddata "data/reference/${fixture}" 2>/dev/null || true
done

echo ""
echo "[2/2] Oczekiwanie na gotowość serwera na http://localhost:8009/..."
for i in {1..60}; do
    if curl -s http://localhost:8009/ > /dev/null 2>&1; then
        break
    fi
    echo "Oczekiwanie na serwer (próba $i/60)..."
    sleep 2
done

echo ""
echo "=== ZAP: uruchamianie skanowania DAST ==="
echo "Pobieranie obrazu securecodebox/zap..."
docker pull securecodebox/zap:latest 2>&1 | tail -2

ZAP_ARGS="-cmd -quickurl http://host.docker.internal:8009 -quickout /tmp/zap_report.xml"
if [ $# -gt 0 ]; then
    ZAP_ARGS="$ZAP_ARGS $*"
fi

docker run --rm --add-host=host.docker.internal:host-gateway securecodebox/zap:latest \
    zap.sh $ZAP_ARGS 2>&1

if [ -f /tmp/zap_report.xml ]; then
    echo ""
    echo "=== ZAP: wyniki skanowania ==="
    cat /tmp/zap_report.xml 2>/dev/null || true
    rm -f /tmp/zap_report.xml
fi

echo ""
echo "=== ZAP zakończony pomyślnie ==="
