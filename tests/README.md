# Test Suite — Struktura & Uruchamianie

> Pełna strategia testowa: `docs/Test Strategy.md`

## Struktura katalogów

```
tests/
├── conftest.py          # Global fixtures (db, cache, settings)
├── factories/           # Factory Boy — tworzenie testowych danych
├── fakes/               # Fake implementacje portów (Clock, Repozytoria)
├── domain/              # Pure domena — bez DB, bez Django
├── application/         # Use Case'y — Fake repozytoria, bez DB
├── apps/                # Testy modeli, adminów, widoków
├── infrastructure/      # Testy adapterów (OSM, Persistence)
├── architecture/        # Fitness functions (dependency direction, DTO contracts)
├── e2e/                 # Playwright — czarna skrzynka
└── bootstrap/           # Middleware, kontener DI
```

## Typy testów (markery)

| Marker | Typ | Wymaga DB? | Czas | Komenda |
|--------|-----|-----------|------|---------|
| _(brak)_ | Unit / Property | ❌ | < 5s | `make check` |
| `@pytest.mark.integration` + `@pytest.mark.django_db` | Integration | ✅ (docker-compose db) | < 30s | `make test-all` |
| `@pytest.mark.testcontainers` | Testcontainers | ✅ (Docker socket) | ~18s | `make experimental-testcontainers` |
| `@pytest.mark.e2e` | End-to-End (Playwright) | ✅ (compose.e2e.yml) | ~5m | `./scripts/e2e-run.sh` |

## Najważniejsze komendy

| Komenda | Co robi | Kiedy |
|---------|---------|-------|
| `make check` | Format + lint + mypy + importlinter + unit tests + audit_contracts | Każdy commit (lokalny pre-commit hook) |
| `make test-all` | Pełny zestaw: `not e2e` (unit + integration + arch) | PR / CI |
| `make experimental-testcontainers` | Izolowane PostGIS w Dockerze | Ręcznie, tylko dla adapterów DB |
| `./scripts/e2e-run.sh` | Spin-up compose.e2e.yml → Playwright | Przed release / ręcznie |

## Uruchamianie konkretnego testu

```bash
# Jednostkowy (bez DB)
ENV_FILE=.env.test uv run pytest tests/domain/rules/test_badge_rules.py -v

# Integracyjny (z DB z compose)
docker compose up -d db redis
ENV_FILE=.env.test uv run pytest tests/apps/badges/test_models.py -m integration

# Konkretny test e2e
./scripts/e2e-run.sh -k test_homepage

# Tylko testy architektoniczne (fitness functions)
uv run pytest tests/architecture/ -v
```

## Często spotykane problemy

1. **`OperationalError: failed to resolve host 'db'`** — uruchom `docker compose up -d db redis` najpierw.
2. **`Coverage failure: ... less than fail-under=80`** — spowodowane uruchomieniem podzbioru testów. Uruchom `make check` dla pełnego zestawu.
3. **Pre-commit hook przekracza 120s** — `make check` w hooku może być wolny. Dla docs-only commitów użyj `git commit --no-verify`.
