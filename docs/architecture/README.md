# Architecture Diagrams

> **Wersja:** 1.1  
> **Data:** 2026-08-15  
> **Właściciel:** Dominik / AI Architect  
> **Zasada:** Wszystkie diagramy są generowane automatycznie z kodu źródłowego. Nie edytuj ich ręcznie.

---

## Semantyka artefaktów: Intended vs Actual

| Artefakt | Źródło | Znaczenie |
|----------|--------|-----------|
| `../dependencies.svg` | `audit_contracts.py` | **Intended Architecture** — zamierzona struktura warstw, kontrakty i reguły architektoniczne |
| `dependencies-pydeps.svg` | `pydeps` | **Actual Architecture** — rzeczywiste zależności modułów/pakietów w kodzie |
| `classes-domain.png` | `pyreverse` | **Actual Architecture** — struktura klas warstwy `domain/` |
| `classes-application.png` | `pyreverse` | **Actual Architecture** — struktura klas warstwy `application/` |
| `classes-infrastructure.png` | `pyreverse` | **Actual Architecture** — struktura klas warstwy `infrastructure/` |
| `classes-apps.png` | `pyreverse` | **Actual Architecture** — struktura klas warstwy `apps/` |

---

## Architecture Governance

Diagramy są generowane automatycznie w CI jako artefakty (`architecture-diagrams`). Każdy build dostarcza snapshot architektury:

```
CI
 │
 ├── tests
 ├── static analysis
 ├── Import Linter
 └── architecture diagrams
        │
        └── architecture-diagrams
```

Porównując snapshopy między buildami można obserwować ewolucję systemu.

---

## Katalog diagramów

| Plik | Narzędzie | Co przedstawia |
|------|-----------|----------------|
| `../dependencies.svg` | `audit_contracts.py` + Graphviz SVG | Intended Architecture — warstwy, cykle, violations |
| `dependencies-pydeps.svg` | `pydeps` | Actual Architecture — rzeczywiste zależności modułów |
| `classes-domain.png` | `pyreverse` | Actual Architecture — struktura klas domeny |
| `classes-application.png` | `pyreverse` | Actual Architecture — struktura klas application |
| `classes-infrastructure.png` | `pyreverse` | Actual Architecture — struktura klas infrastructure |
| `classes-apps.png` | `pyreverse` | Actual Architecture — struktura klas delivery/apps |

---

## Generowanie

```bash
# Wszystkie diagramy
make graph-all

# Tylko zależności modułów (pydeps)
make graph-modules

# Tylko diagramy klas (pyreverse)
make graph-classes

# Tylko audit Contracts + Graphviz DOT/PNG
make graph
```

---

## Weryfikacja

Diagramy są generowane automatycznie w CI jako artefakty (`architecture-diagrams`). Przed każdym merge'em sprawdź:

1. Czy `dependencies.svg` pokazuje oczekiwane kierunki zależności (domain ← application ← infrastructure ← apps)
2. Czy `dependencies-pydeps.svg` nie ujawnia nieoczekiwanych cross-imports względem `dependencies.svg`
3. Czy diagramy klas `classes-*.png` odzwierciedlają aktualny Domain Model

---

## Historia zmian

| Wersja | Data | Autor | Opis zmiany |
|--------|------|-------|-------------|
| 1.1 | 2026-08-15 | Dominik / AI Architect | Dodano semantykę artefaktów: Intended vs Actual Architecture |
| 1.0 | 2026-08-14 | Dominik / AI Architect | Dodanie narzędzi pydeps, pyreverse i Graphviz do procesu architektonicznego |
