# Development & CI/CD Flow

Diagram przedstawia pełny przepływ od klonowania repo do produkcji. Każdy krok powiązany z konkretnym kontraktem.

---

```mermaid
flowchart TD
    START([START]) --> clone

    clone["git clone &lt;repo&gt;
        📄 Documentation Contract"]
    setup["make setup
        uv sync + pre-commit install
        📄 Makefile Contract
        📄 Dependency Governance"]
    check_local["make check
        format + lint + type-check + test
        📄 Makefile Contract
        📄 Test Coverage & Quality"]
    docker_dev["make docker-up
        dev containers
        📄 Docker Contract"]
    work["Development Work
        feature/* / bugfix/* / hotfix/*
        📄 Branching Strategy"]
    check_before_push["make check before push
        📄 Makefile Contract"]
    push["git push / Pull Request
        📄 Branching Strategy"]

    subgraph quality_gate["quality-gate"]
        validate_lock["uv lock --check
            📄 Dependency Governance"]
        ci_check["make check
            ruff + mypy + lint-imports + fast tests + audit
            📄 Makefile Contract
            📄 Test Coverage & Quality
            📄 Domain Purity Contract"]
        secrets["make secrets-check
            .env.example validation
            📄 Secrets Management"]
    end

    lint_docker["lint-docker (równolegle)
        hadolint Dockerfile
        📄 Docker Contract"]

    subgraph integration_gate["integration-gate (równolegle z security-gate, wymaga quality-gate ✅)"]
        test_all["make test-all
            testy integracyjne + e2e
            📄 Test Coverage & Quality"]
    end

    subgraph security_gate["security-gate (wymaga quality-gate ✅)"]
        build_docker["docker build --no-cache
            multi-stage, /opt/venv, hardening
            📄 Docker Contract
            📄 Base Image Policy"]
        log_sha["Log base image SHA
            📄 Base Image Policy"]
        trivy["Trivy CRITICAL/HIGH → FAIL
            .trivyignore policy
            📄 Vulnerability Scanning"]
        runtime_tests["Runtime Integrity Tests
            whitelist /tmp + blacklist /app
            📄 Runtime Integrity"]
    end

    release["git tag -a vX.Y.Z
        CHANGELOG.md
        📄 Release & Tagging"]
    deploy["Deployment / Production
        📄 Docker Contract"]

    clone --> setup
    setup --> check_local
    check_local --> docker_dev
    docker_dev --> work
    work --> check_before_push
    check_before_push --> push
    push --> validate_lock
    validate_lock --> ci_check
    ci_check --> secrets
    secrets --> test_all
    secrets --> build_docker
    push --> lint_docker
    build_docker --> log_sha
    log_sha --> trivy
    trivy --> runtime_tests
    runtime_tests --> release
    test_all --> release
    release --> deploy
    deploy --> END([END / Feedback Loop])
```

---

## Kontrakty architektoniczne — egzekwowane przez `make check`

Kontrakty architektoniczne nie są osobnym krokiem w pipeline — są wbudowane w `make check` przez `mypy` i `lint-imports`:

```
make check
├── ruff format --check     → styl kodu
├── ruff lint               → reguły jakości + TID251 (zakaz bibliotek w domain/)
├── mypy                    → typy per-warstwa (strict dla domain/ i application/)
├── lint-imports            → kierunek zależności (Domain Purity, Import Direction)
├── pytest -m "not integration"  → testy jednostkowe + coverage
└── audit_contracts.py      → AST scan: forbidden imports, determinism, dataframe, env access
```

| Kontrakt | Narzędzie w make check |
|----------|----------------------|
| Domain Purity | ruff TID251 + import-linter + audit_contracts.py |
| Error Boundary | ruff B001 (bare except) + mypy |
| Determinism | audit_contracts.py + ruff banned-api |
| DataFrame | audit_contracts.py + mypy (typy) |
| Configuration | audit_contracts.py (os.getenv w application/) |
