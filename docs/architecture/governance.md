# Architecture Governance

> **Wersja:** 2.1  
> **Data:** 2026-08-29  
> **Właściciel:** Dominik / AI Architect  
> **Zasada:** Ten dokument jest master indexem wszystkich mechanizmów governance w projekcie. Model opiera się na dwóch wymiarach: INVARIANTS (co chronimy) i TOOLS (jak to sprawdzamy). Każde narzędzie ma TIER (Gate/Diagnostic/Experimental) i charakter wykonania (Blocking/Advisory).

---

## Trójtorowy Model Governance i Tooling Lifecycle

Projekt rygorystycznie rozdziela narzędzia nadzoru na trzy kasty operacyjne (Tiers), aby zapobiec paraliżowi wdrożeniowemu (Alert Fatigue) oraz tzw. *Tool Sprawl*. Każde narzędzie w systemie podlega cyklowi życia (Lifecycle), w którym musi udowodnić swoją wartość (Exit Criteria), zanim awansuje do grupy blokującej.

```text
                     TOOLING LIFECYCLE
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
       [1. CANDIDATE]                [2. EXPERIMENTAL]
      Wstępna analiza                Weryfikacja hipotezy
        narzędzia                     (Sandbox / Manual)
                                            │
                                  ┌─────────┴─────────┐
                             Value Proven        No Value / Slow
                                  │                   │
                                  ▼                   ▼
                           [3. DIAGNOSTIC]         [REMOVE]
                            Obserwacja i
                            Analiza trendów
                            (Non-blocking)
                                  │
                          Promote to Gate
                                  │
                                  ▼
                              [4. GATE]
                             Ochrona systemu
                               (Blocking)
 ```

### Stany Wewnątrz Fazy EXPERIMENTAL (R&D Lifecycle)

Narzędzia znajdujące się w warstwie eksperymentalnej nie są "czarną dziurą". Podlegają one mikro-cyklowi życia:
1. **Unvalidated:** Narzędzie świeżo dodane do repozytorium. Trwają próby uruchomienia (np. błędy kontenerów, walka z konfiguracją).
2. **Validated PoC (Proof of Concept):** Narzędzie udowodniło, że działa, wykonuje test end-to-end i nie generuje awarii infrastruktury (np. `Testcontainers`, `Axe-Playwright`, `Hypothesis`). Znalazło co najmniej 1 realny błąd.
3. **Candidate for Diagnostic:** Po okresie "leżakowania" (np. 1-2 miesiące) i udowodnieniu, że narzędzie nie zgłasza irytujących *False Positives* przy zmianach w kodzie, zespół rozważa przesunięcie go do grupy nienadzorowanej (Diagnostic) w `make check`.

---

### Klasyfikacja Operacyjna (Obecny Stan)

| Poziom (Tier) | Cel i Pytanie | Charakter CI | Przykładowe Narzędzia w Projekcie |
|:---|:---|:---|:---|
| **GATE** | „Czy wolno zaakceptować zmianę?” | Blocking (Fail-Fast) | Ruff, Mypy, Import Linter, Trivy, pytest, Semgrep, Hadolint, Checkov |
| **DIAGNOSTIC** | „Co się dzieje z jakością / trendami?” | Advisory (Raportowanie) | Radon, Wily, pydeps, Checkov, Hadolint, pytest-randomly, diff-cover, gitleaks, mutmut |
| **EXPERIMENTAL** | „Czy ta technika ma u nas sens operacyjny?” | Manual (Poza głównym CI) | Schemathesis, Testcontainers, axe-playwright |

### Zasady Wdrażania Nowych Narzędzi (Exit Criteria)

- Narzędzie przebywające w klasie EXPERIMENTAL posiada jasno zdefiniowaną Hipotezę (np. "Czy axe-playwright wykryje realne błędy WCAG na frontendzie?").
- Jeśli po okresie testowym hipoteza nie zostanie potwierdzona lub narzut operacyjny przewyższy wartość diagnostyczną, narzędzie musi zostać niezwłocznie usunięte z projektu i odnotowane w archiwum ADR (lub rejestrze długów) jako próba odrzucona.
- Degradacja z GATE do DIAGNOSTIC jest zjawiskiem naturalnym, jeśli narzędzie zaczyna generować zbyt dużo fałszywych alarmów (False Positives) i spowalnia prędkość dostarczania funkcji.

