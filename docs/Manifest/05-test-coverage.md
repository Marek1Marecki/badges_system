# Test Coverage & Quality

**Status:** Egzekwowalny  
**Zakres:** Wszystkie projekty Python

---

## Zasada nadrzędna

**`make check = CI quality-gate`** — CI uruchamia dokładnie to co `make check`. Pre-commit uruchamia `make check` lub jego szybki podzbiór (`pre-commit ⊆ make check`) — nigdy nic spoza `make check`.

---

## Obowiązkowe narzędzia

| Narzędzie | Cel |
|-----------|-----|
| `ruff` | Linting i formatowanie |
| `mypy` | Type checking |
| `import-linter` | Weryfikacja kierunku zależności między warstwami |
| `pytest` + `pytest-cov` | Testy i coverage |

### mypy + import-linter — kompletna weryfikacja architektury

Mypy weryfikuje typy per-warstwa. `import-linter` weryfikuje kierunek zależności między warstwami. Razem stanowią kompletną weryfikację architektury.

Mypy nie wykryje że `domain/` importuje z `infrastructure/` jeśli typy są poprawne — import-linter wykryje to zawsze.

| Narzędzie | Co weryfikuje | Konfiguracja |
|-----------|--------------|--------------|
| mypy | Poprawność typów per-warstwa | `pyproject.toml [tool.mypy]` |
| import-linter | Kierunek zależności między warstwami | `.importlinter` |

### Mypy — poziomy rygorystyczności

| Warstwa | Poziom | Uzasadnienie |
|---------|--------|--------------|
| `domain/`, `application/` | **strict** | Rdzeń projektu — całkowita pewność typów, wykrywa błędy architektoniczne |
| `infrastructure/`, `apps/` | **pragmatic** | Adaptery zewnętrzne mogą nie mieć stubów (Django, Torch) |

```toml
[tool.mypy]
plugins = ["pydantic.mypy", "pandera.mypy"]
disallow_untyped_defs = true
warn_return_any = true
ignore_missing_imports = true

# Konfiguracja wtyczki Pydantic — likwiduje fałszywe błędy w warstwie application/
# (dynamiczne __init__, aliasy). Bundlowana z pydantic v2 — bez dodatkowej zależności.
# pandera.mypy — likwiduje fałszywe błędy dla Series[T] i DataFrameModel (15-dataframe-contract.md).
[tool.pydantic-mypy]
init_forbid_extra = true
init_typed = true
warn_required_dynamic_aliases = true
warn_untyped_fields = true

[[tool.mypy.overrides]]
module = ["infrastructure.*", "apps.*"]
disallow_untyped_defs = false

[[tool.mypy.overrides]]
module = ["django.*", "torch.*", "whisperx.*"]
ignore_missing_imports = true
```

---

## Zasada 10 sekund (lokalny feedback)

`make check` uruchamiany przez pre-commit nie powinien trwać dłużej niż 10–15 sekund. Przekroczenie tego progu powoduje że deweloper zaczyna używać `--no-verify` — co łamie zasadę `pre-commit = make check = CI`.

### Podział testów

| Marker | Typ | Czas | Uruchamiany w |
|--------|-----|------|---------------|
| brak markera | Jednostkowy | < 1s | `make test` (lokalnie i CI quality-gate) |
| `@pytest.mark.integration` | Integracyjny, dotyka DB/API | > 1s | `make test-all` (CI) |
| `@pytest.mark.ml` | Wymaga Torch/WhisperX | > 10s | `make test-all` (CI) |

### Implementacja w Makefile

```makefile
test:      ## Szybkie testy jednostkowe — lokalna pętla feedbacku
    uv run pytest $(TEST_DIRS) -m "not integration and not ml" \
        --cov=$(PY_DIRS) --cov-report=term-missing \
        --cov-fail-under=$(MIN_COVERAGE)

test-all:  ## Pełna paczka testów — CI i przed release
    uv run pytest $(TEST_DIRS) \
        --cov=$(PY_DIRS) --cov-report=term-missing \
        --cov-fail-under=$(MIN_COVERAGE)
```

