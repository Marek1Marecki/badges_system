# Release & Tagging

**Status:** Egzekwowalny  
**Zakres:** Wszystkie repozytoria Git

---

## Semantyczne wersjonowanie (SemVer)

Format: `MAJOR.MINOR.PATCH`

| Typ | Kiedy |
|-----|-------|
| MAJOR | Niekompatybilne zmiany API |
| MINOR | Nowe funkcje, kompatybilne wstecz |
| PATCH | Poprawki błędów i drobne usprawnienia |

---

## Tagowanie w Git

Prefiks `v` jest obowiązkowy:

```bash
git tag -a v1.4.2 -m "Release v1.4.2: krótki opis zmian"
git push origin v1.4.2
```

---

## Zasady

- Releases tworzone wyłącznie z `main`
- Nie tagujemy gałęzi feature/bugfix bez merge do `main`
- Każdy release wymaga przejścia pełnego pipeline CI
- `uv.lock` musi być zsynchronizowany przed release

---

## Procedura release

```bash
git checkout main
git pull origin main
make check
git tag -a v1.4.2 -m "Release v1.4.2"
git push origin v1.4.2
```

---

## Traceability

Każdy release powiązany z:
- Konkretnym commit SHA
- SHA obrazu bazowego (logowany w CI przy każdym buildzie)
- Wersją `uv.lock`

```bash
# SHA commitu powiązanego z tagiem
git show -s --format="%H" v1.4.2

# SHA obrazu Docker
docker inspect <image> --format='{{index .RepoDigests 0}}'
```

---

## Changelog

Każdy release wymaga wpisu w `CHANGELOG.md`:

```markdown
## v1.4.2 — YYYY-MM-DD

### Added
- ...

### Fixed
- ...

### Changed
- ...
```

---

## Hotfix

```bash
git checkout -b hotfix/v1.4.3
# wprowadź poprawkę
make check
git checkout main
git merge hotfix/v1.4.3
git tag -a v1.4.3 -m "Hotfix v1.4.3: opis poprawki"
git push origin main v1.4.3
git branch -d hotfix/v1.4.3
```

---

## Zakazane praktyki

- Tagowanie gałęzi innych niż `main`
- Release bez przejścia pełnego CI pipeline
- Tag bez wpisu w `CHANGELOG.md`
- Modyfikowanie istniejącego tagu (`git tag -f`)
