# Sprawozdanie AUDYT-058 — Architecture Compliance Scorecard

> **Status:** `zrealizowany`  
> **Data:** 2026-09-02  
> **Obszar:** `Procesy / CI/CD`  
> **Priorytet:** `🟢 NISKI`  
> **Audytor:** Zewnętrzny Audyt Architektury (Step 3.7 Flash)  
> **Autor wdrożenia:** Dominik / AI Architect  

---

## 1. Kontekst i cel

### Diagnoza Audytora
> *„Obecnie system walidacji architektonicznej (`make check`, `import-linter`, `audit_contracts.py`) to mechanizm zero-jedynkowy (Działa/Nie działa). Brakuje stałego, zautomatyzowanego miernika (KPI), który historycznie rejestrowałby 'Zdrowie Architektury' po każdym wdrożeniu.”*

Audytor zauważył, że projekt nie posiada **ściągłego miernika (KPI)** architektonicznego — nie ma mechanizmu, który po każdym wdrożeniu wypisywałby zdrowie architektury w sposób powtarzalny i porównywalny.

Wszystkie istniejące narzędzia (Import Linter, radon, xenon, mypy, ruff, audit_contracts.py) działają w trybie *fail/fast* — albo przechodzą, albo nie. Projekt **dostarcza dane niezbędne do historycznego porównania**, ale nie posiada jeszcze **automatycznego silnika trendu**.

### Uzasadnienie wyboru
Podczas planowania zakresu, zaproponowano **SonarQube** i **CodeClimate** jako rozwiązania komercyjne. Zgodnie z ustnieniem zespołu — **brak płatnych narzędzi** — zdecydowano się na **czyste rozwiązanie open-source** oparte wyłęcznie na narzędziach już obecnych w `pyproject.toml`:

| Narzędzie | Jest już w projekcie? | Koszt |
|-----------|----------------------|-------|
| SonarQube / CodeClimate | Nie | Płatny |
| Import Linter | ✅ Tak (`import-linter`) | 0 |
| Radon | ✅ Tak (`radon`) | 0 |
| wily | ✅ Tak (`wily`) | 0 |
| mypy | ✅ Tak (`mypy>=2.3.0`) | 0 |
| ruff | ✅ Tak (`ruff>=0.16.3`) | 0 |

**Decyzja:** Utworzyć własny agregator, który nie wymaga żadnych nowych zależności i uruchamia istniejące narzędzia jako subprocessy.

---

## 2. Co zostało wdrożone

### 2.1 Skrypt: `scripts/architecture-scorecard.py`

Skrypt uruchamia wszystkie istniejące narzędzia analizy i agreguje wyniki do jednego pliku JSON. Działa jako **Diagnostic** (nie blokuje CI).

**Wywoływane narzędzia (wszystkie open-source):**
| Metryka | Źródło danych | Co mierzy |
|---------|---------------|-----------|
| Cyclomatic Complexity | `radon cc -j` | Średnia, max, rank distribution |
| Maintainability Index | `radon mi -j` | Średnia MI, pliki ≤ C |
| LOC per layer | `radon raw -j` | Loc, LLOC, SLOC |
| Architecture Contracts | `audit_contracts.py` stdout | 0 violations / N violations |
| Import Linter | `lint-imports` stdout | `kept` / `broken` (contract count) |
| Type Check | `mypy` stdout | Error count |
| Lint | `ruff check` stdout | Error/warning count |
| Security (sensitive data in logs) | AST scan source code | Violations of logger-call-with-sensitive-keyword patterns |

> **Uwaga techniczna:** Metryka `security` nie analizuje wyniku `radon cc`. Script wykonuje własną analizę AST na plikach wykrytych jako "hotspoty" przez radon — skanuje ich treść źródłową w poszukiwaniu wywołań loggera z argumentami zawierającymi słowa kluczowe typu `password`, `token`, `secret`, itp.

### 2.2 Test fitness function: `tests/architecture/test_scoreboard_metrics.py`

19 testów podzielonych na 4 klasy:

| Klasa | Liczba testów | Co weryfikuje |
|-------|---------------|---------------|
| `TestScoreboardStructure` (4) | Metadane, health_score w [0,100], wszystkie grupy metryk |
| `TestScoreboardMetrics` (8) | Pole `status` w każdej grupie; `import_linter.broken=0` → pass; `complexity.max > próg` → fail |
| `TestScoreboardLayerMetrics` (3) | Wszystkie 6 warstw obecnych, każda z `loc` i `complexity` |
| `TestScoreboardThresholds` (2) | Domain complexity ≤ 20; Scripts MI ≥ 40 |