`make check` wywołuje `test` (szybki) — jest częścią `quality-gate`. CI wywołuje `test-all` (pełny) w osobnym jobie `integration-gate`, który startuje po przejściu `quality-gate` równolegle z `security-gate`.

### Oznaczanie testów

```python
# Test jednostkowy — nie dotyka DB
def test_task_title_cannot_be_empty() -> None:
    with pytest.raises(ValidationError):
        Task(title="")


# Test integracyjny — dotyka DB
@pytest.mark.integration
def test_task_save_to_db(db) -> None:
    task = Task.objects.create(title="Buy milk")
    assert Task.objects.filter(title="Buy milk").exists()
```

### Konfiguracja w `pyproject.toml`

```toml
[tool.pytest.ini_options]
markers = [
    "integration: testy dotykające bazy danych lub zewnętrznych API",
    "ml: testy wymagające Torch/WhisperX",
]
addopts = ["--strict-markers"]
```

---

## Coverage

Minimalny próg: `MIN_COVERAGE=80` (konfigurowalny per projekt). Pokrycie poniżej progu → pipeline FAIL. Raport w CI: terminal + HTML + XML.

**Zakaz:** obniżania progu coverage pod pretekstem "fazy MVP". Jeśli kod jest na `main`, musi być przetestowany.

### Wyjątek: projekty ML — obniżony próg

Projekty ML zawierają adaptery zewnętrznych bibliotek (Torch, WhisperX) których nie można przetestować bez pełnego środowiska. Obniżony próg globalny jest świadomym wyjątkiem — nie zaniedbaniem.

**Kluczowa zasada:** obniżenie `MIN_COVERAGE` nie zwalnia z testowania logiki biznesowej. Rzeczywiste pokrycie `domain/` i `application/` musi wynosić ≥80% — mierzone osobno przez wykluczenie adapterów ML z pomiaru.

**Wymagania:**
- `MIN_COVERAGE` obniżone do 20 z komentarzem uzasadniającym w Makefile
- `[tool.coverage.run] omit` wyklucza adaptery ML z pomiaru globalnego
- `domain/` i `application/` pokryte w ≥80% — weryfikowalne przez `coverage report --include="domain/*,application/*"`
- Wyjątek udokumentowany w `pyproject.toml`

```makefile
# ML project: globalne MIN_COVERAGE=20 bo adaptery ML są wykluczone z pomiaru.
# Logika biznesowa (domain/ + application/) jest pokryta w >=80%.
# Weryfikacja: coverage report --include="domain/*,application/*"
MIN_COVERAGE ?= 20
```

```toml
[tool.coverage.run]
omit = [
    "infrastructure/adapters/ml/*",
    "infrastructure/adapters/whisper/*",
]
```

---

## Pre-commit

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: uv-lock-check
        name: uv lock check
        entry: uv lock --check
        language: system
        always_run: true
        pass_filenames: false

      - id: check
        name: make check
        entry: make check
        language: system
        always_run: true
        pass_filenames: false
```

Hook `uv-lock-check` blokuje commit jeśli `pyproject.toml` został zmieniony bez regeneracji `uv.lock`. Uruchamiany przed `make check`.

### Wyjątek: projekty ML z ciężkimi zależnościami systemowymi

Projekty wymagające Torch lub GDAL mogą stosować uproszczony pre-commit gdy pełna instalacja jest niepraktyczna lokalnie. Warunki: pełne `make check` działa w CI, wyjątek udokumentowany w `pyproject.toml`, deweloper uruchamia `make check` świadomie przed PR.

```yaml
# .pre-commit-config.yaml (wariant ML — tylko ruff)
repos:
  - repo: local
    hooks:
      - id: ruff-format
        name: ruff format
        entry: uv run ruff format --check
        language: system
        types: [python]
      - id: ruff-lint
        name: ruff lint
        entry: uv run ruff check
        language: system
        types: [python]
