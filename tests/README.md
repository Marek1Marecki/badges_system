# Struktura testów

Ten katalog zawiera wszystkie testy automatyczne dla systemu PTTK Badges.  
Podział na foldery opiera się na warstwach architektury heksagonalnej, a nie na sztucznym podziale Unit/Integration.

## Gdzie co znajduje się

| Ścieżka | Rodzaj testów | Opis |
|---------|---------------|------|
| `tests/domain/` | **Jednostkowe** | Reguły biznesowe PTTK (`MinAgeRule`, `TimeLimitRule`, itp.) i encje domenowe. Nie wymagają bazy danych. |
| `tests/application/` | **Jednostkowe** | Use case'y, DTO i porty. Wykorzystują `tests/fakes/` do izolacji od infrastruktury. |
| `tests/fakes/` | **Narzędzia** | In-memory implementacje portów (`FakeBadgeRepository`, `FakeClock`). Współdzielone przez testy jednostkowe. |
| `tests/infrastructure/` | **Jednostkowe + Integracyjne** | Adaptery (GPX, OSM, cache, MVT, region cache). Część testów używa mocków, część wymaga PostGIS. |
| `tests/infrastructure/adapters/persistence/` | **Integracyjne** | Adaptery ORM (`DjangoBadgeRepository`, `DjangoTouristRepository`, itp.) oznaczone `@pytest.mark.integration`. Wymagają działającej bazy PostgreSQL/PostGIS. |
| `tests/apps/` | **Jednostkowe + Integracyjne** | Modele Django, formularze, widoki API, zadania Celery. |
| `tests/e2e/` | **E2E (Playwright)** | Scenariusze end-to-end w przeglądarce. Odrzucone z liczenia coverage. |

## Jak uruchomić

```bash
# Szybkie testy jednostkowe (bez bazy danych) — < 15s
make check

# Pełen zestaw z integracyjnymi (wymaga PostGIS)
make test-all

# Tylko wybrana kategoria
uv run pytest tests/domain/ -v
uv run pytest tests/application/ -v
uv run pytest tests/infrastructure/adapters/persistence/ -v --no-cov -m integration
```

## Zasady nazewnictwa

- Testy integracyjne **muszą** być oznaczone `@pytest.mark.integration` oraz `@pytest.mark.django_db`.
- Nazwy plików testowych zaczynają się od `test_`.
- Nie twórz folderów `tests/unit/` ani `tests/integration/` — organizacja jest per-moduł architektoniczny.
