# CI ↔ Governance Audit Matrix

> Status: Active  
> Data: 2026-08-28  
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
2. Nowy krok musi mieć przypisany Tier — jeśli nie wiadomo, domyślnie jest **Diagnostic**.
3. **Gate × blocking** może dodać maksymalnie 3 sekundy do pipeline'u. Wszystko co wolniej → Diagnostic.
