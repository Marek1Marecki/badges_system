# CI ↔ Governance Audit Matrix

> Status: Active  
> Data: 2026-08-29
> Właściciel: Dominik / AI Architect

Ten dokument mapuje każdy krok w `.github/workflows/ci.yml` na odpowiadający mu element w `docs/architecture/governance.md`.

## Zasada

Każdy krok CI musi mieć jasno przypisany: **Tier** (Gate/Diagnostic/Experimental) i **Charakter** (blocking/advisory).

---

## Matrix: CI Step → Governance

| CI Job | CI Step | Tool | FF | Tier | Mode | Blocking? | Workflow |
|--------|---------|------|----|------|------|-----------|----------|
| `static-analysis-and-unit-tests` | Ruff format | Ruff | code quality | Gate | blocking | ✅ | ci.yml |
| `static-analysis-and-unit-tests` | Ruff check | Ruff | code quality | Gate | blocking | ✅ | ci.yml |
| `static-analysis-and-unit-tests` | Mypy | Mypy | type checking | Gate | blocking | ✅ | ci.yml |
| `static-analysis-and-unit-tests` | Import Linter | Import Linter | FF-001, FF-002 | Gate | blocking | ✅ | ci.yml |
| `static-analysis-and-unit-tests` | Semgrep | Semgrep | security | Gate | blocking | ✅ | ci.yml |
| `static-analysis-and-unit-tests` | audit_contracts.py | AST audit | custom FFs | Gate | blocking | ✅ | ci.yml |
| `static-analysis-and-unit-tests` | Unit tests | pytest | FF-002..005, FF-007, FF-010.. | Gate | blocking | ✅ | ci.yml |
| `diagnostics` | complexity-check | Radon + Xenon | — | Diagnostic | advisory | ❌ | ci.yml |
| `diagnostics` | complexity-trend | wily | — | Diagnostic | advisory | ❌ | ci.yml |
| `diagnostics` | graph-all | pydeps + pyreverse | Discovery | Diagnostic | advisory | ❌ | ci.yml |
| `diagnostics` | arch-docs | PlantUML | C4 Model | Diagnostic | advisory | ❌ | ci.yml |
| `diagnostics` | api-docs | pdoc | Documentation | Diagnostic | advisory | ❌ | ci.yml |
| `diagnostics` | coverage-diff | diff-cover | — | Diagnostic | advisory | ❌ | ci.yml |
| `integration-tests` | Docker build | Docker | Build Once | BUILD | N/A | ✅ | ci.yml |
| `integration-tests` | Trivy scan | Trivy | FF-013 | Gate | blocking (CRITICAL+HIGH) | ✅ | ci.yml |
| `integration-tests` | SBOM generation | Syft | Supply chain | BUILD | N/A | ✅ | ci.yml |
| `integration-tests` | SBOM validation | grep | Deployment invariant | Gate | blocking | ✅ | ci.yml |
| `integration-tests` | Test scripts check | Docker exec | Deployment invariant | Gate | blocking | ✅ | ci.yml |
| `integration-tests` | Integration tests | pytest | integration | Gate | blocking | ✅ | ci.yml |
| `e2e-tests` | Playwright tests | Playwright | scenarios | Gate | blocking | ✅ | ci.yml |
| — (separate) | CodeQL | CodeQL | security scanning | Gate (Security) | blocking | ✅ | codeql.yml |
| — (manual) | Mutation testing | mutmut | Test quality | Diagnostic | advisory | ❌ | `make mutation` |
| `e2e-tests` | Accessibility (axe) | axe-core via Playwright | WCAG 2 AA | Experimental (validated PoC, candidate for Diagnostic) | advisory | ❌ | `make experimental-axe` |

---

## Inne workflow-y

| Workflow | Trigger | Cel | Tier |
|----------|---------|-----|------|
| `codeql.yml` | push, PR, schedule, manual | Security analysis (SAST/SEMA) | Gate (Security) |
| `dependabot.yml` | schedule | Dependency updates | N/A (Automation) |

### Dependabot — nie jest Tier'em analitycznym

Dependabot jest **mechanizmem automatyzacji**, nie narzędziem oceny invariantów. Generuje PR-y z aktualizacjami, które następnie przechodzą przez pełny pipeline CI (Gate).

| Ecosystem | open-pull-requests-limit | Cooldown | Uzasadnienie |
|-----------|------------------------|----------|--------------|
| `uv` | 10 | 7 days | Szybkie CI, wiele zależności |
| `github-actions` | 5 | 7 days | Akcje są pinowane do SHA, limit niższy |
| `docker` | 5 | 7 days | Obrazy bazowe, limit niższy |

---

## Zasady utrzymania matrixu

1. Każda zmiana w `ci.yml`, `codeql.yml` lub `dependabot.yml` musi być odzwierciedlona w tej tabeli.
2. Nowy krok musi mieć przypisany Tier — jeżeli nie wiadomo, domyślnie jest **Diagnostic**.

