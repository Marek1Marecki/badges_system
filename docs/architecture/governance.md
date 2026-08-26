# Architecture Governance

> **Wersja:** 1.0  
> **Data:** 2026-08-26  
> **Właściciel:** Dominik / AI Architect  
> **Zasada:** Ten dokument jest master indexem wszystkich mechanizmów governance w projekcie. Pokazuje co jest blocking, co advisory, gdzie są wyjątki, i jaka jest kolejność w CI.

---

## Przegląd warstw governance

```
                    ARCHITECTURE GOVERNANCE
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
      DECIDE             DOCUMENT             DISCOVER
       ADR                C4/ADR             pydeps
        │                    │               pyreverse
        ▼                    │
     ENFORCE                 │
 Import Linter               │
 Architecture Tests         │
        │                    │
        ▼                    ▼
      MEASURE ────────────→ EVOLVE
  Radon / Xenon              wily
         │
         ▼
  INFRASTRUCTURE GOVERNANCE
  Hadolint / Checkov / Trivy
         │
         ▼
  OPERATIONAL GOVERNANCE
  Health Checks / Error Handling / Observability
```

---

## Mechanizmy governance

### DECIDE — Architecture Decision Records

| Mechanizm | Plik/Katalog | Cel | Charakter |
|-----------|-------------|-----|----------|
| ADR | `docs/adr/ADR-*.md` | Rejestr decyzji architektonicznych | Advisory / Documentation |
| Architecture Debt Register | `docs/architecture/debt-register.md` | Rejestr długów architektonicznych | Advisory / Planning |

**Kiedy dodajemy nowy ADR:**
- Zmiana stosu technologicznego
- Nowa reguła biznesowa wpływająca na architekturę
- Wyjątek z Import Lintera

---

### DOCUMENT — Architektura zamierzona

| Mechanizm | Plik/Katalog | Cel | Charakter |
|-----------|-------------|-----|----------|
| C4 Context | `docs/architecture/context.puml` | Kontekst systemu (C1) | Documentation |
| C4 Containers | `docs/architecture/containers.puml` | Kontenery systemu (C2) | Documentation |
| C4 Components | `docs/architecture/components.puml` | Komponenty (C3) | Documentation |
| Fitness Functions | `docs/architecture/fitness-functions.md` | Rejestr reguł architektonicznych | Enforcement |
| Dependency Graph | `docs/dependencies.svg` | Zamierzona struktura zależności | Discovery |

**Zasada:**
- Diagramy są generowane automatycznie z kodu
- Nie edytuje się ich ręcznie
- Każda zmiana w kodzie powinna być odzwierciedlona w diagramach

---

### ENFORCE — Egzekwowanie reguł

| Mechanizm | Plik/Konfiguracja | Cel | Charakter | Blokuje CI? |
|-----------|-------------------|-----|----------|-------------|
| Import Linter | `.importlinter` | Kierunek zależności między warstwami | **Blocking** | ✅ Tak |
| Architecture Tests — FF-001..FF-005, FF-007..FF-010, FF-015..FF-016 | `tests/architecture/` | Fitness functions (architectural invariants) | **Blocking** | ✅ Tak |
| Architecture Tests — FF-006 (DTO Naming Convention) | `tests/architecture/` | Konwencja stylistyczna | Advisory | ❌ Nie |

**Import Linter — wyjątki:**

| Wyjątek | Uzasadnienie | Powiązanie |
|---------|--------------|------------|
| `apps.badges.tasks -> infrastructure.adapters.osm_adapter` | Zadania Celery wywołują OSMAdapter bezpośrednio dla retry logic | DŁUG-001 |
| `apps.badges.models -> infrastructure.schemas.badge_rules_schema` | Walidacja JSONB w modelu Django | DŁUG-002 |
| `apps.tourists.context_processors -> infrastructure.config.map_layers` | Context Processor wstrzykuje warstwy map | DŁUG-003 |
| `infrastructure.adapters.celery_event_publisher -> apps.badges.tasks` | Adapter zdarzeń importuje nazwy zadań Celery | DŁUG-004 |

