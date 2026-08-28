# PRE-PROD Validation — Koncepcja

> Status: Draft  
> Data: 2026-08-28  
> Właściciel: Dominik / AI Architect  
> Zasada: Ten dokument opisuje proponowany job CI do walidacji wdrożenia na środowisko PRE-PROD. Jest to **deployment/environment validation**, oddzielna kategoria od testowania integracyjnego i testów E2E.

---

## Cel

Job `preprod-validation` odpowiada na pytanie:

> „Czy wdrożony artefakt działa poprawnie w środowisku PRE-PROD?”

To jest **smoke/validation test wdrożenia i środowiska uruchomieniowego**, nie pełna suita integracyjna i nie powtórzenie testów z `integration-tests`.

## Co jest W SCOPE

- Deploy artefaktu na `badges_preprod`
- Weryfikacja zdrowia środowiska (health check, migracje, Redis, Celery)
- Mały zestaw smoke tests (~10-20 testów) przeciwko działającemu środowisku
- Cleanup środowiska po zakończeniu

## Co jest OUT OF SCOPE

- Pełna suita testów integracyjnych — już realizowana przez `integration-tests`
- Testy E2E — już realizowane przez `e2e-tests`
- Testy jednostkowe — już realizowane przez `static-analysis-and-unit-tests`
- Testy architektury (FF-001..FF-023) — już realizowane przez `make check`

**PRE-PROD validation nie jest kolejnym poziomem testów aplikacji. Jest kontrolą poprawności wdrożenia i środowiska uruchomieniowego.**

## Docelowy model CI

```text
GATE
  │
  ├── Czy kod spełnia invariants?
  │
  ▼
INTEGRATION
  │
  ├── Czy komponenty współpracują?
  │
  ▼
E2E
  │
  ├── Czy system realizuje scenariusze użytkownika?
  │
  ▼
PRE-PROD VALIDATION
  │
  └── Czy konkretny artefakt został poprawnie wdrożony
      i działa w docelowo podobnym środowisku?

A równolegle:

DIAGNOSTIC
    └── dodatkowa obserwowalność jakości

EXPERIMENTAL
    ├── Testcontainers
    ├── Schemathesis
    ├── ZAP
    ├── axe
    ├── k6
    └── mutmut
```

PRE-PROD validation odpowiada na zupełnie inne pytanie niż testy integracyjne. Nie powinien zawierać tych samych testów, tylko krótkie sprawdzenia, że wdrożenie się udało i środowisko działa.

## Zakres

Job uruchamia się **tylko na `main`** (nie na każdy PR) i wykonuje:

1. Deploy najnowszego zbudowanego obrazu na `badges_preprod`
2. Weryfikację zdrowia środowiska (health check, migracje, Redis, Celery)
3. Mały zestaw smoke tests (~10-20 testów) przeciwko działającemu środowisku
4. Cleanup środowiska po zakończeniu

## Wyzwalacz

```yaml
if: github.ref == 'refs/heads/main'
```

Opcjonalnie: manual trigger przez maintainera na PR z label `preprod-check`.

## Zależności

Job wymaga:

- `integration-tests` — buduje obraz `badges-system:${SHA}`
- Dostęp do Docker socket na runnerze self-hosted
- Sekrety PRE-PROD w GitHub Secrets:
  - `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
  - `SECRET_KEY`, `ALLOWED_HOSTS`
  - `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`
  - `MAPY_CZ_API_KEY`
  - `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD`

## Struktura jobu

```yaml
preprod-validation:
  name: PRE-PROD Validation
  needs: integration-tests
  runs-on: self-hosted
  timeout-minutes: 45
  if: github.ref == 'refs/heads/main'
  concurrency:
    group: preprod-validation
    cancel-in-progress: false
```

## Kroki

### 1. Deploy

Użycie istniejącego skryptu `preprod-deploy.sh`:

```bash
./scripts/preprod-deploy.sh
```

Skrypt wykonuje:
- `release-database.sh` — migracje
- `release-application.sh` — collectstatic, check --deploy
- `up -d` — uruchomienie kontenerów

### 2. Smoke tests

Mały zestaw testów uruchomionych przeciwko `http://localhost:8008`:

- `/health/` — 200 OK
- Authentication flow
- Podstawowy GET API (np. lista badge'ów)
- GIS query (np. nearby objects)
- Redis-dependent operation
- Celery task smoke
- Database migration state

### 3. Cleanup

```bash
./scripts/preprod-run.sh down
```

## Wpływ na istniejące joby

| Job | Wpływ |
|-----|-------|
| `static-analysis-and-unit-tests` | Brak |
| `integration-tests` | Minimalny — buduje obraz, który może być używany przez preprod-validation |
| `e2e-tests` | Średni — jeśli preprod-validation jest przed e2e, e2e czeka dłużej |
| `preprod-validation` | Nowy job — wymaga sekretów PRE-PROD |

## Alternatywy

### A. Efemeryczne PRE-PROD-like

Zamiast używać istniejącego `badges_preprod`, utworzyć nowy, efemeryczny projekt Compose:

```bash
COMPOSE_PROJECT_NAME="ci-preprod-${GITHUB_RUN_ID}"
docker compose -p "$COMPOSE_PROJECT_NAME" \
  -f compose.yml -f compose.preprod.yml \
  up -d --wait db redis web celery_worker celery_beat
```

**Plusy:** Pełna izolacja, brak konfliktów, czysty stan zawsze.  
**Minusy:** Nie testujesz prawdziwego `badges_preprod`, tylko jego kopii.

### B. Prawdziwy `badges_preprod`

Użycie istniejącego środowiska:

```bash
./scripts/preprod-deploy.sh
```

**Plusy:** Testujesz przeciwko trwałemu środowisku, z rzeczywistymi danymi.  
**Minusy:** Ryzyko konfliktów przy równoległych uruchomieniach, stan między przebiegami.

## Rekomendacja

Na obecnym etapie: **nie implementować jobu `preprod-validation`**.

Uzasadnienie:
- Obecne joby `integration-tests` i `e2e-tests` już realizują walidację infrastruktury i systemu.
- Dodanie kolejnego jobu zwiększy złożoność CI i czas pipeline.
- PRE-PROD validation jest wartościowe, ale jako osobna inicjatywa, nie jako natychmiastowe rozszerzenie CI.

Jeśli w przyszłości zdecydujemy się na dodanie `preprod-validation`, wybrać wariant **A (efemeryczny)**, aby uniknąć konfliktów i problemów z stanem.

---

## Historia zmian

| Wersja | Data | Autor | Opis zmiany |
|--------|------|-------|-------------|
| 0.1 | 2026-08-28 | Dominik / AI Architect | Draft koncepcji |
