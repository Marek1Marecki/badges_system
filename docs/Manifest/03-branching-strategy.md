# Branching Strategy

**Status:** Egzekwowalny  
**Zakres:** Wszystkie repozytoria Git

---

## Filozofia

Trunk-based development — minimalna złożoność, maksymalna widoczność zmian. Brak długożyjących gałęzi `develop` i `release/*`. Wszystkie zmiany integrują się z `main` przez krótkotrwałe gałęzie robocze.

---

## Struktura gałęzi

| Gałąź | Cel | Pochodzi z | Merge do |
|-------|-----|-----------|----------|
| `main` | Stabilna, produkcyjna wersja | — | — |
| `feature/<opis>` | Nowa funkcjonalność | `main` | `main` |
| `bugfix/<opis>` | Poprawka funkcjonalności | `main` | `main` |
| `hotfix/<opis>` | Krytyczna poprawka produkcyjna | `main` | `main` |

### Nazewnictwo

Małe litery, myślniki jako separator: `feature/add-login`, `bugfix/fix-auth-token`. Krótki i opisowy opis. Brak `develop`, brak `release/*`.

---

## Workflow

```bash
# 1. Tworzenie gałęzi
git checkout main
git pull origin main
git checkout -b feature/<opis>

# 2. Praca lokalna + commitowanie
# Każdy commit powiązany z taskiem: TASK-<id>: opis

# 3. Push
git push -u origin feature/<opis>

# 4. Pull Request → CI → merge do main

# 5. Tagowanie jeśli release
git tag -a v1.4.2 -m "Release v1.4.2"
git push origin v1.4.2

# 6. Usunięcie gałęzi po merge
git branch -d feature/<opis>
git push origin --delete feature/<opis>
```

---

## Zasady egzekwowania

1. Merge do `main` wyłącznie przez PR z przejętym pipeline CI
2. CI weryfikuje: `make check`, coverage, secrets-check, integralność kontenera
3. Gałęzie krótkotrwałe — usuwane po merge
4. Zakaz force-push na `main`
5. Brak automatycznych merge bez PR

---

## Wyjątki

`git commit --no-verify` dopuszczalne wyłącznie świadomie, w sytuacji awaryjnej. Hotfix może być mergowany natychmiast przy krytycznej luce bezpieczeństwa bez pełnego review. Każde obejście wymaga wpisu w `CHANGELOG.md`.

---

## Powiązanie z innymi kontraktami

| Kontrakt | Rola |
|----------|------|
| Makefile Contract | `make check` przed merge obowiązkowe |
| CI/CD Enforcement | PR i pipeline egzekwują standardy |
| Release & Tagging | Releasy produkcyjne muszą być tagowane |
| Dependency Governance | `uv lock --check` w pipeline przed merge |
