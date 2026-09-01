# Architectural Contracts System v2.0

**Zakres:** Wszystkie projekty Python/Docker  
**Zasada nadrzędna:** `make check = CI quality-gate`, `pre-commit ⊆ make check`

---

## Filozofia systemu

Kontrakty definiują jeden standard jakości egzekwowany przez `make check`. CI uruchamia dokładnie to samo — brak rozbieżności między lokalnym środowiskiem a pipeline. Pre-commit uruchamia pełny `make check` lub jego szybki podzbiór (projekty ML) — ale nigdy nic czego nie ma w `make check`. Naruszenie kontraktu blokuje merge do `main`.

Różnica względem klasycznego podejścia: `make check` zawiera nie tylko narzędzia jakości kodu (`ruff`, `mypy`, `import-linter`, `pytest`) ale też skrypt audytu architektonicznego (`audit_contracts.py`) który wykrywa naruszenia kontraktów których nie widzi żadne inne narzędzie.

Dokumenty są podzielone na trzy kategorie:
- **Egzekwowalne** — naruszenie jest wykrywalne automatycznie i blokuje pipeline
- **Architektoniczne** — zasady struktury kodu weryfikowane przez mypy i import-linter
- **Referencyjne** — materiały pomocnicze, nie blokują pipeline

---

## Kontrakty egzekwowalne — Development

| # | Dokument | Kluczowa zasada |
|---|----------|-----------------|
| 01 | [Makefile Contract](01-makefile-contract.md) | `make check` = format + lint + type-check + test + audit |
| 02 | [Dependency Governance](02-dependency-governance.md) | `uv sync --frozen`, `uv lock --check` w CI |
| 03 | [Branching Strategy](03-branching-strategy.md) | Trunk-based, PR + CI przed merge |
| 04 | [Development Workflow](04-development-workflow.md) | WSL2, onboarding, codzienny workflow |
| 05 | [Test Coverage & Quality](05-test-coverage.md) | MIN_COVERAGE=80, zasada 10 sekund |
| 06 | [Documentation Contract](06-documentation-contract.md) | Google Style, Sphinx, `.python-version` |

## Kontrakty egzekwowalne — Infrastructure

| # | Dokument | Kluczowa zasada |
|---|----------|-----------------|
| 07 | [Docker Contract](07-docker-contract.md) | Multi-stage, `/opt/venv`, non-root, hardening Stage 2 |
| 08 | [Base Image Policy](08-base-image-policy.md) | `-bookworm` obowiązkowe, SHA w CI |
| 09 | [CI/CD Enforcement](09-ci-enforcement.md) | Two-Stage Pipeline: quality-gate → security-gate |
| 10 | [Secrets Management](10-secrets-management.md) | `.env.example`, `make secrets-check`, Security-by-Default |
| 11 | [Vulnerability Scanning](11-vulnerability-scanning.md) | Trivy CRITICAL/HIGH blokuje, `.trivyignore` policy |
| 12 | [Runtime Integrity](12-runtime-integrity.md) | Whitelist `/tmp` + blacklist `/app` |
| 13 | [Release & Tagging](13-release-tagging.md) | SemVer, `git tag -a`, CHANGELOG |

## Kontrakty architektoniczne

| # | Dokument | Kluczowa zasada |
|---|----------|-----------------|
| 14 | [Domain Purity Contract](14-domain-purity.md) | stdlib-only w `domain/`, DTO pattern, import-linter, TYPE_CHECKING |
| 16 | [Error Boundary Contract](16-error-boundary.md) | `DomainException → ApplicationException`, `raise X from e` |
| 17 | [Determinism Contract](17-determinism-contract.md) | ClockPort + IdGeneratorPort, FakeClock w testach |
| 20 | [Configuration Contract](20-configuration-contract.md) | `pydantic-settings`, bootstrap, feature flags, środowiska |

## Materiały referencyjne

| # | Dokument | Zawartość |
|---|----------|-----------|
| 18 | [Logging & Monitoring](18-logging-monitoring.md) | Loguru, JSON w produkcji, stdout/stderr |
| 19 | [Flow Diagram](19-flow-diagram.md) | Wizualizacja pipeline CI/CD |

## Narzędzia audytu

| Plik | Rola |
|------|------|
| `scripts/audit_contracts.py` | Skrypt audytu architektonicznego — część `make check` |

---

## Rejestr portów

| Środowisko | App | DB | Admin |
|------------|-----|----|-------|
| PTTK Badges (dev) | 8000 | 5432 | 8000 |
| PTTK Badges (test) | — | 5433 | — |

---

## Kluczowe decyzje architektoniczne

**`/opt/venv` zamiast `/app/.venv`** — mount `./:/app` w trybie dev nadpisuje cały katalog `/app`, niszcząc `.venv` z obrazu. Przeniesienie venv do `/opt/venv` rozwiązuje problem strukturalnie.

**Hardening Stage 2** — `pip uninstall -y pip setuptools wheel || true` usuwa vendored copies starych pakietów które Trivy wykrywa jako CVE, mimo że projekt używa wyłącznie `/opt/venv`.

**Two-Stage Pipeline** — `security-gate` uruchamia się tylko gdy `quality-gate` przejdzie. Nie budujemy obrazu Docker dopóki kod nie przeszedł jakości — oszczędza czas i zasoby CI.

**lint-docker jako osobny job** — `hadolint` uruchamiany równolegle z `quality-gate`, nie jako część `make check`. Dockerfile to infrastruktura, nie kod aplikacji — ma osobny cykl życia i osobną odpowiedzialność. Nie blokuje `security-gate` samodzielnie.

**import-linter Wariant B** — w Django monolicie kontrakt `layers` jest niemożliwy gdy domena i infrastruktura dzielą hierarchię `apps.*`. Stosujemy `forbidden` per-aplikacja z `include_external_packages = True`.

**dev-slim dla ML** — `[dependency-groups] dev-slim` zawiera tylko ruff/mypy/pytest. CI quality-gate używa `--only-group dev-slim` by uniknąć budowania Torch (~864MB). Security-gate buduje pełny obraz Docker.

**Zasada 10 sekund** — `make check` przez pre-commit musi kończyć się w <15s. Testy integracyjne oznaczone `@pytest.mark.integration` są wykluczone z domyślnego `make test`. Pełna paczka w `make test-all` (tylko CI).

**mypy + import-linter duplet** — mypy weryfikuje typy per-warstwa. import-linter weryfikuje kierunek zależności między warstwami. mypy nie wykryje że `domain/` importuje z `infrastructure/` jeśli typy są poprawne — import-linter wykryje to zawsze.

**`audit_contracts.py` jako część `make check`** — skrypt oparty na AST (zero zewnętrznych zależności) wykrywa naruszenia których nie łapie ruff/mypy/import-linter: `datetime.now()` w domenie, `logging` w domenie, `os.getenv` w `application/`, DataFrame w domenie, importy w bloku `TYPE_CHECKING` (klasyczne obejście kontraktu). Konfiguracja ścieżek w `pyproject.toml [tool.audit]` lub autodiscovery.

**`make check = CI quality-gate`, `pre-commit ⊆ make check`** — pre-commit uruchamia pełny `make check` lub slim subset (projekty ML), ale nigdy nic spoza `make check`. Brak rozbieżności między lokalnym środowiskiem a CI.