---

## Przegląd warstw governance

```
                     GOVERNANCE
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       INVARIANTS     TOOLS         META
          │              │              │
             FF-001..FF-024  pytest        ADR
          │          import-linter  Debt Register
          │          trivy          FF Registry
          │          radon
          │          xenon
          │          hadolint
          │          checkov
          │          wily
          ▼              ▼
    CO-DESIGN ──────→ EXECUTION
    (FF ↔ Tool)      Tier × Mode
```

**Dwa wymiary:**
- **INVARIANTS** — `FF-001..FF-024` w `docs/architecture/fitness-functions.md`. Odpowiadają na pytanie: „Jakiego invariant’a chcemy chronić?”
- **TOOLS** — mechanizmy sprawdzające invariants. Odpowiadają na pytanie: „Czym sprawdzamy ten invariant?”
- **CO-DESIGN** — jeden tool może realizować wiele FF, jedno FF może być realizowane przez więcej niż jeden tool.

**Trzy poziomy zaufania (TIER):**

```
                     TIER
           ┌──────────┼──────────┐
           ▼          ▼          ▼
         GATE     DIAGNOSTIC EXPERIMENTAL
           │          │          │
      "must pass" "tell me"  "let's find
                    why"      out"
```

**Charakter wykonania (MODE):**
- `blocking` — łamanie blokuje CI/merge
- `advisory` — łamanie generuje ostrzeżenie, ale nie blokuje; informacja dla developera

**Kombinacje Tier × Mode:**
- `Gate × blocking` — `make check`
- `Diagnostic × advisory` — świadomie uruchamiane przez developera
- `Experimental × advisory` — świadomie uruchamiane w sandboxie

---

## Klasyfikacja toolingu: Tier × Mode

Każde narzędzie ma przypisany **Tier** (poziom zaufania) i **Mode** (charakter wykonania):

```
                     GOVERNANCE
                          │
           ┌──────────────┼──────────────┐
           ▼              ▼              ▼
         GATE         DIAGNOSTIC     EXPERIMENTAL
           │              │              │
      "must pass"    "tell me why"   "let's find out"
           │              │              │
      blocking       advisory        advisory
```

### GATE × blocking

Narzędzia, które **muszą przejść** w każdym przebiegu CI. Ich łamanie blokuje merge/PR.

| Tool | Plik/Konfiguracja | Realizuje FF | Tryb |
|------|-------------------|--------------|------|
| Import Linter | `.importlinter` | FF-001, FF-002 | blocking |
| pytest | `tests/architecture/` | FF-003..FF-005, FF-007, FF-010, FF-015..FF-017, FF-019..FF-021, FF-023 | blocking |
| Trivy | `make security-audit` | FF-013 | blocking (HIGH/CRITICAL) |
| Ruff / mypy / lint-imports | `make check` | code quality | blocking |

### DIAGNOSTIC × advisory

Narzędzia, które **dostarczają informacji**, ale nie blokują CI. Uruchamiane świadomie przez developera.

| Tool | Plik/Konfiguracja | Realizuje FF | Tryb |
|------|-------------------|--------------|------|
| pytest | `tests/architecture/` | FF-001, FF-006, FF-008, FF-009, FF-018, FF-022 | advisory |
| Radon | `make complexity-check` | — | advisory |
| Xenon | `make complexity-check` | — | advisory |
| wily | `make complexity-trend` | — | advisory |
| Hadolint | `.hadolint.yaml` | FF-011 | advisory |
| Checkov | `.checkov.yaml` | FF-012 | advisory |
| Docker Bench | `make docker-bench` | FF-014 | advisory |
| pytest-randomly | `make test-random` | — | advisory |
| pytest-timings | `make test-timings` | — | advisory |
| pytest-html | `make test-html` | — | advisory |
| diff-cover | `make coverage-diff` | — | advisory |
| detect-secrets | `make secret-scan` | — | advisory |
| docstr-coverage | `make docstr-coverage` | — | advisory |
| djLint | `make lint-templates` | — | advisory |
| mutmut | `make mutation` | Test quality (mutation score) | advisory |

