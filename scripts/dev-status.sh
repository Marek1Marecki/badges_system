#!/bin/bash
# UWAGA: celowo BEZ `set -e` — to narzędzie DIAGNOSTYCZNE. Ma zgłosić
# wszystkie znalezione problemy na raz, nie przerwać się na pierwszym.

# Skrypt działa NA HOŚCIE — `.env` trzeba wczytać jawnie (sam docker compose
# czyta go tylko na potrzeby interpolacji ${VAR} w plikach compose*.yml,
# to nie trafia automatycznie do zmiennych tej powłoki).
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

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

echo "=== Stan kontenerów ==="
docker compose ps
echo ""

echo "=== Kontrole szczegółowe ==="
check "PostgreSQL odpowiada (pg_isready)" \
    docker compose exec -T db pg_isready -U "${POSTGRES_USER:-postgres}"

check "Redis odpowiada (PING)" \
    bash -c "docker compose exec -T redis redis-cli ping | grep -q PONG"

check "Django check (bez --deploy — to tylko diagnostyka DEV)" \
    docker compose exec -T web uv run python manage.py check

check "Migracje zastosowane (migrate --check)" \
    docker compose exec -T web uv run python manage.py migrate --check

check "Celery worker odpowiada (inspect ping)" \
    bash -c "docker compose exec -T celery_worker uv run celery -A config inspect ping | grep -qi pong"

# UWAGA — granica tego narzędzia: Celery Beat (w przeciwieństwie do workera)
# nie ma wbudowanego mechanizmu odpowiedzi na "ping" — to scheduler, nie
# konsument zadań. Sprawdzamy więc wyłącznie, czy kontener w ogóle działa
# (nie: czy faktycznie coś planuje). Pełna weryfikacja wymagałaby dodatkowej
# instrumentacji po stronie aplikacji (np. tabela heartbeat w bazie) — poza
# zakresem tego skryptu infrastrukturalnego.
check "Kontener celery_beat działa (tylko status procesu, nie funkcjonalność)" \
    bash -c "docker compose ps celery_beat --status running --format '{{.Name}}' | grep -q ."

# Kontrola poprawności mountu wolumenu PostgreSQL (ADR-025). Historia tego
# projektu: niedopasowanie wersji obrazu Postgres do ścieżki montowania
# wolumenu tworzyło cichą, PUSTĄ bazę zamiast rozpoznać istniejące dane —
# `db healthy` nic o tym nie mówi (proces odpowiada, nawet gdy dane "pod
# spodem" są niewłaściwe). Ta kontrola nie zastępuje backupów, tylko
# wykrywa jedną konkretną, już raz kosztowną pomyłkę.
DB_MOUNT=$(docker inspect badges_system-db-1 \
    --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql"}}{{.Destination}}{{end}}{{end}}' \
    2>/dev/null)
if [ "$DB_MOUNT" = "/var/lib/postgresql" ]; then
    echo "✓ Wolumen PostgreSQL zamontowany poprawnie (/var/lib/postgresql, zgodnie z ADR-025)"
else
    echo "✗ Wolumen PostgreSQL NIE jest zamontowany pod /var/lib/postgresql (ADR-025)"
    echo "  Sprawdź: docker inspect badges_system-db-1 --format '{{json .Mounts}}'"
    FAILURES=$((FAILURES + 1))
fi

# Druga, NIEZALEŻNA kontrola tej samej rzeczy — nie z zewnątrz (docker
# inspect widzi tylko deklarację mountu), tylko "od środka": pytamy sam
# proces PostgreSQL, jakiego katalogu danych faktycznie używa. Celowo NIE
# zakładamy z góry konkretnego numeru wersji (np. ".../18/docker") — to
# byłoby dokładnie tym samym błędem hardcodowania, przed którym ostrzega
# ADR-025, tylko przeniesionym do skryptu diagnostycznego. Sprawdzamy
# wyłącznie, że ścieżka zaczyna się od zamontowanego wolumenu.
DATA_DIR=$(docker compose exec -T db psql -U "${POSTGRES_USER:-postgres}" -tAc "SHOW data_directory;" 2>/dev/null | tr -d '[:space:]')
if [[ "$DATA_DIR" == /var/lib/postgresql/* ]]; then
    echo "✓ PostgreSQL faktycznie używa katalogu danych wewnątrz wolumenu (${DATA_DIR})"
else
    echo "✗ PostgreSQL zgłasza nieoczekiwany katalog danych: '${DATA_DIR:-<brak odpowiedzi>}'"
    echo "  Oczekiwano ścieżki zaczynającej się od /var/lib/postgresql/ (ADR-025)"
    FAILURES=$((FAILURES + 1))
fi

echo ""
echo "=== Sanity check danych ==="
# UWAGA: ta sekcja jest wyłącznie INFORMACYJNA — nie wlicza się do FAILURES
# i nie wpływa na kod wyjścia tego skryptu. Powód: zaraz po świeżym
# `dev-up`/`dev-reset` (przed ręcznym `bootstrap.sh`) baza LEGALNIE ma zero
# danych referencyjnych — to zgodne z ADR-020 (restore_reference_data nigdy
# nie jest wywoływane automatycznie), nie błąd środowiska. Traktuj "0" tutaj
# jako przypomnienie "uruchom bootstrap.sh", nie jako czerwoną flagę.
#
# Nazwy tabel poniżej są SPECYFICZNE DLA TEGO PROJEKTU (zweryfikowane
# ręcznie) — jeśli zmienią się nazwy modeli/aplikacji Django, zaktualizuj tę
# listę (Django nazywa tabele jako `<app_label>_<model_lowercase>`).
DATA_CHECK=$(docker compose exec -T db psql \
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
            echo "⚠ ${label}: 0 (oczekiwane na świeżym środowisku przed bootstrap.sh)"
        fi
    }
    report_count "Users" "$N_USERS"
    report_count "Badges" "$N_BADGES"
    report_count "Tourist objects" "$N_OBJECTS"
    report_count "Profiles" "$N_PROFILES"
else
    echo "⚠ Nie udało się odczytać liczby rekordów (tabele jeszcze nie istnieją?"
    echo "  Upewnij się, że 'make dev-up' zakończyło Database Release poprawnie.)"
fi

echo ""
if [ "$FAILURES" -eq 0 ]; then
    echo "Wszystkie kontrole przeszły pomyślnie."
    exit 0
else
    echo "UWAGA: ${FAILURES} kontrol(a/i) nie powiodła/y się — patrz ✗ powyżej."
    exit 1
fi
