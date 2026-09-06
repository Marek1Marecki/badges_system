## ✅ Checklist przed `git push`

### Testy i Jakość
- [ ] `make check` przechodzi lokalnie (865+ testów, ruff, mypy, audit)
- [ ] Coverage ≥ 80%
- [ ] Nowe testy dodane dla nowej funkcjonalności

### Architektura
- [ ] Nowa encja nie łamie `ADR-002` (PostGIS geometry jako transport, nie VO domena)
- [ ] Importy Cross-App przez porty/adaptery (AUDYT-016) — nie `apps.X.models → apps.Y`
- [ ] Nie ma nowych `ignore_imports` w `import-linter` bez usprawiedliwienia

### Działanie w zespole
- [ ] `CHANGELOG.md` zaktualizowany (jeśli nowa wersja) → tag `git tag -a v<X> -m "Release v<X>"`
- [ ] Commit message według konwencji: `feat|fix|refactor(doc): AUDYT-NN opis`