### EXPERIMENTAL × advisory

Narzędzia w **kontrolowanej eksperymentacji**. Można je uruchamiać świadomie, ale nie są częścią standardowego CI.

| Tool | Plik/Konfiguracja | Cel |
|------|-------------------|-----|
| Schemathesis | `make experimental-schemathesis` | API fuzzing |
| Testcontainers | `make experimental-testcontainers` | Izolowane środowisko PostGIS w testach |
| axe-playwright | `make experimental-axe` | Accessibility |
| k6 | `make experimental-k6` | Load testing |
| OWASP ZAP | `make experimental-zap` | DAST |
| Factory Boy | `make experimental-factory-boy` | Test data architecture |
| pytest-xdist | `make experimental-xdist` | Parallel testing |
| pytest-benchmark | `make experimental-benchmark` | Microbenchmark |

**Zasady:**
- Experimental nie blokuje CI
- Po eksperymencie decyzja: awans do Diagnostic, awans do Gate, lub usunięcie
- Każde narzędzie Experimental musi mieć clear exit criteria

### Testcontainers — scope i ograniczenia

Testcontainers służy do izolowanego uruchomienia zależności infrastrukturalnych (obecnie PostgreSQL/PostGIS) w środowisku testowym deweloperskim lub CI. Nie jest przeznaczony do weryfikacji wdrożeń PRE-PROD/PROD.

Różnica względem istniejącego `integration-tests`:
- `integration-tests` używa Docker Compose z ustalonymi obrazami i wolumenami — to środowisko stabilne, powtarzalne, częścią standardowego CI.
- Testcontainers tworzy efemeryczny kontener na czas sesji testowej — to narzędzie developerskie do eksperymentów z konfiguracją zależności.

Wnioski:
- Nie uruchamiać Testcontainers w standardowym CI — istniejące joby `integration-tests` i `e2e-tests` już realizują cel testowania z prawdziwą infrastrukturą.
- Nie mapować Testcontainers na środowisko `badges_preprod` — to inna kategoria walidacji (deployment/environment validation).
- Po okresie eksperymentalnym podejmować decyzję: awans do Diagnostic, awans do Gate, lub usunięcie.

### axe — scope i ograniczenia

axe (accessibility testing) jest narzędziem do automatycznego sprawdzania dostępności WCAG 2 AA na stronach HTML. Uruchamiany jest jako `make experimental-axe` przy użyciu Playwright + axe-core CDN.

- **Obecny zakres:** 7 kluczowych widoków (root, login, 404, dashboard, catalog, ranking, profile)
- **Wynik PoC (2026-08-31):** 7/7 testów przechodzi
- **Realne problemy wykryte:** kontrast kolorów (4 naprawy), brak etykiet formularzy (3 pola)
- **Poziom blocking:** ❌ Experimental — nie blokuje CI
- **Architektura:** część warstwy E2E (Playwright), a nie osobny job CI

Po zwalidowaniu wartości, axe jest kandydatem na awans do Diagnostic (advisory), a nie Gate.

### k6 — scope i ograniczenia

k6 jest narzędziem do load/performance testingu HTTP. Uruchamiany jest jako `make experimental-k6` przy użyciu skryptu `scripts/k6/load-test.js`.

- **Obecny scenariusz:** 50 VUs, 4 minuty, ramp-up/ramp-down
- **Testowane endpointy:** `/`, `/health/`, `/accounts/login/`, `/api/openapi.json`
- **Wynik PoC (2026-08-31):** 0% failed requests, 100% checks, avg 191ms, p95 607ms
- **Threshold HTTP p95 < 500ms:** ⚠️ przekroczony (607ms) — wynik obserwacyjny, nie regression
- **Poziom blocking:** ❌ Experimental — nie blokuje CI
- **Baseline:** p95 ≈ 607ms przy 50 VUs (wartość odniesienia, nie aspiracja)
- **Ograniczenia:** testuje tylko proste endpointy HTTP, nie obejmuje zapytań GIS/PostGIS, wyszukiwania, rankingów czy ciężkich endpointów API