**Import Linter a testy architektury:**
- `test_dependency_direction.py` (FF-001) jest komplementarny do Import Lintera — test dostarcza diagnostykę w pytest, ale Import Linter jest źródłem prawdy.
- `test_domain_purity.py` (FF-002) nie powtarza już sprawdzania importów (to obowiązek Import Lintera `domain-purity`). Test chroni tylko invariant behawioralny: brak dziedziczenia po `Model` w warstwie domenowej, który Import Linter nie może wykryć.

---

### MEASURE — Jakość kodu

| Mechanizm | Plik/Konfiguracja | Cel | Charakter | Blokuje CI? |
|-----------|-------------------|-----|----------|-------------|
| Radon | `make complexity-check` | Złożoność cyklomatyczna | Advisory | ❌ Nie |
| Xenon | `xenon.ini` | Brama jakości złożoności | **Blocking** | ✅ Tak |
| wily | `make complexity-trend` | Trend jakości w czasie | Advisory | ❌ Nie |

**Xenon — limity:**
- Złożoność cyklomatyczna: B (max 10)
- Maintainability Index: C (min 20)

---

### INFRASTRUCTURE GOVERNANCE — Bezpieczeństwo runtime

| Mechanizm | Plik/Konfiguracja | Cel | Charakter | Blokuje CI? |
|-----------|-------------------|-----|----------|-------------|
| Hadolint | `.hadolint.yaml` | Jakość Dockerfile | Advisory | ❌ Nie |
| Checkov | `.checkov.yaml` | Bezpieczeństwo Compose/IaC | Advisory | ❌ Nie |
| Trivy | `make security-audit` | CVE w obrazie kontenerowym | **Blocking** | ✅ Tak (HIGH/CRITICAL) |
| Docker Bench | `make docker-bench` | Audyt hosta Docker | Advisory | ❌ Nie (placeholder) |

**Hadolint — obecny baseline:**

| Ostrzeżenie | Status | Uzasadnienie |
|-------------|--------|--------------|
| DL3006 — tag obrazu bazowego | ⚠️ Non-blocking | Wersje przypięte przez ARG (`PYTHON_BASE`, `UV_IMAGE`) |
| DL3008 — pin pakietów APT | ⚠️ Non-blocking | Pakiety zmieniają się często; pinowanie w builderze |
| DL3046 — `useradd` bez `-l` | ⚠️ Non-blocking | Świadome użycie wysokiego UID (10001) dla django_user |

**Polityka:** Sześć obecnych warningów jest zaakceptowanym baselinem. Nowe warningi nie powinny być dodawane bez uzasadnienia.

---

### OPERATIONAL GOVERNANCE — Runtime & Observability

| Mechanizm | Plik/Konfiguracja | Cel | Charakter | Blokuje CI? |
|-----------|-------------------|-----|----------|-------------|
| Health Checks | `tests/architecture/test_health_checks.py` | Wszystkie services mają `healthcheck` | **Blocking** | ✅ Tak |
| API Exception Handling | `tests/architecture/test_exception_handling.py` | Widoki łapią `ApplicationException` | **Blocking** | ✅ Tak |

**Health Checks:**
- Każdy service w `compose*.yml` musi mieć `healthcheck`
- Wyjątki: `db`, `redis` (mają healthcheck w `compose.yml`)
- Test: `test_all_application_services_have_healthcheck`

**API Exception Handling:**
- Każda metoda `post`/`patch` w `apps/api/views.py` musi łapać `ApplicationException`
- Test: `test_api_views_handle_application_exception`

### OBSERVABILITY GOVERNANCE — Kontrakty przed wdrożeniem

| Mechanizm | Plik/Konfiguracja | Cel | Charakter | Blokuje CI? |
|-----------|-------------------|-----|----------|-------------|
| Request ID Contract | `tests/architecture/test_request_id_contract.py` | Korelacja żądań | **Blocking** | ✅ Tak |
| No Sensitive Data in Logs | `tests/architecture/test_no_sensitive_data_in_logs.py` | Brak wrażliwych danych w logach | Advisory | ❌ Nie |
| Structured Error Context | `tests/architecture/test_structured_error_context.py` | RFC 7807 + request_id | **Blocking** | ✅ Tak |
| Health Check Semantics | `tests/architecture/test_health_checks.py` | Semantyka healthcheck | **Blocking** | ✅ Tak (TEST/PROD) |

