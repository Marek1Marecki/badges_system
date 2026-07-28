#!/bin/bash
# UWAGA: celowo BEZ `set -e` — to narzędzie DIAGNOSTYCZNE. Ma zgłosić
# wszystkie znalezione problemy na raz, nie przerwać się na pierwszym.
#
# Ten skrypt jest odrębny od dev-status.sh (nie tylko cienki wrapper) z
# jednego, konkretnego powodu: dev-status.sh ma na sztywno wpisaną nazwę
# kontenera `badges_system-db-1` (projekt "badges_system"). Dla PRE-PROD,
# gdzie `preprod-run.sh` wymusza `-p badges_preprod`, ten sam kontener
# nazywa się `badges_preprod-db-1` — dev-status.sh nie zadziałałby tutaj
# bez modyfikacji. Zamiast parametryzować dev-status.sh dwoma rolami na
# raz (ryzyko pomyłki, który tryb jest aktywny), utrzymujemy dwa osobne,
# krótkie skrypty — każdy poprawny dla jednego, konkretnego środowiska.

# Skrypt działa NA HOŚCIE — `.env` trzeba wczytać jawnie (patrz to samo
# uzasadnienie w dev-status.sh / dev-backup.sh).
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

PROJECT_NAME="badges_preprod"
CONTAINER_DB="${PROJECT_NAME}-db-1"

FAILURES=0

check() {
    local label="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        echo "✓ ${label}"
    else
        echo "✗ ${label}"
        FAILURES=$((FAILURES + 1))
    fi
}

echo "=== Stan kontenerów (PRE-PROD, projekt: ${PROJECT_NAME}) ==="
./scripts/preprod-run.sh ps
echo ""

echo "=== Kontrole szczegółowe ==="
check "PostgreSQL odpowiada (pg_isready)" \
    bash -c "./scripts/preprod-run.sh exec -T db pg_isready -U '${POSTGRES_USER:-postgres}'"

check "Redis odpowiada (PING)" \
    bash -c "./scripts/preprod-run.sh exec -T redis redis-cli ping | grep -q PONG"

check "Django check (bez --deploy — to jest już zweryfikowane w release-application.sh)" \
    bash -c "./scripts/preprod-run.sh exec -T web uv run python manage.py check"

check "Migracje zastosowane (migrate --check)" \
    bash -c "./scripts/preprod-run.sh exec -T web uv run python manage.py migrate --check"

check "Celery worker odpowiada (inspect ping)" \
    bash -c "./scripts/preprod-run.sh exec -T celery_worker uv run celery -A config inspect ping | grep -qi pong"

# Kontrola poprawności mountu wolumenu PostgreSQL (ADR-025) — ten sam
# incydent i to samo uzasadnienie co w dev-status.sh, tylko celujące
# w kontener PRE-PROD, nie DEV.
DB_MOUNT=$(docker inspect "${CONTAINER_DB}" \
    --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql"}}{{.Destination}}{{end}}{{end}}' \
    2>/dev/null)
if [ "$DB_MOUNT" = "/var/lib/postgresql" ]; then
    echo "✓ Wolumen PostgreSQL zamontowany poprawnie (/var/lib/postgresql, zgodnie z ADR-025)"
else
    echo "✗ Wolumen PostgreSQL NIE jest zamontowany pod /var/lib/postgresql (ADR-025)"
    echo "  Sprawdź: docker inspect ${CONTAINER_DB} --format '{{json .Mounts}}'"
    FAILURES=$((FAILURES + 1))
fi

DATA_DIR=$(./scripts/preprod-run.sh exec -T db psql -U "${POSTGRES_USER:-postgres}" -tAc "SHOW data_directory;" 2>/dev/null | tr -d '[:space:]')
if [[ "$DATA_DIR" == /var/lib/postgresql/* ]]; then
    echo "✓ PostgreSQL faktycznie używa katalogu danych wewnątrz wolumenu (${DATA_DIR})"
else
    echo "✗ PostgreSQL zgłasza nieoczekiwany katalog danych: '${DATA_DIR:-<brak odpowiedzi>}'"
    echo "  Oczekiwano ścieżki zaczynającej się od /var/lib/postgresql/ (ADR-025)"
    FAILURES=$((FAILURES + 1))
fi

echo ""
echo "=== Sanity check danych ==="
# Te same tabele co w dev-status.sh — patrz tam uzasadnienie nazw. Zero
# rekordów jest tu OCZEKIWANE przed pierwszym `bootstrap.sh` na tym
# środowisku; po nim dane referencyjne (badges/tourist_objects) powinny
# odpowiadać wersji snapshotu zgodnej z planowanym wdrożeniem PROD
# (ADR-020, macierz propagacji) — dane użytkownika (users/profiles) są tu
# z założenia fikcyjne, niski/zerowy licznik nie jest niepokojący.
DATA_CHECK=$(./scripts/preprod-run.sh exec -T db psql \
    -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-badges_system_db}" \
    -tA -F'|' -c "
SELECT
  (SELECT count(*) FROM auth_user),
  (SELECT count(*) FROM odznaki_badge),
  (SELECT count(*) FROM odznaki_tourist_object),
  (SELECT count(*) FROM tourists_profile);
" 2>/dev/null)

if [ -n "$DATA_CHECK" ]; then
    IFS='|' read -r N_USERS N_BADGES N_OBJECTS N_PROFILES <<< "$DATA_CHECK"
    report_count() {
        local label="$1" value="$2"
        if [ "${value:-0}" -gt 0 ] 2>/dev/null; then
            echo "✓ ${label}: ${value}"
        else
            echo "⚠ ${label}: 0 (oczekiwane przed pierwszym bootstrap.sh na tym środowisku)"
        fi
    }
    report_count "Users (fikcyjne z założenia — ADR-020)" "$N_USERS"
    report_count "Badges" "$N_BADGES"
    report_count "Tourist objects" "$N_OBJECTS"
    report_count "Profiles (fikcyjne z założenia — ADR-020)" "$N_PROFILES"
else
    echo "⚠ Nie udało się odczytać liczby rekordów (środowisko jeszcze nie uruchomione?"
    echo "  Uruchom najpierw: make preprod-deploy)"
fi

echo ""
if [ "$FAILURES" -eq 0 ]; then
    echo "Wszystkie kontrole przeszły pomyślnie."
    exit 0
else
    echo "UWAGA: ${FAILURES} kontrol(a/i) nie powiodła/y się — patrz ✗ powyżej."
    exit 1
fi