Po uzyskaniu kilku stabilnych pomiarów, k6 jest kandydatem na awans do Diagnostic jako performance baseline.

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

### INVARIANTS — Fitness Functions

Fitness Functions to zbiór invariant’ów architektonicznych (`FF-001..FF-023`). Każdy FF odpowiada na pytanie: „Jakiego invariant’a chcemy chronić?”

Pełny rejestr: [`docs/architecture/fitness-functions.md`](fitness-functions.md)

**Mapowanie FF → Tools:**

| FF | Invariant | Tool | Tier | Mode |
|----|-----------|------|------|------|
| FF-001 | Dependency Direction | Import Linter | Gate | blocking |
| FF-001 | Dependency Direction | pytest | Diagnostic | advisory |
| FF-002 | Domain Purity | Import Linter | Gate | blocking |
| FF-002 | Domain Purity | pytest | Gate | blocking |
| FF-003 | Repository Contracts | pytest | Gate | blocking |
| FF-004 | API DTO Gating | pytest | Gate | blocking |
| FF-005 | DI Container Completeness | pytest | Gate | blocking |
| FF-006 | DTO Naming Convention | pytest | Diagnostic | advisory |
| FF-007 | No Primitive Obsession | pytest | Gate | blocking |
| FF-008 | Migration Idempotency | pytest | Diagnostic | advisory |
| FF-009 | God Class Prevention | pytest | Diagnostic | advisory |
| FF-010 | Badge Rule Immutability | pytest | Gate | blocking |
| FF-011 | Dockerfile Hygiene | Hadolint | Diagnostic | advisory |
| FF-012 | Compose Security | Checkov | Diagnostic | advisory |
| FF-013 | Image Vulnerability Scanning | Trivy | Gate | blocking |
| FF-014 | Docker Bench Security | Docker Bench | Diagnostic | advisory |
| FF-015 | Compose Health Checks | pytest | Gate | blocking |
| FF-016 | API Exception Handling | pytest | Gate | blocking |
| FF-017 | Request ID Contract | pytest | Gate | blocking |
| FF-018 | No Sensitive Data in Logs | pytest | Diagnostic | advisory |
| FF-019 | Structured Error Context | pytest | Gate | blocking |
| FF-020 | Health Check Semantics | pytest | Gate | blocking |
| FF-021 | Lockfile Integrity | pytest | Gate | blocking |
| FF-022 | Dependency Groups Separation | pytest | Diagnostic | advisory |
| FF-023 | Fitness Function Registry Completeness | pytest | Gate | blocking |

**Kluczowe zasady:**
- Jeden FF może być realizowany przez wiele tooli (np. FF-001 przez Import Linter i pytest)
- Jeden tool może realizować wiele FF (np. pytest realizuje 20+ FF)
- Tier jest przypisany do **tool’u**, nie do FF — ten sam FF może mieć różne tier w zależności od toola

### TOOLS — Mechanizmy sprawdzające

| Tool | Tier | Mode | Realizuje FF | Charakter |
|------|------|------|--------------|----------|
| Import Linter | Gate | blocking | FF-001, FF-002 | Kierunek zależności |
| pytest | Gate | blocking | FF-003..FF-005, FF-007, FF-010, FF-015..FF-017, FF-019..FF-021, FF-023 | Architecture Tests |
| pytest | Diagnostic | advisory | FF-001, FF-006, FF-008, FF-009, FF-018, FF-022 | Architecture Tests |
| Trivy | Gate | blocking | FF-013 | CVE HIGH/CRITICAL |
| Ruff / mypy / lint-imports | Gate | blocking | code quality | Code quality |
| Radon | Diagnostic | advisory | — | Złożoność |
| Xenon | Diagnostic | advisory | — | Złożoność threshold |
| wily | Diagnostic | advisory | — | Trend jakości |
| Hadolint | Diagnostic | advisory | FF-011 | Jakość Dockerfile |
| Checkov | Diagnostic | advisory | FF-012 | Bezpieczeństwo Compose |
| Docker Bench | Diagnostic | advisory | FF-014 | Audyt hosta Docker |
| pytest-randomly | Diagnostic | advisory | — | Test dependencies |
| pytest-timings | Diagnostic | advisory | — | Test timings |
| pytest-html | Diagnostic | advisory | — | Test report |
| diff-cover | Diagnostic | advisory | — | Coverage nowego kodu |
| detect-secrets | Diagnostic | advisory | — | Secret discovery |
| docstr-coverage | Diagnostic | advisory | — | Docstring coverage |
| djLint | Diagnostic | advisory | — | Django templates |

