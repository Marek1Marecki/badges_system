# Architecture Metrics Baseline

## Data pomiaru

**2026-08-25** — pierwszy pomiar po wdrożeniu Radon, Xenon i wily.

## Ogólne wyniki

| Metryka | Wartość | Status |
|---------|---------|--------|
| Średnia complexity | **B (9.80)** | ✅ W normie |
| Pliki z MI ≤ C | **1** (`scripts/audit_contracts.py`) | ✅ Akceptowalne |
| Xenon | **PASS** | ✅ Żaden plik nie przekracza C |
| Liczba bloków | **99** | — |

## Breakdown per directory (wily)

| Directory | LOC | Cyclomatic Complexity | Maintainability Index |
|-----------|-----|----------------------|----------------------|
| domain | 627 | 12.55 | 92.99 |
| application | 1985 | 8.62 | 89.89 |
| infrastructure | 2224 | 14.20 | 84.42 |
| apps | 5071 | 20.38 | 83.37 |
| bootstrap | 213 | 2.67 | 86.83 |
| scripts | 2021 | 33.42 | 65.37 |

## Hotspots — complexity D

| Plik | Linia | Funkcja/Metoda | Complexity |
|------|-------|----------------|------------|
| `application/services/poi_scoring_service.py` | 52 | `PoiScoringService.recalculate_and_cache_for_profile` | **D** |

## Hotspots — complexity C (kod produkcyjny)

| Plik | Linia | Funkcja/Metoda | Complexity |
|------|-------|----------------|------------|
| `domain/entities/badge_version.py` | 26, 34 | `BadgeVersionDomain`, `evaluate` | C |
| `application/services/explore_queries_service.py` | 30, 105 | `get_poi_ranking`, `get_region_ranking` | C |
| `application/use_cases/verify_badge.py` | 44 | `EvaluateBadgeProgressQuery.execute` | C |
| `application/use_cases/bulk_log_ascents.py` | 38 | `BulkLogAscentsUseCase.execute` | C |
| `infrastructure/adapters/news_scraper.py` | 16, 19 | `BeautifulSoupNewsScraper`, `fetch_news` | C |
| `infrastructure/adapters/osm_adapter.py` | 145, 73 | `OverpassClient.fetch_multiple_objects`, `fetch_object` | C |
| `infrastructure/adapters/osm_repository.py` | 67 | `OsmRepository.update_object_from_osm` | C |
| `apps/tourists/views.py` | 142, 243, 343 | `profile_settings_view`, `badge_detail_view`, `region_detail_view` | C |
| `apps/badges/management/commands/restore_reference_data.py` | 22 | `Command.handle` | C |
| `apps/badges/management/commands/lint_migrations.py` | 92 | `Command.handle` | C |

## Pliki z niskim MI (≤ C)

| Plik | MI | Uwagi |
|------|----|-------|
| `scripts/audit_contracts.py` | C | Skrypt analizujący — naturalnie ma więcej zagnieżdżeń |

## Uwagi

- `apps/` ma najwyższą średnią complexity (20.38) — wynika z wielu widoków Django
- `scripts/` ma najniższy MI (65.37) — oczekiwane dla skryptów narzędziowych
- `bootstrap/` ma najniższą complexity (2.67) — bardzo prosty kod inicjalizacyjny
- `domain/` ma najwyższy MI (92.99) — doskonała utrzymywalność

## Porównanie z progiem Xenon

| Threshold | Wartość | Status |
|-----------|---------|--------|
| max-absolute | B | ✅ Żaden plik nie przekracza C |
| max-average | A | ✅ Średnia = B (9.80) |
| max-modules | 10 | ✅ Tylko 99 bloków, żaden powyżej C |
