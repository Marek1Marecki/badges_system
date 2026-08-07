# Development Workflow

**Status:** Egzekwowalny (agreguje zasady z pozostałych kontraktów)  
**Zakres:** Wszystkie projekty Python/Docker

---

## Cel dokumentu

Mapa codziennej pracy dewelopera. Agreguje i przypomina zasady z pozostałych kontraktów w kontekście praktycznego workflow. Nie wprowadza nowych zasad — wskazuje gdzie szukać szczegółów.

---

## Środowisko lokalne

### Rekomendacja: natywny Linux lub WSL2

Narzędzia tego systemu (uv, Docker, pre-commit, mypy) są zaprojektowane dla środowisk Unix. Praca "pół-Windows, pół-Linux" generuje błędy ścieżek, uprawnień i line endings które są trudne do debugowania.

**Rekomendacja:**
- Natywny Ubuntu/Debian — optymalne
- WSL2 — akceptowalne pod warunkiem:
  - IDE działa **wewnątrz** WSL (VS Code z rozszerzeniem WSL, PyCharm Linux)
  - Projekt jest sklonowany **wewnątrz** systemu plików WSL (`~/projects/`), nie na `/mnt/c/`
  - Docker Desktop skonfigurowany z integracją WSL2

**Zakaz:** edytowanie plików z Windows Explorer lub IDE działającym na Windows z projektem w WSL — powoduje konflikty uprawnień i CRLF line endings.

### Podstawowe komendy dev

```bash
make setup        # instalacja zależności i pre-commit (idempotentne)
make run          # uruchomienie aplikacji lokalnie (bez infrastruktury)
make check        # pełna walidacja: format + lint + type-check + test
make docker-up    # uruchomienie kontenerów dev
```

### Rozgraniczenie dev / prod

- `docker-compose.dev.yml` — lokalne środowisko developerskie
- `docker-compose.prod.yml` — CI i produkcja
- `.env.dev`, `.env.prod` — jawnie rozdzielone zmienne środowiskowe
- Narzędzia developerskie działają lokalnie przez `uv` — nie wewnątrz kontenera

---

## Zarządzanie zależnościami

```bash
uv update <package>
uv sync --frozen
make check
```

Szczegóły: `02-dependency-governance.md`.

Konfiguracja środowiska: wszystkie wymagane zmienne z `.env.example` muszą być obecne w lokalnym `.env`. `.env` nie jest commitowany — jest w `.gitignore`.

---

## Codzienny workflow

```bash
git checkout main
git pull origin main
git checkout -b feature/<opis>

# praca lokalna...

make check                     # przed commitem — obowiązkowe
git push -u origin feature/<opis>
# Pull Request → CI → merge → usunięcie gałęzi
```

Szczegóły dotyczące gałęzi: `03-branching-strategy.md`.

---

## Self-Review przed PR

Nawet w jednoosobowym projekcie PR wymaga self-review:

- `make check` zielony
- Dokumentacja zaktualizowana jeśli potrzeba
- Każdy commit powiązany z taskiem: `TASK-<id>: opis` lub `BUG-<id>: opis`
- `CHANGELOG.md` zaktualizowany jeśli release
- `.env.example` aktualny jeśli zmieniono zmienne środowiskowe

---

## Feature Flags

Eksperymentalne funkcje przez zmienne środowiskowe:

```bash
FEATURE_X_ENABLED=true make run
```

Pozwala commitować nieukończony kod bez wpływu na produkcję.

---

## Developer Onboarding

Szybkie odtworzenie środowiska na nowym komputerze:

```bash
git clone <repo>
make setup        # uv sync + pre-commit install
make check        # pełna weryfikacja środowiska
make docker-up    # uruchomienie aplikacji
```

`make check` po `make setup` potwierdza że środowisko działa zgodnie z kontraktami. Jeśli `make check` przechodzi lokalnie — przejdzie w CI.

---

## Dokumentacja

Dokumentacja aktualizowana równolegle z kodem:

- `README.md` — instrukcje startowe i Quick Start
- `docs/Manifest/` — aktualne kontrakty
- `CHANGELOG.md` — historia zmian przy każdym release

---

## Powiązanie z kontraktami

| Kontrakt | Obszar |
|----------|--------|
| Makefile Contract | `make check`, `make setup`, `make run` |
| Docker Contract | dev/prod compose, `/opt/venv` |
| Dependency Governance | `uv update`, `uv sync --frozen` |
| Branching Strategy | gałęzie, PR, merge |
| Secrets Management | `.env.example`, `.env` lokalny |
| Test Coverage & Quality | `make check`, coverage |
| Release & Tagging | tagowanie po merge do main |
| CI/CD Enforcement | pipeline egzekwuje wszystko |
