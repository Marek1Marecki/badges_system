# Documentation Contract

**Status:** Egzekwowalny  
**Zakres:** Wszystkie projekty

---

## Obowiązkowe elementy dokumentacji projektu

| Dokument | Zawartość | Egzekwowanie |
|----------|-----------| --------------|
| `README.md` | Opis projektu, Quick Start, zależności | CI: plik istnieje + sekcja Quick Start |
| `docs/Manifest/` | Wszystkie kontrakty projektowe | CI: katalog istnieje, zawiera pliki |
| `CHANGELOG.md` | Historia zmian, release notes | Weryfikacja przy każdym release |
| `.env.example` | Lista wymaganych sekretów (bez wartości) | Zgodnie z Secrets Management |
| `.python-version` | Jawna wersja Pythona wymagana przez `uv` | Zgodność z Dockerfile i CI |

### Zasada `.python-version` — spójność wersji

Wersja Pythona musi być identyczna w trzech miejscach:

| Miejsce | Przykład |
|---------|----------|
| `.python-version` | `3.14` |
| `Dockerfile` | `FROM python:3.14-slim-bookworm` |
| `pyproject.toml` | `requires-python = ">=3.14,<3.15"` |

Rozbieżność między tymi trzema plikami → naruszenie kontraktu.

---

## Egzekwowanie w CI

Minimalny, niezawodny zestaw walidacji:

```yaml
- name: Validate documentation
  run: |
    test -f README.md
    grep -q "Quick Start" README.md
    test -d docs/Manifest/
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

## Filozofia

- **Jawność** — dokumentacja jest wyrocznią, kod i CI muszą się do niej odwoływać
- **Przewidywalność** — każdy projekt ma identyczną strukturę katalogów
- **Egzekwowalność** — tylko to co można sprawdzić automatycznie jest kontraktem
- **Minimalizm** — lepiej mało i aktualne niż dużo i nieaktualne
