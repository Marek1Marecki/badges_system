# Dependency Governance

**Status:** Egzekwowalny  
**Zakres:** Wszystkie projekty Python z uv

---

## Filozofia

Każda instalacja musi być identyczna — niezależnie od maszyny, daty ani kontekstu. Każda aktualizacja zależności jest świadoma, udokumentowana i możliwa do odwrócenia.

**Priorytety:** Reproducibility → Jawność → Bezpieczeństwo → Deterministyczność → Prostota

---

## Zasady podstawowe

Wszystkie zależności aplikacji definiowane są w `pyproject.toml`. `uv.lock` jest obowiązkowy, synchronizowany z `pyproject.toml` i commitowany do repozytorium.

Build w Dockerfile używa `uv sync --no-dev --frozen`:
- `--frozen` odmawia buildu jeśli `uv.lock` jest niezsynchronizowany z `pyproject.toml`
- Brak dynamicznego rozwiązywania zależności
- Pełna deterministyczność

---

## Grupy zależności

```toml
[project]
dependencies = [
    "django>=5.0",
    "loguru>=0.7.0",
]

[dependency-groups]
dev = [
    "ruff>=0.3.0",
    "mypy>=1.9.0",
    "pytest>=8.0.0",
    "pytest-cov>=4.0.0",
    "import-linter>=2.0.0",
]
```

### Wariant ML — dev-slim

Projekty z Torch/WhisperX definiują dodatkową grupę `dev-slim` zawierającą tylko narzędzia jakości kodu. CI quality-gate używa flag `--no-dev --group dev-slim` by zainstalować aplikację i narzędzia jakości, unikając pobierania pełnej grupy dev (i ~864MB Torcha).

```toml
[dependency-groups]
dev-slim = [
    "ruff>=0.3.0",
    "mypy>=1.9.0",
    "pytest>=8.0.0",
    "import-linter>=2.0.0",
]
dev = [
    {include-group = "dev-slim"},
    "torch>=2.0.0",
    "whisperx>=3.0.0",
]
```

---

## Procedura aktualizacji

```bash
uv update <package>
uv sync --frozen
make check
```

Po przejściu `make check`:
1. Zmiany w `uv.lock` zatwierdzić w repo
2. Wpis w `CHANGELOG.md`

Aktualizacje bezpieczeństwa mają najwyższy priorytet.

---

## Egzekwowanie w CI

```yaml
- name: Validate lock synchronization
  run: uv lock --check
```

`uv lock --check`:
- Nie instaluje zależności
- Nie tworzy środowiska wirtualnego
- Nie modyfikuje plików
- Weryfikuje zgodność `pyproject.toml` ↔ `uv.lock`

Niespójność → exit code ≠ 0 → pipeline FAIL → blokada merge.

---

## Zakazane praktyki

- `pip install <package>` bez uv
- Brak `uv.lock` w repozytorium
- `COPY pyproject.toml uv.lock* ./` (gwiazdka — lockfile opcjonalny)
- Automatyczne aktualizacje podczas buildów Docker
- Pre-release paczki (`alpha`, `beta`, `rc`) w locku produkcyjnym
- Zależności developerskie w runtime produkcyjnym
