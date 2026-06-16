# API Contracts — specyfikacja punktów końcowych (Faza C)

> **Wersja:** 1.3  
> **Data:** 2026-06-02  
> **Właściciel:** Dominik / AI Architect  
> **Zasada Wersjonowania:** Wersjonowanie odbywa się przez prefix URL (np. `/api/v1/`). Zmiany łamiące kompatybilność wsteczną wymagają inkrementacji do `/v2/` i wpisu w ADR.  
> **Zasada dla Agentów LLM:** Zmiana formatu wyjściowego dowolnego z tych endpointów wymaga uprzedniej edycji tego pliku. Wszystkie błędy muszą ściśle przestrzegać standardu z `ERROR_HANDLING.md` (RFC 7807).

---

## 1. Map GeoData (Eksploracja)

### `GET /api/v1/tiles/{layer}/{z}/{x}/{y}.pbf`
Zwraca kafelki wektorowe (MVT) ze statyczną topografią. Obsługuje przechodzenie między regionami (US-C12).
*   **Autoryzacja:** Brak (Publiczny, globalnie zakechowany)
*   **Params:**
    *   `layer`: Nazwa warstwy (np. `tourist_regions`, `countries`, `mesoregions`)
*   **Response (200 OK):** `Content-Type: application/vnd.mapbox-vector-tile`

### `GET /api/v1/map/objects`
Zwraca listę punktów turystycznych (np. szczytów) wewnątrz widocznego okna mapy, wzbogaconą o dynamiczny stan użytkownika (`peak_color`).
*   **Autoryzacja:** Wymagana
*   **Query Params:**
    *   `bbox` (wymagany): `min_lon,min_lat,max_lon,max_lat`
    *   `badge_id` (opcjonalny): Ogranicza widok do konkretnej odznaki (US-C11).
    *   `region_level` & `region_id` (opcjonalny): Filtrowanie terytorialne (US-C12). Odpytuje CQRS (`ObjectRegionCache`).
*   **Response (200 OK) - Format `GeoJSON`:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [19.981, 49.232] },
      "properties": {
        "id": 15, "name": "Kasprowy Wierch", "type": "Szczyt", "peak_color": "RED"
      }
    }
  ]
}
```

### `GET /api/v1/objects/{id}/nearby`
Zwraca listę obiektów w promieniu 2 km od zadanego punktu (US-C14). Używa `ST_DWithin`.
*   **Autoryzacja:** Opcjonalna (Zalogowany user widzi `peak_color`, publiczny nie).
*   **Response (200 OK):** Zwraca format `GeoJSON` z obiektami wokół celu.

---

## 2. Działania Turysty (Logi i Postęp)

### `POST /api/v1/progress/start`
Zapisuje turystę do zdobywania nowej odznaki (lub kolejnego Cyklu), przypinając go do konkretnej, historycznej Wersji Regulaminu.
*   **Autoryzacja:** Wymagana
*   **Payload:** `{"badge_code": "KGP"}`

### `POST /api/v1/ascents`
Rejestruje historyczny log wejścia na szczyt. Obejmuje walidację bitemporalną (T-01).
*   **Autoryzacja:** Wymagana
*   **Content-Type:** `multipart/form-data`
*   **Payload:**
    *   `peak_id` (int, wymóg)
    *   `ascent_date` (date: YYYY-MM-DD, wymóg)
    *   `proof_file` (file: img/jpg, max 5MB, opcjonalnie - US-C04 Pamiątka)

### `GET /api/v1/progress/badges/{version_id}`
Wymusza przeliczenie w locie (On-Demand) stanu turysty i zwraca m.in. `COMPLETED`.

### `POST /api/v1/gpx/analyze`
Analizuje ślad z pliku GPX w locie, zwracając listę szczytów w promieniu 200m od trasy. (US-C17). Brak zapisu do bazy.
*   **Autoryzacja:** Wymagana
*   **Content-Type:** `multipart/form-data`
*   **Payload:** `file` (Plik `.gpx` lub `.xml`)
*   **Response (200 OK):**
```json
{
  "suggested_date": "2026-08-14",
  "nearby_peaks": [
    {"id": 15, "name": "Skrzyczne", "type": "Szczyt", "altitude": 1257, "lon": 19.0, "lat": 49.0}
  ]
}
```

### `POST /api/v1/ascents/bulk`
Masowo rejestruje logi wejścia (np. na podstawie przeanalizowanego pliku GPX). Gwarantuje *Partial Success* – ignoruje logi łamiące bitemporalność (T-01) i duplikaty (D-04).
*   **Autoryzacja:** Wymagana
*   **Content-Type:** `application/json`
*   **Payload (Lista JSON):**
```json
[
  {"peak_id": 15, "ascent_date": "2026-08-14"},
  {"peak_id": 16, "ascent_date": "2026-08-14"}
]
```
*   **Response (200 OK):**
```json
{
  "saved_count": 1,
  "errors": [
    {"peak_id": 16, "reason": "Data wejścia jest z przyszłości."}
  ]
}
```

---

## 3. Logistyka i Tracker (Personal Kanban)

### `PATCH /api/v1/progress/{progress_id}/logistics`
Aktualizuje status logistyczny zdobytej odznaki i powiązane z nim daty.
*   **Autoryzacja:** Wymagana (`owner`)
*   **Payload:** `{"logistic_status": "WAITING_FOR_VERIFICATION", "status_date": "2026-06-02"}`
*   **Dozwolone przejścia:** `WAITING_FOR_SEND` → `WAITING_FOR_VERIFICATION` → `WAITING_FOR_RECEIVING` → `ALBUM`.
*   **Wyjątki:** `409 Conflict` (Próba edycji logistyki, gdy matematyczny status to `IN_PROGRESS`).
