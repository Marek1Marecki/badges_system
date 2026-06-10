# Documentation Contract

**Status:** Egzekwowalny  
**Zakres:** Wszystkie projekty

---

## Obowiązkowe elementy dokumentacji projektu

| Dokument | Zawartość | Egzekwowanie |
|----------|-----------| --------------|
| `README.md` | Opis projektu, Quick Start, zależności | CI: plik istnieje + sekcja Quick Start |
| `docs/contracts/` | Wszystkie kontrakty projektowe | CI: katalog istnieje, zawiera pliki |
| `CHANGELOG.md` | Historia zmian, release notes | Weryfikacja przy każdym release |
| `.env.example` | Lista wymaganych sekretów (bez wartości) | Zgodnie z Secrets Management |
| `.python-version` | Jawna wersja Pythona wymagana przez `uv` | Zgodność z Dockerfile i CI |

### Zasada `.python-version` — spójność wersji

Wersja Pythona musi być identyczna w trzech miejscach:

| Miejsce | Przykład |
|---------|----------|
| `.python-version` | `3.12` |
| `Dockerfile` | `FROM python:3.12-slim-bookworm` |
| `pyproject.toml` | `requires-python = ">=3.12"` |

Rozbieżność między tymi trzema plikami → naruszenie kontraktu.

---

## Egzekwowanie w CI

Minimalny, niezawodny zestaw walidacji:

```yaml
- name: Validate documentation
  run: |
    test -f README.md
    grep -q "Quick Start" README.md
    test -d docs/contracts/
```

Zero zewnętrznych narzędzi → brak fałszywych alarmów.

---

## Code Documentation — Docstrings

### Standard: Google Style

Obowiązkowy format dla wszystkich publicznych klas i metod. Skupiamy się na "DLACZEGO" — nie na "CO" (typy są w mypy strict).

```python
def calculate_aging_bonus(task: Task, days_overdue: int) -> float:
    """Oblicza bonus priorytetyzacji dla przeterminowanych zadań.

    Im dłużej zadanie jest przeterminowane, tym wyższy bonus.
    Waga 1.0 zapobiega eksponencjalnemu wzrostowi przy długich zaległościach.

    Args:
        task: Zadanie domenowe do oceny.
        days_overdue: Liczba dni od terminu wykonania.

    Returns:
        Wartość bonusu w zakresie [0.0, 10.0].

    Raises:
        ValidationError: Jeśli days_overdue jest ujemne.
    """
```

### Priorytety warstwowe

| Warstwa | Wymaganie | Zakres |
|---------|-----------|--------|
| `domain/` | **Obowiązkowe** | Wszystkie publiczne klasy i metody |
| `application/` | **Obowiązkowe** | Use case'y — opis przepływu biznesowego |
| `infrastructure/` | Zalecane | Tylko niestandardowe rozwiązania |
| `tests/` | Opcjonalne | Tylko złożone fixtures |

### Egzekwowanie przez Ruff (reguły D)

```toml
[tool.ruff.lint]
select = ["E", "F", "I", "B", "C4", "D"]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.per-file-ignores]
"**/tests/**" = ["D"]
"**/migrations/**" = ["D"]
"**/admin.py" = ["D"]
"infrastructure/**" = ["D"]   # stopniowe wdrożenie
```

**Zasada stopniowego wdrożenia:** Wdrażaj per-warstwa: najpierw `domain/`, potem `application/`, na końcu `infrastructure/`. Używaj `# noqa: D` per-plik podczas przejścia.

---

## Sphinx — standard dokumentacji technicznej

Sphinx jest standardowym narzędziem dokumentacji dla wszystkich projektów.

**Katalog:** `docs_sphinx/` (nie `docs/` — zostawiony dla innych celów)

**Zależności (dev-only):**
```bash
uv add --group dev sphinx sphinx-rtd-theme sphinx-autodoc-typehints
```

**Konfiguracja `docs_sphinx/source/conf.py`:**
```python
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",   # obsługa Google Style
    "sphinx.ext.viewcode",   # linki do kodu źródłowego
]
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}
napoleon_google_docstring = True
napoleon_include_private_with_doc = False
```

**Struktura `docs_sphinx/source/`** odzwierciedla architekturę heksagonalną:
```
docs_sphinx/source/
├── conf.py
├── index.rst
├── domain.rst          # domain/ — 100% coverage obowiązkowe
├── application.rst     # application/ — use case'y
└── infrastructure.rst  # infrastructure/ — opcjonalne
```

### `--strict` policy

- Nowe projekty: `--strict` od początku
- Istniejące projekty: `--strict` po pełnym pokryciu `domain/` i `application/`

**Sphinx nie jest częścią `make check`** — `docs-html` to oddzielny target. Dokumentacja nie blokuje merge do `main`.

---

## Filozofia

- **Jawność** — dokumentacja jest wyrocznią, kod i CI muszą się do niej odwoływać
- **Przewidywalność** — każdy projekt ma identyczną strukturę katalogów
- **Egzekwowalność** — tylko to co można sprawdzić automatycznie jest kontraktem
- **Minimalizm** — lepiej mało i aktualne niż dużo i nieaktualne
