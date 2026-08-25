# Architecture Metrics Policy

## Cel

Utrzymywanie niskiej złożoności i wysokiej utrzymywalności kodu poprzez ciągłe pomiary i enforcement architektonicznych metryk.

## Architecture Governance Model

                         ARCHITECTURE GOVERNANCE
                                  │
           ┌────────────────────┼────────────────────┐
           │                    │                    │
           ▼                    ▼                    ▼
       ENFORCEMENT          DISCOVERY             QUALITY
           │                    │                    │
           ▼                    ▼                    ▼
    Import Linter             pydeps               Radon
                              pyreverse              Xenon
                              Graphviz                wily
           │                    │                    │
           ▼                    ▼                    ▼
      architectural         actual structure      complexity
         rules                                      trends
           │                    │                    │
           └────────────────────┼────────────────────┘
                                ▼
                        Architecture Evidence
                                │
                                ▼
                  Architecture Documentation & Visualization
                                │
                                ▼
                         Designed Architecture
                         (C4 / PlantUML / Structurizr)

### Grupy i ich pytania

| Grupa | Pytanie | Narzędzia |
|-------|---------|-----------|
| 1. Architecture Enforcement | Czy architektura przestrzega reguł? | Import Linter |
| 2. Dependency Discovery | Jak rzeczywiście wyglądają zależności? | pydeps, pyreverse, Graphviz |
| 3. Architecture Quality / Metrics | Jak złożona i podatna na degradację jest architektura? | Radon, Xenon, wily |
| 4. Architecture Documentation / Visualization | Jak architekturę zrozumieć i zakomunikować? | C4, PlantUML, Structurizr, Sphinx/pdoc |

### Rozróżnienie: Designed vs Generated

| Typ | Odpowiada na pytanie | Narzędzia | Przykład |
|-----|---------------------|-----------|---------|
| **Designed Architecture** | Jak system powinien być zorganizowany? | C4, PlantUML, Structurizr | `docs/architecture/context.puml` |
| **Generated Architecture** | Jak kod faktycznie wygląda? | pydeps, pyreverse, Graphviz | `docs/architecture/dependencies-pydeps.svg` |

Porównywanie tych dwóch widoków to sedno Architecture Governance.

## Narzędzia

| Narzędzie | Rola | Grupa |
|-----------|------|-------|
| **Import Linter** | Enforcement | 1. Architecture Enforcement |
| **pydeps** | Dependency visualization | 2. Dependency Discovery |
| **pyreverse** | Class diagrams | 2. Dependency Discovery |
| **Graphviz** | Graph rendering | 2. Dependency Discovery |
| **Radon** | Measurement | 3. Architecture Quality / Metrics |
| **Xenon** | Enforcement | 3. Architecture Quality / Metrics |
| **wily** | Trend Analysis | 3. Architecture Quality / Metrics |
| **PlantUML** | Architecture diagrams | 4. Architecture Documentation / Visualization |
| **Structurizr** | C4 modeling | 4. Architecture Documentation / Visualization |
| **Sphinx/pdoc** | Technical documentation | 4. Architecture Documentation / Visualization |

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

| Parametr | Znaczenie | Uwagi |
|----------|-----------|-------|
| `max-absolute = B` | Żaden plik nie może mieć complexity > B | Operuje na poziomie modułu |
| `max-average = A` | Średnia complexity projektu ≤ A | Operuje na poziomie projektu |
| `max-modules = 10` | Max 10 plików powyżej B | Limit wyjątków |

### Uwaga do semantyki

Radon i Xenon operują na **poziomie modułu** (plik), ale wewnątrz modułu liczą complexity **funkcji/metod**. Dlatego:

- "plik ma complexity B" — to **uproszczenie** mówiące o średniej/module
- "metoda X ma complexity D" — to **dokładna** informacja z Radon CC

W dokumentacji i komunikacji zawsze rozróżniaj te poziomy.

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

### No Regression Policy

Nowy lub zmieniany kod nie może pogarszać baseline'u bez uzasadnienia.