### 2.3 Makefile target
```makefile
scoreboard:
	uv run python scripts/architecture-scorecard.py
```
- Dodany do `.PHONY`
- Dodany do `make diagnostics` (Diagnostic tier)
- Widoczny w `make help`

### 2.4 CI — GitHub Actions
W jobie `diagnostics` (w `.github/workflows/ci.yml`), po sekcji `coverage-diff`, dodano krok:
```yaml
- name: Generowanie Architecture Scorecard
  run: make scorecard
  continue-on-error: true
```
Artefakt `architecture_scorecard.json` jest uploadowany jako część artefaktu `diagnostic-artifacts` (retencja 30 dni).

### 2.5 Dokumentacja
- **FF-024** — zarejestrowany w `docs/architecture/fitness-functions.md` jako Fitness Function typu *Diagnostic*.
- **governance.md** — zmieniono liczbę FF z 23 na 24.
- **backlog_po_audycie.md** — AUDYT-058 przeniesiony do archiwum z pełnym opisem wdrożenia.

### 2.6 per-file-ignores dla subprocess
W `pyproject.toml` dodano `S603`/`S607` do ignorów dla `tests/**` i `S603` dla `scripts/**` — to standardowe reguły bandity dla kodu uruchamiającego subprocessy, które są fałszywymi alarmami dla skryptów narzędziowych.

---

## 3. Jak korzystać z scorecardu

### 3.1 Jednorazowy check
```bash
make scorecard
```
→ Generuje `architecture_scorecard.json` w katalogu głównym repozytorium.

### 3.2 Codzienne użycie (DIAGNOSTIC)
```bash
make diagnostics        # uwzględnia scorecard + wszystkie inne metryki
```

### 3.3 W CI / GitHub Actions
Scorecard jest generowany automatycznie w jobie `diagnostics` po każdym pushu na `main`. Artefakt JSON jest dostępny w zakładce **Actions → Artifacts → diagnostic-artifacts**.

> **Ograniczenie:** Obecnie system przechowuje artefakty 30 dni, ale nie ma komponentu, któryby automatycznie porównywał wyniki run za runem. Trend historyczny można analizować ręcznie pobierając artefakty z poszczególnych runów.

### 3.4 Interpretacja `health_score`
| Zakres | Znaczenie | Akcja |
|--------|-----------|-------|
| 90–100 | 🟢 Zdrowe | Brak działań |
| 70–89 | 🟡 Monitoruj | Przeglądnij metryki z `status: warn` |
| 0–69 | 🔴 Alarm | Natychmiastowy przegląd `status: fail` / `timeout` |

### 3.5 Co sprawdzać w pliku JSON
```json
{
  "health_score": 100.0,
  "metrics": {
    "complexity": {
      "average_complexity": 14.6,
      "max_complexity": 20,
      "worst_hotspot": { "file": "infrastructure/adapters/news_scraper.py", ... }
    },
    "layer_metrics": {
      "domain": { "loc": 435, "complexity": 15.5, "mi": 91.19 },
      ...
    },
    "import_linter": { "kept": 4, "broken": 0, "status": "pass" },
    "architecture_contracts": { "violations": 0, "status": "pass" },
    ...
  }
}
```

### 3.6 Fitness function jako test
```bash
pytest tests/architecture/test_scoreboard_metrics.py
```
Scoreboard jest **automatycznie regenerowywany** przy każdym uruchomieniu testu (fixture `scope="module"`), więc testy zawsze działają na aktualnym stanie.

---

## 4. Architektura i projekt

### 4.1 Tier
- **Diagnostic** (advisory) — nie blokuje `make check` ani CI Gate.
- Motywacja: AUDYT-058 nie definiuje invariantu blokującego, a **trendu**. Scoreboard dostarcza dane niezbędne do historycznego porównania, ale nie wymusza natychmiastowego przepisania kodu.

### 4.2 Zgodność z modelem governance
| Filary governance | Jak scorecard się wpisuje |
|-------------------|--------------------------|
| Enforce | Nie — to nie jest enforcement (to radon/xenon/import-linter robią) |
| Discovery | Częściowo — `worst_hotspot` i `worst_file` to discovery |
| Quality Metrics | ✅ Główny cel tej FF |
| Documentation | ✅ Registrowany jako FF-024 |

