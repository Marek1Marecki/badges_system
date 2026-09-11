# Architecture Index — Indeks Komponentów Architektonicznych

> **Wersja:** 1.0  
> **Cel:** Baza wiedzy dla nowych programistów. Powiązanie decyzji ADR z konkretnymi endpointami API, adapterami infrastrukturalnymi i orkiestratorami.

---

## 1. Warstwa Geograficzna i Kafelki MVT

| Uzasadnienie (ADR) | Kontroler / Endpoint | Orkiestrator (Use Case) | Adapter (Infrastruktura) |
|:---|:---|:---|:---|
| **ADR-013** (MVT & GZIP) | `VectorTileView` (`/tiles/...pbf`) | `GetMvtTileUseCase` | `DjangoMvtRepository` (Raw SQL) |
| **ADR-011** (Hybrydowe BBox) | `MapObjectsView` (`/map/objects/`) | `ExploreMapUseCase` | `DjangoMapRepository` |
| **ADR-005** (CQRS Cache) | `region_detail_view` (`/region/`) | `CalculateObjectRegionsUseCase` | `RegionCacheRepository` |

## 2. Silnik Grywalizacji (Punkty i Kolory)

| Uzasadnienie (ADR) | Kontroler / Zdarzenie | Orkiestrator (Use Case) | Adapter (Infrastruktura) |
|:---|:---|:---|:---|
| **ADR-010** (Priorytety Kolorów) | `MapObjectsView` (GeoJSON) | `ExploreMapUseCase` | Redis (Cache), MapLibre GL JS |
| **ADR-015** (Score 100/n) | Task: `recalculate_poi_scores` | `PoiScoringService` (App Layer) | Redis Cache (TTL) |

## 3. Infrastruktura i Bezpieczeństwo

| Uzasadnienie (Architektura) | Kontroler / Zdarzenie | Orkiestrator (Mechanizm) | Adapter (Infrastruktura) |
|:---|:---|:---|:---|
| **Ochrona danych (Secrets)** | Skrypt: `check_secrets.py` | `.env` Validaton | Wstrzykiwanie z `app_settings.py` |
| **Ochrona Błędów (RFC 7807)** | `RFC7807ErrorMiddleware` | `_handle_application_exception` | Widoki API (`apps/api/views.py`) |
| **Data Stewardship (Seed)** | Skrypt: `export/restore` | Single Source of Truth w Git | Mechanizm `dumpdata`/`loaddata` + Manifest |