### Wyjątki

**Import Linter — wyjątki:**

| Wyjątek | Uzasadnienie | Powiązanie | Status |
|---------|--------------|------------|--------|
| `apps.badges.tasks -> infrastructure.adapters.osm_adapter` | Zadania Celery wywołują OSMAdapter bezpośrednio dla retry logic | DŁUG-001 | Open |
| `apps.badges.models -> infrastructure.schemas.badge_rules_schema` | Walidacja JSONB w modelu Django | DŁUG-002 | Open |
| `apps.tourists.context_processors -> infrastructure.config.map_layers` | Context Processor wstrzykuje warstwy map | DŁUG-003 | Open |
| `infrastructure.adapters.celery_event_publisher -> apps.badges.tasks` | Adapter zdarzeń importuje nazwy zadań Celery | DŁUG-004 | Open |

**Import Linter a testy architektury:**
- `test_dependency_direction.py` (FF-001) jest komplementarny do Import Lintera — test dostarcza diagnostykę w pytest, ale Import Linter jest źródłem prawdy.
- `test_domain_purity.py` (FF-002) nie powtarza już sprawdzania importów (to obowiązek Import Lintera `domain-purity`). Test chroni tylko invariant behawioralny: brak dziedziczenia po `Model` w warstwie domenowej, który Import Linter nie może wykryć.

### Hadolint — baseline

| Ostrzeżenie | Status | Uzasadnienie |
|-------------|--------|--------------|
| DL3006 — tag obrazu bazowego | ⚠️ Non-blocking | Wersje przypięte przez ARG (`PYTHON_BASE`, `UV_IMAGE`) |
| DL3008 — pin pakietów APT | ⚠️ Non-blocking | Pakiety zmieniają się często; pinowanie w builderze |
| DL3046 — `useradd` bez `-l` | ⚠️ Non-blocking | Świadome użycie wysokiego UID (10001) dla django_user |

**Polityka:** Obecny baseline jest zaakceptowany. Nowe warningi nie powinny być dodawane bez uzasadnienia.

### Trivy — wyjątki

Trivy skanuje zależności deweloperskie Semgrep (przez MCP). Wyjątki w `osv-scanner.toml`:

- `PYSEC-2026-3481`..`PYSEC-2026-3483` — zależności deweloperskie Semgrep
- `PYSEC-2026-3696`..`PYSEC-2026-3699` — zależności deweloperskie
- `GHSA-prg7-hcfm-mfcr` — zależność deweloperska

**Uzasadnienie:** Mitygacja przez `--no-dev` / podział grup w `pyproject.toml`.

---

## Kolejność w CI

```text
CI Pipeline (Gate)
│
├── static-analysis-and-unit-tests
│   ├── Ruff format --check
│   ├── Ruff lint
│   ├── Mypy
│   ├── Import Linter
│   ├── Semgrep
│   ├── audit_contracts.py
│   └── pytest (unit tests)
│
├── integration-tests
│   ├── Docker build (Build Once)
│   ├── Trivy (Gate, HIGH/CRITICAL)
│   ├── SBOM generation (Syft)
│   ├── SBOM validation (assertion-based)
│   └── Integration tests
│
└── e2e-tests
    └── Playwright

Diagnostics (Diagnostic Tier — advisory, non-blocking)
│
├── complexity-check (Radon + Xenon)
├── complexity-trend (wily)
├── graph-all (pydeps + pyreverse)
├── arch-docs (PlantUML C4)
├── api-docs (pdoc)
└── coverage-diff (diff-cover)
```

