# Supply Chain & Dependency Governance

> **Wersja:** 1.1  
> **Data:** 2026-08-26  
> **Właściciel:** Dominik / AI Architect  
> **Zasada:** Ten dokument definiuje kontrakty i polityki dotyczące łańcucha dostaw oprogramowania. Wykorzystuje istniejące mechanizmy (uv.lock, pyproject.toml, Dependabot, Trivy, OSV-Scanner, Syft).

---

## Poziomy maturity

### Poziom 1 — Już zaimplementowane

| Mechanizm | Plik/Narzędzie | Rola |
|-----------|----------------|------|
| Lockfile | `uv.lock` | Reproducible builds, pinned transitive dependencies |
| Dependency declaration | `pyproject.toml` | Jedno źródło prawdy dla zależności |
| Dependency groups | `[dependency-groups]` w `pyproject.toml` | Rozdzielenie runtime / test / dev |
| Vulnerability scanning | Trivy, OSV-Scanner, Semgrep | Wykrywanie CVE i sekretów |
| Lockfile validation | `uv lock --check` (pre-commit) | Weryfikacja spójności `uv.lock` z `pyproject.toml` |
| Automated dependency updates | Dependabot (`.github/dependabot.yml`) | Automatyczne PR dla `uv`, GitHub Actions, Docker |
| SBOM | Syft (`.github/workflows/ci.yml`) | Generowanie CycloneDX dla obrazu testowego |
| Runtime vs dev separation | FF-022 (`test_dependency_groups_separation.py`) | Weryfikacja, że narzędzia dev/test nie trafiają do runtime |

### Poziom 2 — Warto rozważyć (przy zbliżaniu się do TEST/PROD)

| Mechanizm | Cel | Status |
|-----------|-----|--------|
| Dependency inventory | Dokumentacja bezpośrednich zależności i ich uzasadnienia | Planned |
| Dependency update policy | Formalny proces aktualizacji zależności | Zaimplementowany w polityce lockfile |

### Poziom 3 — Przyszłość (po wdrożeniu TEST/PROD)

| Mechanizm | Cel | Status |
|-----------|-----|--------|
| SLSA / Build provenance | Udowodnienie pochodzenia artefaktu | Future |
| Cosign / Image signing | Weryfikacja podpisu obrazu w PROD | Future |

**Uwaga:** Renovate nie jest planowany. Dependabot jest używany jako narzędzie do automatycznych aktualizacji zależności. Renovate oferuje więcej możliwości (grouping, automerge), ale wymaga dodatkowej złożoności i nie ma oficjalnego wsparcia dla `uv`/`pyproject.toml` z `[dependency-groups]`. Dla obecnego projektu Dependabot jest wystarczający.

---

## Polityka lockfile

### Zasady

1. **`uv.lock` jest committed** — lockfile jest częścią repozytorium, nie generowany w CI.
2. **Wspólny dla wszystkich środowisk** — DEV, TEST, PRE-PROD, PROD używają tego samego `uv.lock`.
3. **Aktualizacja z kontrolą** — zależności są aktualizowane tylko przez świadomą decyzję dewelopera, nie automatycznie.
4. **Weryfikacja w pre-commit** — `uv lock --check` blokuje commit jeśli `uv.lock` jest niezsynchronizowany z `pyproject.toml`.
5. **Cooldown aktualizacji** — `make lock` generuje nowy lockfile z 7-dniowym cooldownem zależności.

### Proces aktualizacji zależności

```
LOCK (bieżący stan)
    ↓
MONITOR (Trivy / OSV-Scanner wykrywa CVE)
    ↓
REVIEW (deweloper ocenia wpływ)
    ↓
UPDATE (świadoma aktualizacja w pyproject.toml)
    ↓
TEST (uv lock + make check)
    ↓
RELEASE (commit + push)
```

**Zakazane:**
- `uv sync --upgrade` bez konsultacji
- Ręczna edycja `uv.lock`
- Wyłączanie Dependabota lub modyfikacja jego konfiguracji bez zgody maintainera

---

## Polityka dependency groups

### Grupy w `pyproject.toml`

| Grupa | Cel | Przykłady |
|-------|-----|-----------|
| `dependencies` (runtime) | Zależności potrzebne w PROD | Django, psycopg, celery, redis |
| `test` | Zależności do testów | pytest, hypothesis, pytest-django |
| `dev` | Narzędzia deweloperskie | ruff, mypy, pre-commit, semgrep, radon, xenon |

### Zasady

1. **Zero dev leakage** — narzędzia deweloperskie (`ruff`, `mypy`, `semgrep`, `radon`, `xenon`, `wily`, `pre-commit`) pozostają w `[dependency-groups.dev]`.
2. **Zero test leakage** — narzędzia testowe (`pytest`, `hypothesis`, `playwright`) pozostają w `[dependency-groups.test]`.
3. **CI używa `--group test --no-dev`** — testy w CI nie instalują narzędzi dev.
4. **PROD używa `--no-dev`** — obraz produkcyjny nie zawiera narzędzi dev.
5. **Lintery/analyzery w CI** — narzędzia do analizy kodu (Semgrep, Radon, Xenon) są w `dev`, ale CI instaluje je jawnie przez `uv sync --group dev` w osobnym stage'ie.

