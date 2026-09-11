# ADR-031 — Konwencja Nazewnictwa DTO

> **Status:** `accepted`
> **Data:** 2026-09-04
> **Autor:** Push 8 Refactor / Architecture Team
> **Zastępuje:** —
> **Zastąpiony przez:** —

---

## Kontekst

`application/dto/` zawiera 12 klas DTO z chaotycznymi przyrostkami (`AscentInputDTO`, `AscentDTO`, `LogisticStatusUpdateDTO`). Brakuje jednolitej konwencji, co utrudnia nowym programistom odgadnięcie intencji klasy.

## Decyzja

Wprowadzam **trzy** prefiksy dla DTO w `application/dto/`:

| Suffix         | Zastosowanie                            | Przykład                  |
|----------------|------------------------------------------|---------------------------|
| `RequestDTO`   | Wejścia z API (request body / params)    | `AscentRequestDTO`        |
| `ResponseDTO`  | Wyjścia z Use Case'ów (API response)     | `VerifyBadgeResponseDTO`  |
| `DomainDTO`    | Struktury między Use Case a Repozytorium | `RankedPeakDomainDTO`     |

### Zasady:
1. **Każde nowe DTO musi używać jednego z powyższych suffixów.** — wymuszone przez `tests/architecture/test_dto_naming_convention.py` (`ALLOWED_SUFFIXES`).
2. **`Legacy DTO`** (np. `AscentDTO`, `TouristProfileDTO`) umieszczone są na liście `LEGACY_DTOS` w teście i muszą być przemianowane w kolejnych sprintach.
3. **Nested DTO** (np. `GeoJSONFeatureDTO` zagnieżdżony w `MapExploreResponseDTO`) oznaczone są jako `*ResponseDTO` i wyłączone z wymogu (część modelu wewnętrznego).

## Migration Plan (AUDYT-137)

| Old                        | New                              | Status      |
|----------------------------|----------------------------------|-------------|
| `AscentInputDTO`           | `AscentRequestDTO`               | In Progress |
| `LogisticStatusUpdateDTO`  | `LogisticStatusRequestDTO`       | Open        |
| `TouristProfileDTO`        | `TouristProfileResponseDTO`      | Open        |
| `BadgeProgressDTO`         | `BadgeProgressResponseDTO`       | Open        |
| `AscentDTO`                | `AscentDomainDTO`                | Open        |
| `BulkAscentResultDTO`      | `BulkAscentResponseDTO`          | Open        |
| `GpxAnalysisResultDTO`     | `GpxAnalysisResponseDTO`         | Open        |
| `BadgeCodeNameDTO`         | `BadgeCodeNameResponseDTO`       | Open        |
| `RankingItemDTO`           | `RankingItemResponseDTO`         | Open        |
| `ObjectRegionDTO`          | `ObjectRegionResponseDTO`        | Open        |
| `TouristObjectGeoDTO`      | `TouristObjectGeoResponseDTO`    | Open        |
| `RegionRankingItemDTO`     | `RegionRankingItemResponseDTO`   | Open        |
| `BadgeNewsDTO`             | `BadgeNewsResponseDTO`           | Open        |

## Konsekwencje

- Nowi programiści mogą odgadnąć, czy DTO jest wejściem czy wyjściem po nazwie.
- `jsonschema`/Swagger może generować kontrakty API z górnego poziomu.
- Tech debt: `AscentInputDTO` i inne legacy DTO muszą być przemianowane (tracked w `docs/backlog.md` — AUDYT-137).