```

---

## Ruff — reguły dokumentacji (D)

Ruff pilnuje obecności docstringów w `domain/` i `application/`:

```toml
[tool.ruff.lint]
# E, F   - błędy i standardy stylu (pycodestyle, pyflakes)
# I      - sortowanie importów (isort)
# B      - częste błędy i pułapki Pythona (bugbear)
# C4     - czystsze list/dict comprehensions
# D      - wymóg docstringów (pydocstyle) — patrz niżej
# S      - bezpieczeństwo: zakaz eval, assert w kodzie produkcyjnym (bandit)
# UP     - nowoczesna składnia Pythona 3.11+ (union A | B, dict zamiast Dict)
# TID    - tidy imports: egzekwuje banned-api z 14-domain-purity.md i 10-secrets-management.md
select = ["E", "F", "I", "B", "C4", "D", "S", "UP", "TID"]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.per-file-ignores]
"**/tests/**" = ["D", "S101"]     # D: docstringi zbędne w testach; S101: assert jest OK w pytest
"**/domain/**" = ["S101"]         # S101: assert jest dozwolony w domain/ do weryfikacji invariantów
"**/migrations/**" = ["D"]
"**/admin.py" = ["D"]
```

**Zasada stopniowego wdrożenia:** Dodanie reguł `D` do istniejącego projektu powoduje wiele błędów jednocześnie. Kolejność: `domain/` → `application/` → `infrastructure/`. Używaj `# noqa: D` per-plik podczas przejścia.

---

## Django — filterwarnings

Ostrzeżenia `naive datetime` zaśmiecają logi testów. Wyciszamy je jawnie:

```toml
[tool.pytest.ini_options]
filterwarnings = [
    "ignore:DateTimeField .* received a naive datetime:RuntimeWarning",
]
```

Zasada: wyciszamy tylko ostrzeżenia które są świadomie akceptowane — nie używamy `ignore::DeprecationWarning` jako blanket suppression.

---

## Biblioteki testowe

### Pandera — walidacja DataFrame

**Status:** Zalecane dla projektów z Pandas  
**Gdzie:** `infrastructure/adapters/`, `application/dto/`  
**Zakaz:** `domain/` — domena nie zna struktury DataFrame

Szczegóły: `15-dataframe-contract.md`.

### Hypothesis — property-based testing

**Status:** Opcjonalne — nie wymagane przez `make check`  
**Gdzie:** `tests/unit/domain/` dla Value Objects i reguł domenowych

```toml
[dependency-groups]
dev = ["hypothesis>=6.0.0"]
```

### VCR.py — deterministyczne testy API

**Status:** Zalecane dla projektów z zewnętrznymi API  
**Gdzie:** wyłącznie `tests/integration/`

VCR nagrywa odpowiedź HTTP przy pierwszym uruchomieniu (`cassette`), przy kolejnych używa nagrania. Testy integracyjne stają się szybkie i niezależne od sieci. Cassettes commitować do repozytorium — są częścią kontraktu testowego.

**Sanityzacja przed commitem:** Cassettes mogą zawierać nagłówki autoryzacyjne z oryginalnego requestu (np. `Authorization: Bearer <token>`). Przed commitem zweryfikuj że plik YAML nie zawiera żadnych wartości sekretów — VCR domyślnie nagrywa pełne nagłówki. Użyj `filter_headers` lub `filter_query_parameters` w konfiguracji VCR:

```python
@vcr.use_cassette(
    "tests/cassettes/google_sheets.yaml",
    filter_headers=["authorization"],  # usuń nagłówki auth z cassette
    filter_query_parameters=["key", "token"],  # usuń tokeny z URL
)
def test_fetch_returns_valid_schema():
    adapter = GoogleSheetsAdapter()
    df = adapter.fetch()
    MeasurementsSchema.validate(df)
```

### Faker — realistyczne dane testowe

**Status:** Zalecane  
**Gdzie:** wyłącznie `tests/`

```toml
[dependency-groups]
dev-slim = ["faker>=24.0.0"]
```

---

## Rozstrzyganie sporów

W przypadku konfliktu między lokalnym środowiskiem a CI, pipeline CI jest punktem odniesienia. Każde obejście `make check` wymaga uzasadnienia w `CHANGELOG.md`.