---

## axe: Experimental → Candidate for Diagnostic

### Status: Validated PoC

**Data walidacji:** 2026-08-31  
**Wynik:** 7/7 testów axe przechodzi w pełnym E2E (root, login, 404, dashboard, catalog, ranking, profile)  
**Realne problemy wykryte i naprawione:**
- Kontrast kolorów (WCAG 2 AA violations) — 4 naprawy w szablonach
- Etykiety formularzy (`<label for>` ↔ `id`) — 3 pola w `profile.html`

### Kryteria awansu

| Kryterium | Status | Uwagi |
|-----------|--------|-------|
| Działa stabilnie lokalnie | ✅ | `make experimental-axe` |
| Działa w pełnym E2E | ✅ | przez `scripts/e2e-run.sh` |
| Wykrywa realne problemy | ✅ | kontrast, label, semantyka |
| Problemy zostały naprawione | ✅ | potwierdzone przez testy ponowne |
| Testy obejmują kluczowe widoki | ✅ | root, login, dashboard, catalog, ranking, profile, 404 |
| False positives pod kontrolą | 🟡 | DO SPRAJDZENIA — przy kolejnych zmianach UI |
| Polityka severity zdefiniowana | 🟡 | DO ZDEFINIOWANIA — które violations blokują? |
| Stabilność przy CI pipeline | 🟡 | DO SPRAJDZENIA — axe jako część E2E, nie osobny job |

### Ścieżka awansu

```
Experimental
    ↓
Validated PoC  (obecny stan — 2026-08-31)
    ↓
Diagnostic     (po spełnieniu kryteriów, w tym polityce severity)
    ↓
Gate           (tylko jeśli accessibility stanie się blocking invariant)
```

### Decyzja

axe pozostaje **poza standardowym CI** (`ci.yml`) jako `Experimental`. Nie tworzy osobnego joba CI. Jego naturalne miejsce to część warstwy E2E:

```
              CI
               │
    ┌──────────┴──────────┐
    │                     │
   GATE                DIAGNOSTIC
    │                     │
    │                     ├── complexity
    │                     ├── architecture
    │                     └── documentation
    │
    └── E2E
          │
    ┌─────┴─────┐
    │           │
 Playwright   axe
 functional   accessibility
```
3. **Gate × blocking** może dodać maksymalnie 3 sekundy do pipeline'u. Wszystko co wolniej → Diagnostic.

---

## k6: Experimental → Validated PoC → Candidate for Diagnostic

### Status: Validated PoC

**Data walidacji:** 2026-08-31  
**Wynik:** 50 VUs / 4 min / 0% errors / p95 ~607ms  
**Baseline:** p95 ≈ 607ms przy 50 VUs (wartość odniesienia, nie aspiracja)

### Scenariusz testowy

- Ramp-up: 10→50 VUs (30s + 1m)
- Steady state: 50 VUs (1m)
- Ramp-down: 50→0 VUs (30s)
- Endpointy: `/`, `/health/`, `/accounts/login/`, `/api/openapi.json`

### Wyniki PoC

| Metryka | Wartość | Status |
|---------|---------|--------|
| Iteracje | 2 838 | ✅ |
| Requesty | 14 190 | ✅ |
| Checks | 11 352 / 11 352 (100%) | ✅ |
| Failed requests | 0 (0%) | ✅ |
| Avg response | 191 ms | ✅ |
| p95 | 607 ms | ⚠️ (threshold 500ms) |
| Max | 1 910 ms | ⚠️ |
| Throughput | 64,8 req/s | ✅ |

### Kryteria awansu

| Kryterium | Status | Uwagi |
|-----------|--------|-------|
| Działa stabilnie | ✅ | `make experimental-k6` |
| 0% failed requests | ✅ | przy 50 VUs |
| Obserwowany baseline | ✅ | p95 ≈ 607ms (do powtórzenia 5×) |
| Test obejmuje kluczowe endpointy | 🟡 | tylko proste HTTP, brak GIS/PostGIS |
| Threshold spełniony | ❌ | p95 > 500ms — to baseline, nie regression |
| Stabilny w czasie | 🟡 | DO SPRAJDZENIA — 5 powtórzeń |
| Obecny w standardowym CI | ❌ | Experimental |

### Decyzja

k6 pozostaje **poza standardowym CI** jako Experimental. Threshold `p95 < 500ms` zostaje niezmieniony jako aspiracja. Baseline ~607ms służy jako punkt odniesienia do obserwacji w kolejnych zmianach aplikacji.

Ścieżka awansu:
```
Experimental
    ↓
Validated PoC  (obecny stan — 2026-08-31)
    ↓
Candidate for Diagnostic  (po 5 stabilnych pomiarach)
```