> **Uwaga:** Mutation testing (mutmut) jest w tierze Diagnostic, ale **nie** jest częścią automatycznego jobu `diagnostics` w ci.yml — jest uruchamiany ręcznie jako `make mutation` ze względu na koszt CPU (pełny run trwa godziny).
>
> Baseline: [`docs/experimental-mutmut-baseline.md`](../experimental-mutmut-baseline.md)

**Zasada:**
- `static-analysis-and-unit-tests` uruchamia tylko **Gate** — tools które muszą przejść przed merge.
- `diagnostics` jest uruchamiany jako **separate job** z `if: always()` i `continue-on-error: true` — nie blokuje CI.
- **Experimental** jest uruchamiany ręcznie (`make experimental-*`).
- **Diagnostic ręczne** (mutmut) są uruchamiane ręcznie (`make mutation`) ze względu na koszt.

Audyt pełnej macierzy CI ↔ Governance: [`docs/architecture/ci-governance-matrix.md`](ci-governance-matrix.md)

---

## Zasady awansu i degradacji

```
Experimental
     │
     │ proven useful
     ▼
Diagnostic
     │
     │ objective invariant + low FP/FN
     │ + clear remediation
     ▼
Gate
```

```
Gate
  │
  │ false positives / excessive maintenance /
  │ weak architectural invariant
  ▼
Diagnostic
```

**Kryteria awansu Experimental → Diagnostic:**
- Narzędzie przeżyło co najmniej 1 kwartał w użyciu
- Wygenerowało wartość (wykryło coś, co inaczej by przegapiono)
- Ma clear exit criteria i maintenance plan

**Kryteria awansu Diagnostic → Gate:**
- Invariant jest obiektywnie weryfikowalny (nie subiektywny)
- Ma niski poziom false positives i false negatives
- Remediation jest jasne i jednoznaczne
- Łamanie invariant'a oznacza realne ryzyko dla systemu

**Kryteria degradacji Gate → Diagnostic:**
- Narzędzie generuje częste false positives
- Invariant jest słaby lub subiektywny
- Maintenance overhead przekracza wartość
- Istnieje lepszy sposób wykrywania tego samego problemu

**Przykłady:**
- Xenon: Gate → Diagnostic (złożoność to sygnał, nie blocking rule; Radon + wily już dają pomiar/trend)
- FF-009 God Class Prevention: Gate → Diagnostic (proxy metric, heurystyka, nie invariant)
- FF-018 No Sensitive Data in Logs: Gate → Diagnostic (heurystyka, możliwe FP; detect-secrets jako lepszy mechanizm)
- **mutmut: Experimental → Diagnostic** (zakończony 2026-08-29. Po 3 miesiącach eksperymentu mutmut wykrył 5 realnych luk testowych. Wszystkie zostały naprawione bez zmian w kodzie produkcyjnym. Mutation score: ~96.8% killed. Nie awansowano do Gate ze względu na koszt CPU i subiektywność wyników SUSPICIOUS.)

---

## Podsumowanie: Tier × Mode

### 🟢 Gate × blocking (CI fails)

| Tool | Realizuje FF | Plik |
|------|--------------|------|
| Import Linter | FF-001, FF-002 | `.importlinter` |
| pytest | FF-002..FF-005, FF-007, FF-010, FF-015..FF-017, FF-019..FF-021, FF-023 | `tests/architecture/` |
| Trivy | FF-013 | `make security-audit` |
| Ruff / mypy / lint-imports | code quality | `make check` |

### 🟡 Diagnostic × advisory (CI passes, ale warto sprawdzić)

| Tool | Realizuje FF | Plik |
|------|--------------|------|
| pytest | FF-001, FF-006, FF-008, FF-009, FF-018, FF-022 | `tests/architecture/` |
| Radon | — | `make complexity-check` |
| Xenon | — | `make complexity-check` |
| wily | — | `make complexity-trend` |
| Hadolint | FF-011 | `.hadolint.yaml` |
| Checkov | FF-012 | `.checkov.yaml` |
| Docker Bench | FF-014 | `make docker-bench` |
| pytest-randomly | — | `make test-random` |
| pytest-timings | — | `make test-timings` |
| pytest-html | — | `make test-html` |
| diff-cover | — | `make coverage-diff` |
| detect-secrets | — | `make secret-scan` |
| docstr-coverage | — | `make docstr-coverage` |
| djLint | — | `make lint-templates` |
| mutmut | Test quality | `make mutation` |

