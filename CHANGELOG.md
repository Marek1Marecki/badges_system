# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **AUDYT-055 / AUDYT-155-159 (Phase 0–3)**: Refaktoryzacja hierarchii regionów
  → jednolita tabela `regions_flat` oparta o `ltree` (ADR-028). Dotyczy:
  - `ObjectRegionCache.region_id` przekształcone z `BigIntegerField` na `ForeignKey` →
    `RegionFlatModel` (referential integrity).
  - `DjangoRegionCacheRepository`, `DjangoRegionGeometryRepository`,
    `DjangoMvtRepository` — refactorizowane na `RegionFlatModel`:
    - `recalculate_all_region_levels`: 6 zapytań po starych modelach → 1 po
      `RegionFlatModel.filter(level__in=...)`.
    - `get_related_regions`/`recalculate_tourist_regions`: M2M z `TouristRegionModel`
      → `RegionFlatModel.neighbors`.
    - `get_tile` (MVT): mapa warstw → filtr `level` w `regions_flat`.
  - Migracje danych ETL: `0004_create_regions_flat_ltree`,
    `0005_migrate_region_neighbors_m2m`, `0006_alter_objectregioncache_region_id_fk`,
    `0007_drop_legacy_regions`.
  - Usunięto 7 historycznych tabel: `odznaki_country`,
    `odznaki_voivodeship`, ..., `odznaki_tourist_region`.
  - Usunięto klasy modeli: `CountryModel`, `VoivodeshipModel`, `ProvinceModel`,
    `SubprovinceModel`, `MacroregionModel`, `MesoregionModel`,
    `TouristRegionModel`, `RegionBaseModel`, `PhysicalRegionMixin`,
    `RegionLevelType` (zastąpiony przez `RegionLevel`).
  - Django Admin: jeden `RegionFlatAdmin` z `list_filter("level")` i
    `filter_horizontal("neighbors")` zastępuje 7 osobnych paneli.
  - `calculate_neighbors.py` / `export_reference_data.py` działają na
    `RegionFlatModel` zamiast 7 starych modeli.

### Removed
- **AUDYT-158**: 7 historycznych tabel regionów
  (`odznaki_country`, `odznaki_voivodeship`, `odznaki_province`,
  `odznaki_subprovince`, `odznaki_macroregion`, `odznaki_mesoregion`,
  `odznaki_tourist_region`) oraz ich modele Django.
- `RegionLevelType` (duplikat `RegionLevel`).

### Migration notes
- Baza danych wymaga migracji do `0007` — migracja ETL `0004` kopiuje dane 1:1
  z zachowaniem PK, `0006` przekształca `region_id` na FK (ETL usunie orphaned),
  `0007` usuwa stare tabele.
- Zarządzane poprzez `scripts/dev-up.sh` / `scripts/release-database.sh`.