**Request ID Contract:**
- Middleware generuje `request_id` jeśli brak `X-Request-ID`; honoruje nagłówek jeśli obecny
- `request_id` jest wstrzykiwany do obiektu `request` i do kontekstu Loguru
- Test: `test_request_id_contract.py`

**No Sensitive Data in Logs:**
- Logi nie mogą zawierać haseł, tokenów, sekretów, kluczy API
- Test skanuje komunikaty pod kątem słów kluczowych
- Status Advisory z powodu możliwości false positives
- Test: `test_no_sensitive_data_in_logs.py`

**Structured Error Context:**
- Wszystkie `except ApplicationException` w API używają `_handle_application_exception` lub `_problem_detail`
- Oba helpery wstrzykują `request_id` do odpowiedzi RFC 7807
- Test: `test_structured_error_context.py`

**Health Check Semantics:**
- Endpoint `/health/` sprawdza DB (`SELECT 1`) i Redis (`cache.set`/`cache.get`)
- Jeśli zależność niedostępna — zwraca `503 Service Unavailable`
- W `APP_ENV=test` pomija sprawdzanie zależności (testy jednostkowe bez DB/Redis)
- Test: `test_health_checks.py` + `test_urls.py`

**Przyszłe wdrożenia (nie teraz):**
- Sentry — error tracking (po pojawieniu się użytkowników produkcyjnych)
- Prometheus + Grafana — metryki i dashboardy (po potrzebie capacity planning)
- Loki — agregacja logów (po zniknięciu wartości `docker compose logs`)
- OpenTelemetry — distributed tracing (po zrozumieniu Prometheusa)

### SUPPLY CHAIN GOVERNANCE — Kontrakty łańcucha dostaw

| Mechanizm | Plik/Konfiguracja | Cel | Charakter | Blokuje CI? |
|-----------|-------------------|-----|----------|-------------|
| Lockfile Integrity | `tests/architecture/test_lockfile_integrity.py` + pre-commit `uv lock --check` | `uv.lock` jest committed i śledzony | **Blocking** | ✅ Tak |
| Dependency Groups Separation | `tests/architecture/test_dependency_groups_separation.py` | Narzędzia dev/test nie mieszają się z runtime | Advisory | ❌ Nie |

**Lockfile Integrity:**
- `uv.lock` istnieje i jest śledzony przez Git
- Pre-commit hook `uv lock --check` gwarantuje synchronizację z `pyproject.toml`
- Test: `test_lockfile_integrity.py`

**Dependency Groups Separation:**
- Zależności z `[dependency-groups.dev]` i `[dependency-groups.test]` nie pojawiają się w runtime `dependencies`
- CI używa `uv sync --group test --no-dev` dla testów i `uv sync --no-dev` dla PROD
- Test: `test_dependency_groups_separation.py`

**Polityka aktualizacji zależności:**
1. LOCK — bieżący stan (`uv.lock` gwarantuje reproducible builds)
2. MONITOR — Trivy/OSV-Scanner wykrywa CVE
3. REVIEW — deweloper ocenia wpływ
4. UPDATE — świadoma aktualizacja w `pyproject.toml`
5. TEST — `uv lock` + `make check`
6. RELEASE — commit + push

**Zaimplementowane:**
- Dependabot — automatyczne PR dla `uv`, GitHub Actions, Docker (`.github/dependabot.yml`)
- SBOM — generowanie CycloneDX przez Syft w CI (`.github/workflows/ci.yml`)

**Przyszłe wdrożenia (po zbliżeniu się do TEST/PROD):**
- SLSA/Cosign — build provenance i image signing (po wdrożeniu PROD)

**Uwaga:** Renovate nie jest planowany. Dependabot jest używany jako narzędzie do automatycznych aktualizacji zależności.

---

## Kolejność w CI