### 🔵 Experimental × advisory (świadomie uruchamiane)

| Tool | Cel |
|------|-----|
| Schemathesis | API fuzzing |
| Testcontainers | Real PostgreSQL/Redis w testach |
| axe-playwright | Accessibility |
| k6 | Load testing |
| OWASP ZAP | DAST |
| Factory Boy | Test data architecture |
| pytest-xdist | Parallel testing |
| pytest-benchmark | Microbenchmark |

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

### Gate

| Tool | Właściciel | Odpowiedzialność |
|------|-----------|-----------------|
| Import Linter | Dominik / AI Architect | Konfiguracja i wyjątki |
| pytest (Blocking FF) | Dominik / AI Architect | Dodawanie nowych fitness functions |
| Trivy | Dominik / AI Architect | Ignore list i tolerancja CVE |
| Health Checks | Dominik / AI Architect | Utrzymanie healthcheck w Compose |
| API Exception Handling | Dominik / AI Architect | Utrzymanie obsługi ApplicationException w widokach |
| Request ID Contract | Dominik / AI Architect | Utrzymanie middleware request_id |
| Lockfile Integrity | Dominik / AI Architect | Utrzymanie uv.lock w sync |
| Fitness Function Registry | Dominik / AI Architect | Kompletność dokumentacji FF |

### Diagnostic

| Tool | Właściciel | Odpowiedzialność |
|------|-----------|-----------------|
| pytest (Diagnostic FF) | Dominik / AI Architect | Utrzymanie heurystyk i smell detectorów |
| Radon | Dominik / AI Architect | Utrzymanie limitów złożoności |
| Xenon | Dominik / AI Architect | Advisory threshold dla hotspocy |
| wily | Dominik / AI Architect | Trend analysis |
| mutmut | Dominik / AI Architect | Mutation testing — baseline in `docs/experimental-mutmut-baseline.md` |
| Hadolint | Dominik / AI Architect | Baseline i wyjątki |
| Checkov | Dominik / AI Architect | Konfiguracja i skany Compose |
| Docker Bench | Dominik / AI Architect | Placeholder — aktualizacja po znalezieniu successor'a |
| pytest-randomly | Dominik / AI Architect | Wykrywanie zależności między testami |
| pytest-timings | Dominik / AI Architect | Analiza czasu testów |
| pytest-html | Dominik / AI Architect | Raport HTML |
| diff-cover | Dominik / AI Architect | Coverage nowego kodu |
| detect-secrets | Dominik / AI Architect | Secret discovery baseline |
| docstr-coverage | Dominik / AI Architect | Sprawdzanie pokrycia docstringami |
| djLint | Dominik / AI Architect | Jakość Django templates |

### Experimental

| Tool | Właściciel | Odpowiedzialność |
|------|-----------|-----------------|
| Schemathesis | Dominik / AI Architect | API fuzzing experiments |
| Testcontainers | Dominik / AI Architect | Real DB w testach experiments |
| axe-playwright | Dominik / AI Architect | Accessibility experiments |
| k6 | Dominik / AI Architect | Load testing experiments |
| OWASP ZAP | Dominik / AI Architect | DAST experiments |
| Factory Boy | Dominik / AI Architect | Test data architecture experiments |
| pytest-xdist | Dominik / AI Architect | Parallel testing experiments |
| pytest-benchmark | Dominik / AI Architect | Microbenchmark experiments |

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
| 2.0 | 2026-08-27 | Dominik / AI Architect | Utworzenie master indexu governance (CI refactor: Gate/Diagnostic separation, CI↔Governance matrix) |
| 2.1 | 2026-08-29 | Dominik / AI Architect | mutmut awansowany z Experimental do Diagnostic (w wyniku eksperymentu 2026-08-26→2026-08-29). Baseline w `docs/experimental-mutmut-baseline.md`. |