- Jeśli existing function ma complexity C, zmiana nie może zwiększyć jej do D bez aprobaty
- Jeśli existing moduł ma MI B, zmiana nie może zmniejszyć go do C bez aprobaty
- Aprobata wymaga dokumentacji w PR description

## Wyjątki

Wyjątki muszą być **semantyczne**, nie techniczne. Każdy wyjątek wymaga uzasadnienia biznesowego/architektonicznego.

### Skrypty narzędziowe

**Plik:** `scripts/audit_contracts.py`

**Uzasadnienie:** Narzędzie statycznej analizy, którego zwiększona complexity wynika z liczby obsługiwanych reguł i wzorców AST. Nie stanowi części runtime application architecture.

**Dopuszczalne wartości:**
- MI ≤ C
- Complexity ≤ C

### Widoki Django

**Pliki:** `apps/*/views.py`

**Uzasadnienie:** Delivery layer obsługuje HTTP request lifecycle, który naturalnie obejmuje authentication, permissions, validation, use case invocation i response serialization. Większa liczba rozgałęzień jest oczekiwana.

**Dopuszczalne wartości:**
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

### Krok 3: Architecture diagrams

Uruchamiane w CI przy każdym push do `main`:

```yaml
- name: Generowanie diagramów architektury (pydeps + pyreverse)
  run: make graph-modules graph-classes
```

**Artifacts:**
- `docs/architecture/dependencies-pydeps.svg`
- `docs/architecture/classes-*.png`

### Kolejność w CI

```
security-audit
    ↓
audit contracts
    ↓
complexity-check
    ↓
complexity-trend
    ↓
architecture diagrams
```

Semantyka:
1. SECURITY
2. ARCHITECTURE
3. QUALITY
4. OBSERVABILITY
5. DOCUMENTATION

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

### Interpretacja trendów

| Wzorzec | Znaczenie | Akcja |
|---------|-----------|-------|
| `domain` CC rośnie | Logika biznesowa staje się bardziej skomplikowana | Rozważ refactoring domain services |
| `application` CC rośnie | Use cases stają się bardziej skomplikowane | Sprawdź czy nie przekraczają C |
| `infrastructure` CC rośnie | Adaptery/repozytoria stają się bardziej skomplikowane | Sprawdź czy nie przekraczają C |
| `apps` CC rośnie | Delivery layer staje się bardziej skomplikowany | Sprawdź czy nie przekraczają C |
| `scripts` CC rośnie | Narzędzia stają się bardziej skomplikowane | Akceptowalne do C |

## Plan migracji wily

### Obecny stan: filesystem archiver

```makefile
complexity-trend:
	uv run wily build $(PY_DIRS) -n 20 -a filesystem
```

Używamy `filesystem` archivera, ponieważ repository może być nieczyste. To rozwiązanie developmentowe / przejściowe.

### Docelowy stan: git archiver

```makefile
complexity-trend:
	uv run wily build $(PY_DIRS) -n 20
```

Wymagania:
1. CI checkout musi mieć pełną historię (nie shallow)
2. Repozytorium musi być w czystym stanie przed build
3. `wily` buduje historię z ostatnich N commitów

### Kryteria przejścia

- CI jest stabilne przez co najmniej 4 tygodnie
- Wszyscy developezy znają model Architecture Governance
- `make complexity-trend` działa bezbłędnie przez 4 tygodnie

## Architecture Documentation

Szczegóły dotyczące dokumentacji i wizualizacji architektury znajdują się w:

- **`docs/architecture-documentation.md`** — polityka dokumentacji architektury
- **`docs/architecture-metrics-baseline.md`** — baseline metryk
- **`docs/architecture-metrics-trends.md`** — trendy miesięczne

## Historia zmian

| Data | Zmiana |
|------|--------|
| 2026-08-25 | Wdrożenie Radon + Xenon + wily |
| 2026-08-25 | Dodano politykę no regression i wyjątki semantyczne |
| 2026-08-25 | Dodano plan migracji wily na git archiver |
| 2026-08-25 | Dodano grupę 4: Architecture Documentation & Visualization |