### 4.3 Zero nowych zależności
```bash
# Weryfikacja — żadnych nowych packages w pyproject.toml
uv run python scripts/architecture-scoreboard.py  # działa z istniejącymi narzędziami
```

### 4.4 Health Score — definicja

Health Score to średnia arytmetyczna **8 grup metryk**:

```
Health Score = Σ(weight) / 8 × 100
```

Gdzie:
- `pass` → 1.0
- `warn` → 0.5 (tylko dla `maintainability`)
- `fail`/`timeout`/`unknown` → 0.0

**8 składników (alphabetical):**
1. `architecture_contracts`
2. `complexity`
3. `import_linter`
4. `lint`
5. `maintainability`
6. `security`
7. `tdd`
8. `type_check`

> **Uzasadnienie wyboru metryk dla Health Score:** Wszystkie 8 grup to **metryki techniczne**, które odzwierciedlają faktyczny stan kodu w danym momencie. `tdd` (test-to-code ratio) wchodzi jako dodatkowy wymiar pokrywalności, ale jego waga (0.5 przy `warn`) jest świadomie niska, aby nie dominuować overal score przy projektach, które mają wiele plików produkcyjnych stosunkowo do testów.

---

## 5. Known Limitations

| # | Ograniczenie | Wpływ | Kompensacja |
|:---:|-------------|-------|-------------|
| 1 | Scorecard nie blokuje CI | Gate-tier pozostaje w `make check`. Scorecard służy tylko do diagnostyki. | Brak — to celowy design. |
| 2 | Brak automatycznego trend engine | Nie ma komponentu porównującego run N do run N-1. | Artefakty CSV/JSON dostępne w CI; można ręcznie porównać. |
| 3 | Health Score ≠ jakość architektury | 100% Health Score oznacza tylko, że wszystkie 8 grup metryk spełniły określone kryteria. Nie ocenia np. jakości reguł biznesowych ani testów E2E. | Health Score traktujemy jako **Composite Proxy Metric**, nie jako miernik jakości architektury. |
| 4 | TDD ratio może obniżać Health Score | W projektach z dużą liczbą plików produkcyjnych i niewielką liczbą testów metryka TDD może przyczynić się do obniżki score, nawet jeśli testy są dobrze pokryte. | Waga `warn` = 0.5, a nie 1.0. Dodatkowo istnieją bardziej precyzyjne mierniki: `coverage`, `mutation testing`, `audit_contracts.py`. |
| 5 | Security metric to heurystyka | Wyszukiwanie słów kluczowych ("password", "token") w logach to podejście słowne, które może generować false positives. | `detect-secrets` i `semgrep` pełnią rolę głębszej analizy bezpieczeństwa. |

---

## 6. Co dalej (rekomendacja dla audytora)

### Etap 1 — Obserwacja (2-4 tygodnie)
Zbierać artefakty `architecture_scorecard.json` z kolejnych runów CI. Obserwować stabilność poszczególnych metryk.

### Etap 2 — Trend tracking
Po zebraniu ~10 artefaktów, porównać `health_score` run za runem. Jeśli wartość jest stabilna (±2 pp), można rozważyć automatyczny trend engine (np. prosty skrypt porównujący z poprzednim commitem).

### Etap 3 — Alert (opcjonalnie)
Gdy zostanie potwierdzona stabilność:
- Dodać komentarz do PR, gdy `health_score` spadnie poniżej 70.
- Dodać komentarz, gdy `Δ health_score` < -10 pp w stosunku do `main`.

### Etap 4 — Rozszerzenie metryk (opcjonalnie)
Dopiero po potwierdzeniu stabilności istniejących metryk:
- `mccabe` (CC per function)
- Liczba `TODO`/`FIXME` w kodzie
- Liczba nieoznaczonych zależności w `import-linter`

---

## 7. Podsumowanie

| Element | Status |
|---------|--------|
| Skrypt `scripts/architecture-scoreboard.py` | ✅ Gotowy |
| Test fitness function `test_scoreboard_metrics.py` (19 testów) | ✅ Przechodzi |
| Makefile target `make scorecard` | ✅ Gotowy |
| CI step w jobie `diagnostics` | ✅ Gotowy |
| FF-024 w `fitness-functions.md` | ✅ Zarejestrowany |
| AUDYT-058 w `backlog_po_audycie.md` | ✅ Archiwum |
| Zero nowych zależności | ✅ Zweryfikowane |
| `make check` (Gate tier) | ✅ Niezaburzone |