# CI/CD Enforcement

**Status:** Egzekwowalny  
**Zakres:** Wszystkie projekty z pipeline CI

---

## Zasada nadrzędna

Pipeline nie instaluje środowiska developerskiego. **Pipeline egzekwuje kontrakt.**

Jeśli kontrakt jest naruszony → merge jest zablokowany.

---

## Two-Stage Pipeline

Pipeline dzieli się na dwa niezależne gate'y. `security-gate` uruchamia się tylko gdy `quality-gate` przejdzie. `lint-docker` uruchamia się równolegle z `quality-gate` — jest niezależny od obu gate'ów.

```
quality-gate (lock check, make check, secrets-check)    lint-docker (hadolint)
    ↓ tylko jeśli ✅                                         ↓ niezależnie
security-gate (docker build, trivy, runtime integrity)
integration-gate (make test-all — testy integracyjne i ML)
```

**Uzasadnienie:** Nie budujemy obrazu Docker dopóki kod nie przeszedł quality gate — oszczędza czas i zasoby CI. `integration-gate` jest oddzielony od `security-gate` — oba zależą od `quality-gate`, ale działają niezależnie od siebie. Testy integracyjne nie blokują budowania obrazu i vice versa. `lint-docker` jest oddzielony bo lintowanie Dockerfile to infrastruktura, nie jakość kodu aplikacji.

---

## Kompletny workflow GitHub Actions

```yaml
name: Contract Enforcement

on:
  pull_request:
  push:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}
  # Na PR: anuluje przestarzałe buildy gdy wchodzi nowy commit — oszczędza minuty CI.
  # Na main: nigdy nie anuluje — każdy commit musi mieć pełny, udokumentowany dowód
  # poprawności (traceability, ciągłość artefaktów Docker do release'u).

jobs:
  quality-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true

      - name: Validate lock synchronization
        run: uv lock --check

      - name: Install dependencies
        run: uv sync --group dev

      - name: Run make check
        run: make check
        # make check zawiera: ruff format, ruff lint, mypy, lint-imports, fast tests, audit
        # lint-imports weryfikuje kierunek zależności zgodnie z .importlinter
        # audit_contracts.py weryfikuje: forbidden imports, determinism, dataframe, env access

      - name: Validate secrets
        run: make secrets-check
        # Wymaga zarejestrowania sekretów z .env.example jako GitHub Secrets w repozytorium.
        # Każdy nowy klucz dodany do .env.example musi być dodany do GitHub Secrets — inaczej
        # ten krok zakończy się FAIL. To jest celowe zachowanie kontraktu, nie błąd pipeline.

  integration-gate:
    runs-on: ubuntu-latest
    needs: quality-gate        # uruchamia się tylko gdy quality-gate ✅
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true

      - name: Install dependencies
        run: uv sync --group dev

      - name: Run full test suite (integration + coverage)
        run: make test-all
        # test-all uruchamia wszystkie testy włącznie z @pytest.mark.integration i @pytest.mark.ml
        # Oddzielony od quality-gate — wolniejszy, zależy od infrastruktury (DB, API)
        # Nie blokuje security-gate: docker build nie czeka na testy integracyjne

  lint-docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Lint Dockerfile (hadolint)
        uses: hadolint/hadolint-action@v3.1.0
        with:
          dockerfile: Dockerfile
    # Uruchamiany równolegle z quality-gate — Dockerfile to infrastruktura,
    # nie kod aplikacji. Nie blokuje security-gate jeśli quality-gate nie przeszedł
    # (hadolint nie zależy od wyniku quality-gate).

  security-gate:
    runs-on: ubuntu-latest
    needs: quality-gate        # uruchamia się tylko gdy quality-gate ✅
                               # nie czeka na integration-gate — docker build jest niezależny
    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: docker build --no-cache -t app:test .

      - name: Log base image SHA
        run: docker inspect python:3.12-slim-bookworm --format='{{index .RepoDigests 0}}'

      - name: Scan vulnerabilities (Trivy)
        uses: aquasecurity/trivy-action@0.30.0
        with:
          image-ref: app:test
          severity: CRITICAL,HIGH
          ignore-unfixed: true
          exit-code: 1

      - name: Ensure non-root runtime
        run: |
          CONTAINER_UID=$(docker run --rm app:test id -u)
          if [ "$CONTAINER_UID" = "0" ]; then
            echo "Container runs as root. Contract violation."
            exit 1
          fi

      - name: Runtime integrity — whitelist
        run: |
          docker run --rm --read-only --tmpfs /tmp app:test \
            python -c "open('/tmp/test', 'w').write('ok')"

      - name: Runtime integrity — blacklist
        run: |
          docker run --rm --read-only --tmpfs /tmp app:test \
            python -c "open('/app/test', 'w')" 2>&1 | grep -q "Read-only" \
            || { echo "SECURITY BREACH: /app is writable!"; exit 1; }
```

---

## Wariant ML — quality-gate z dev-slim

W projektach ML quality-gate używa `dev-slim` by uniknąć pobierania Torch (~864MB). Pełny obraz Docker z Torch budowany jest tylko w security-gate.

```yaml
  quality-gate:
    steps:
      - name: Install dependencies (slim — bez Torch)
        run: uv sync --only-group dev-slim

      - name: Run make check
        run: make check
        # check używa tylko ruff, mypy, pytest na logice biznesowej
        # Torch nie jest potrzebny do weryfikacji jakości kodu

  security-gate:
    steps:
      - name: Build full Docker image (z Torch)
        run: docker build --no-cache -t app:test .
        # security-gate buduje pełny obraz — Trivy skanuje wszystko
```

**Uwaga o cache runnera:** `uv sync --only-group dev-slim` modyfikuje `.venv` na CI runnerze — usuwa z niego pakiety produkcyjne (Torch) jeśli były wcześniej zcache'owane. To nie jest problem dla pipeline, bo Docker build w security-gate jest zawsze izolowany (`--no-cache`, własne środowisko obrazu). Świadomość: cache `astral-sh/setup-uv` przyspiesza `quality-gate`, ale `security-gate` i tak buduje Torch od zera wewnątrz Dockerfile — to jest oczekiwane zachowanie.

---

## Zasady

- Pipeline blokuje merge do `main` w przypadku naruszenia kontraktu
- `make check` uruchamiany na CI runnerze, nie wewnątrz kontenera
- `--no-cache` przy `docker build` eliminuje złudne sukcesy oparte o lokalne warstwy
- `astral-sh/setup-uv@v5` z `enable-cache: true` przyspiesza kolejne uruchomienia
- Każdy job ma jedną odpowiedzialność
- Brak cichych fallbacków
- Akcje GitHub pinowane do konkretnych wersji (`@vX.Y.Z`) — `@master` jest ruchomym celem i łamie reproducibility. Wyjątek: `actions/checkout` i `astral-sh/setup-uv` używają tagów major (`@v4`, `@v5`) jako stabilnych aliasów.

---

## Kolejność egzekwowania

```
validate-lock → make check → secrets-check → docker build → log SHA → trivy → non-root → runtime-integrity
                                           ↘ make test-all (integration + ML)
lint-docker (równolegle z quality-gate)
```

Pierwsze dwa kroki (validate-lock, make check) są najszybsze i najczęściej łapią błędy — dlatego są pierwsze. `integration-gate` i `security-gate` startują równolegle po przejściu `quality-gate` — są od siebie niezależne. `lint-docker` działa równolegle — lintowanie Dockerfile nie wymaga wyniku quality-gate i nie blokuje security-gate samodzielnie.
