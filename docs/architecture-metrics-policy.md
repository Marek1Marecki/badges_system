# Architecture Metrics Policy

## Cel

Utrzymywanie niskiej złożoności i wysokiej utrzymywalności kodu poprzez ciągłe pomiary i enforcement architektonicznych metryk.

## Narzędzia

| Narzędzie | Rola | Skanuje |
|-----------|------|---------|
| **Radon** | Measurement | Cyclomatic Complexity, Maintainability Index, LOC |
| **Xenon** | Enforcement | Complexity thresholds |
| **wily** | Trend Analysis | Complexity trends over git history |

## Thresholds

### Cyclomatic Complexity (Radon CC / Xenon)

| Poziom | Wartość | Akcja |
|--------|---------|-------|
| A | 1-4 | Brak |
| B | 5-7 | Monitoruj |
| C | 8-10 | **Zaplanuj refactoring** przy najbliższej zmianie |
| D | 11-20 | **Wymaga refactoringu PRZED merge** |
| E | 21-50 | **Blokuje merge** |
| F | 50+ | **Krytyczny — natychmiastowa akcja** |

### Maintainability Index (Radon MI)

| Poziom | Wartość | Akcja |
|--------|---------|-------|
| A | 100-20 | Brak |
| B | 19-10 | Monitoruj |
| C | 9-0 | **Zaplanuj refactoring** |
| D | <0 | **Natychmiastowa akcja** |

### Xenon Configuration

```ini
[xenon]
max-absolute = B
max-average = A
max-modules = 10
```

- **max-absolute = B**: żaden plik nie może mieć complexity > B
- **max-average = A**: średnia complexity projektu ≤ A
- **max-modules = 10**: max 10 plików powyżej B

## Reguły decyzyjne

### Complexity może rosnąć w czasie, ale nie może skakać

- A → B: bez działania
- B → C: zaplanuj refactoring przy zmianie kodu
- C → D: **wymaga refactoringu PRZED merge**
- D → E: **blokuje merge**
- E → F: **krytyczny — natychmiastowa akcja**

### Maintainability Index

- A → B: bez działania
- B → C: zaplanuj refactoring
- C → D: **wymaga refactoringu PRZED merge**
- D → F: **blokuje merge**

## Wyjątki

### Skrypty narzędziowe

Pliki w `scripts/` mogą mieć wyższy MI niż kod produkcyjny, ponieważ naturalnie zawierają więcej zagnieżdżeń.

**Dopuszczalne wartości dla `scripts/`:**
- MI ≤ C
- Complexity ≤ C

### Widoki Django

Pliki w `apps/*/views.py` często mają wyższą complexity z powodu obsługi wielu przypadków w jednym miejscu.

**Dopuszczalne wartości dla `apps/*/views.py`:**
- Complexity ≤ C
- MI ≤ C

## CI Integration

### Krok 1: `make complexity-check`

Uruchamiane w CI przy każdym push do `main`:

```yaml
- name: Analiza Złożoności (Radon + Xenon)
  run: make complexity-check
```

**Składa się z:**
- `radon cc` — cyclomatic complexity, threshold B
- `radon mi` — maintainability index, threshold C
- `xenon` — enforcement, max-absolute B, max-average A

**FAILuje na:**
- Wystąpienie complexity > B
- Wystąpienie MI < C
- Xenon: więcej niż 10 plików powyżej B
- Xenon: średnia complexity > A

### Krok 2: `make complexity-trend`

Uruchamiane w CI przy każdym push do `main`:

```yaml
- name: Analiza Trendów Złożoności (wily)
  run: make complexity-trend | tee complexity-trend.txt
```

**Artifacts:**
- `complexity-trend.txt` — przechowywane 30 dni

## Monitoring

### Co tydzień

```bash
make complexity-trend
```

Porównuj wyniki z poprzednim tygodniem.

### Co miesiąc

1. Pobierz `complexity-trend.txt` z CI artifacts
2. Porównaj trendy z poprzednim miesiącem
3. Zaktualizuj `docs/architecture-metrics-trends.md`

## Historia zmian

| Data | Zmiana |
|------|--------|
| 2026-08-25 | Wdrożenie Radon + Xenon + wily |