```
CI Pipeline (make check)
│
├── 1. Code Quality
│   ├── Ruff format --check
│   ├── Ruff lint
│   ├── mypy
│   └── lint-imports (Import Linter)
│
├── 2. Tests
│   └── pytest (jednostkowe + architektura FF-001..FF-023)
│
├── 3. Architecture Audit
│   └── audit_contracts.py (graf zależności)
│
├── 4. Complexity / Quality
│   ├── Radon
│   └── Xenon
│
├── 5. Security / Supply Chain
│   ├── Semgrep
│   ├── OSV-Scanner
│   └── Trivy (HIGH/CRITICAL)
│
└── 6. Infrastructure Governance
    ├── Hadolint
    └── Checkov
```

**Zasada kolejności:**
- Code Quality → Tests → Architecture Audit → Complexity → Security → Infrastructure
- `make check` uruchamia wszystkie warstwy sekwencyjnie; brak early-exit między warstwami
- FF-015, FF-016, FF-017, FF-019, FF-020 (Operational + Observability Governance) są częścią warstwy Tests (pytest)

---

## Blokujące vs Advisory — podsumowanie

### Blokujące (CI fails)

| Mechanizm | Gdzie | Co chroni |
|-----------|-------|-----------|
| Import Linter | `.importlinter` | Kierunek zależności |
| Architecture Tests — FF-001 (Dependency Direction) | `test_dependency_direction.py` | Kierunek zależności (komplementarne do Import Lintera) |
| Architecture Tests — FF-002 (Domain Purity) | `test_domain_purity.py` | Brak Model w domenie |
| Architecture Tests — FF-003 (Repository Contracts) | `test_repository_contracts.py` | Pełność implementacji portów |
| Architecture Tests — FF-004 (API DTO Gating) | `test_api_dto_gating.py` | Walidacja wejścia w API |
| Architecture Tests — FF-005 (DI Container Completeness) | `test_di_container_completeness.py` | Rejestracja UseCase'ów |
| Architecture Tests — FF-007 (No Primitive Obsession) | `test_no_primitive_obsession.py` | Typy zwracane przez UseCase'y |
| Architecture Tests — FF-008 (Migration Idempotency) | `test_migration_idempotency.py` | Expand & Contract |
| Architecture Tests — FF-009 (God Class Prevention) | `test_god_class_prevention.py` | Limit modeli na plik |
| Architecture Tests — FF-010 (Badge Rule Immutability) | `test_badge_rule_immutability.py` | Frozen dataclass dla reguł |
| Architecture Tests — FF-015 (Compose Health Checks) | `test_health_checks.py` | Obecność healthcheck |
| Architecture Tests — FF-016 (API Exception Handling) | `test_exception_handling.py` | Obsługa ApplicationException |
| Architecture Tests — FF-017 (Request ID Contract) | `test_request_id_contract.py` | Korelacja żądań |
| Architecture Tests — FF-019 (Structured Error Context) | `test_structured_error_context.py` | RFC 7807 + request_id |
| Architecture Tests — FF-020 (Health Check Semantics) | `test_health_checks.py` | Semantyka healthcheck |
| Architecture Tests — FF-021 (Lockfile Integrity) | `test_lockfile_integrity.py` | `uv.lock` jest committed i śledzony |
| Architecture Tests — FF-023 (Fitness Function Registry Completeness) | `test_fitness_function_registry.py` | Wszystkie FF mają wpis w rejestrze |
| Xenon | `xenon.ini` | Złożoność kodu |
| Trivy | `security-audit` | CVE HIGH/CRITICAL |

### Advisory (CI passes, ale warto sprawdzić)

| Mechanizm | Gdzie | Co chroni |
|-----------|-------|-----------|
| Architecture Tests — FF-006 (DTO Naming Convention) | `test_dto_naming_convention.py` | Konwencja nazewnictwa DTO |
| Architecture Tests — FF-018 (No Sensitive Data in Logs) | `test_no_sensitive_data_in_logs.py` | Wrażliwe dane w logach |
| Architecture Tests — FF-022 (Dependency Groups Separation) | `test_dependency_groups_separation.py` | Rozdzielenie dev/test od runtime |
| Radon | `make complexity-check` | Złożoność — trend over time |
| wily | `make complexity-trend` | Trend jakości |
| Hadolint | `make hadolint` | Jakość Dockerfile |
| Checkov | `make checkov` | Bezpieczeństwo Compose |
| Docker Bench | `make docker-bench` | Konfiguracja hosta Docker |