---

## Polityka SBOM (Software Bill of Materials)

### Cel

SBOM odpowiada na pytanie: **co dokładnie znajduje się w naszym artefakcie produkcyjnym?**

### Wymagania

1. **SBOM generowany dla każdego buildu** — artefakt CycloneDX JSON zawierający pełny inwentarz zależności obrazu.
2. **Format: CycloneDX** — standard branżowy, czytelny przez maszyny i ludzi.
3. **Publikowany jako artefakt CI** — dostępny do audytu bez budowania obrazu.
4. **Weryfikowalny** — pipeline weryfikuje, że w SBOM nie ma zabronionych zależności (np. `mcp`).

### Implementacja

SBOM jest generowany w CI dla każdego buildu obrazu testowego:

```bash
# Generowanie SBOM przez Syft (CycloneDX)
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$(pwd)":/work -w /work \
  anchore/syft:latest \
  packages docker:badges-system:${{ github.sha }} \
  -o cyclonedx-json=sbom.cdx.json
```

**Weryfikacja w CI:**
- Sprawdzenie, czy SBOM nie zawiera zabronionych zależności (np. `mcp`)
- Upload SBOM jako artefakt GitHub Actions (retention 30 dni)

---

## Polityka dependency drift

### Problem

Lockfile gwarantuje stabilność, ale nie rozwiązuje problemu **przestarzałych zależności** z znanymi CVE.

### Wymagania

1. **Codzienne skanowanie OSV-Scanner** — wykrywa przestarzałe zależności z exploitami.
2. **Cotygodniowe PR z Dependabotem** — automatyzuje aktualizacje dla `uv`, GitHub Actions, Docker.
3. **Cooldown 7 dni** — Dependabot nie tworzy kolejnych PR szybciej niż co 7 dni, aby uniknąć flooda.
4. **Priorytetyzacja** — CVE HIGH/CRITICAL wymagają natychmiastowej aktualizacji; MEDIUM/LOW — planowania w następnym sprincie.

### Proces aktualizacji zależności

```
LOCK (bieżący stan: uv.lock)
    ↓
MONITOR (Trivy / OSV-Scanner / Dependabot wykrywa CVE lub dostępną aktualizację)
    ↓
REVIEW (deweloper ocenia wpływ, Dependabot tworzy PR)
    ↓
TEST (uv lock + make check)
    ↓
RELEASE (merge PR)
```

**Zakazane:**
- `uv sync --upgrade` bez konsultacji
- Ręczna edycja `uv.lock`

---

## Polityka provenance (przyszłość)

### Cel

Udowodnić, skąd pochodzi konkretny artefakt produkcyjny.

### Wymagania (po wdrożeniu TEST/PROD)

1. **SLSA build provenance** — każdy build generuje attestation określający: commit SHA, workflow, inputs, outputs.
2. **Cosign image signing** — obrazy PROD są podpisane kluczem prywatnym.
3. **Weryfikacja w PROD** — środowisko produkcyjne uruchamia tylko obrazy z ważnym podpisem.

**Uwaga:** Dependabot jest używany jako narzędzie do automatycznych aktualizacji zależności. Renovate nie jest planowany — Dependabot oferuje wystarczające możliwości dla tego projektu i ma natywne wsparcie dla `uv`, GitHub Actions i Docker.

---

## Wyjątki i uzasadnienia

### Wyjątki dot. zależności

| Zależność | Uzasadnienie | Status |
|-----------|--------------|--------|
| `semgrep` (w `dev`) | Narzędzie analizy bezpieczeństwa, potrzebne tylko w CI | Accepted — mitygacja przez `--no-dev` w PROD |
| `hypothesis` (w `test` i `dev`) | Testy property-based, potrzebne w CI | Accepted — nie trafia do PROD |

---

## Fitness Functions Grupy 11

| ID | Nazwa | Mechanizm | Chroni | Powiązanie | Status |
|----|-------|-----------|--------|------------|--------|
| FF-021 | Lockfile Integrity | pytest | `uv.lock` jest committed i śledzony | — | Blocking |
| FF-022 | Dependency Groups Separation | pytest | Narzędzia dev/test nie mieszają się z runtime | — | Advisory |

### FF-021: Lockfile Integrity

Test weryfikuje, że `uv.lock` istnieje i jest śledzony przez Git. Gwarantuje to, że wszystkie środowiska używają tej samej wersji zależności.

### FF-022: Dependency Groups Separation

Test weryfikuje, że zależności z `[dependency-groups.dev]` i `[dependency-groups.test]` nie pojawiają się w głównej liście `dependencies` w `pyproject.toml`. Zapewnia czystą separację narzędzi deweloperskich od kodu produkcyjnego.