---

## Wyjątki i uzasadnienia

### Wyjątki architektoniczne (Import Linter)

| Wyjątek | Uzasadnienie | Powiązanie | Status |
|---------|--------------|------------|--------|
| `apps.badges.tasks -> infrastructure.adapters.osm_adapter` | Zadania Celery wywołują OSMAdapter bezpośrednio dla retry logic | DŁUG-001 | Open |
| `apps.badges.models -> infrastructure.schemas.badge_rules_schema` | Walidacja JSONB w modelu Django | DŁUG-002 | Open |
| `apps.tourists.context_processors -> infrastructure.config.map_layers` | Context Processor wstrzykuje warstwy map | DŁUG-003 | Open |
| `infrastructure.adapters.celery_event_publisher -> apps.badges.tasks` | Adapter zdarzeń importuje nazwy zadań Celery | DŁUG-004 | Open |

### Wyjątki Hadolint

| Ostrzeżenie | Uzasadnienie | Status |
|-------------|--------------|--------|
| DL3006 — tag obrazu bazowego | Wersje przypięte przez ARG (`PYTHON_BASE`, `UV_IMAGE`) | Accepted |
| DL3008 — pin pakietów APT | Pakiety zmieniają się często; pinowanie w builderze | Accepted |
| DL3046 — `useradd` bez `-l` | Świadome użycie wysokiego UID (10001) | Accepted |

### Wyjątki Checkov

Brak wyjątków — Checkov przechodzi czysto.

### Wyjątki Trivy

Trivy skanuje zależności deweloperskie Semgrep (przez MCP). Wyjątki w `osv-scanner.toml`:

- `PYSEC-2026-3481`..`PYSEC-2026-3483` — zależności deweloperskie Semgrep
- `PYSEC-2026-3696`..`PYSEC-2026-3699` — zależności deweloperskie
- `GHSA-prg7-hcfm-mfcr` — zależność deweloperska

**Uzasadnienie:** Mitygacja przez `--no-dev` / podział grup w `pyproject.toml`.

---

## Właściciele i odpowiedzialności

| Mechanizm | Właściciel | Odpowiedzialność |
|-----------|-----------|-----------------|
| ADR | Dominik / AI Architect | Tworzenie i aktualizacja decyzji |
| Import Linter | Dominik / AI Architect | Konfiguracja i wyjątki |
| Architecture Tests | Dominik / AI Architect | Dodawanie nowych fitness functions |
| Xenon | Dominik / AI Architect | Ustawianie limitów złożoności |
| Hadolint | Dominik / AI Architect | Baseline i wyjątki |
| Checkov | Dominik / AI Architect | Konfiguracja i skany Compose |
| Trivy | Dominik / AI Architect | Ignore list i tolerancja CVE |
| Docker Bench | Placeholder | Aktualizacja po znalezieniu successor'a |
| Health Checks | Dominik / AI Architect | Utrzymanie healthcheck w Compose |
| API Exception Handling | Dominik / AI Architect | Utrzymanie obsługi ApplicationException w widokach |

---

## Artefakty CI

| Artefakt | Generowany przez | Przechowywany w | Cel |
|----------|------------------|-----------------|-----|
| `dependencies.svg` | `audit_contracts.py` | `docs/dependencies.svg` | Intended Architecture |
| `dependencies-pydeps.svg` | `pydeps` | `docs/architecture/dependencies-pydeps.svg` | Actual Architecture |
| `classes-*.png` | `pyreverse` | `docs/architecture/classes-*.png` | Struktura klas |
| Test coverage | `pytest --cov` | Output terminal | Pokrycie kodu |

---

## Historia zmian

| Wersja | Data | Autor | Opis zmiany |
|--------|------|-------|-------------|
| 1.0 | 2026-08-26 | Dominik / AI Architect | Utworzenie master indexu governance |
