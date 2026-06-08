# UI Guidelines — zasady dla agenta frontendowego

> **Wersja:** 1.2  
> **Data:** 2026-06-02  
> **Właściciel:** Dominik / AI Architect
>
> **Zasada naczelna dla agentów LLM:** Warstwa frontendowa jest wyłącznie Delivery Mechanism.  
> Nie zawiera żadnej logiki domenowej. Renderuje to, co backend już przeliczył.  
> Każde odstępstwo od tych zasad wymaga jawnej decyzji i wpisu w ADR.

---

## 1. Stack frontendowy

| Warstwa | Technologia | Wersja | Zakaz zastępowania |
|---------|-------------|--------|-------------------|
| Renderowanie stron | Django Templates (SSR) | — | Tak |
| Dynamika UI | HTMX | `1.9.11` | Tak |
| Mapy (Klient) | MapLibre GL JS | `3.6.2` | Tak |
| Mapy (Admin) | Leaflet (przez `django-leaflet`) | `0.30.x` | Tak — tylko Admin |
| Skrypty | Vanilla JS | — | Zakaz React / Vue / Node.js |

**Zakaz tworzenia komponentów React / Vue.** System nie używa Node.js ani NPM do budowania frontendu.

**Zakaz używania Leafleta poza Django Admin.** Warstwa aplikacji klienckiej (widoki turysty) opiera się wyłącznie na MapLibre GL JS i WebGL.

---

## 2. Technologia Map i Renderowanie (ADR-013)

### Architektura wielowarstwowa

Frontend nakłada trzy niezależne warstwy w MapLibre:

#### Warstwa 0 — Podkład Mapowy (Basemap)
- **Źródło:** Zewnętrzni dostawcy (OSM, Mapy.cz, Turisticka).
- **Zasada:** W UI widnieje kontrolka wyboru warstwy bazowej (Layer Switcher). Aplikacja płynnie podmienia kafelki rastrowe w tle.

#### Warstwa 1 — Statyczna MVT (Regiony)
- **Źródło:** `/api/v1/tiles/{layer}/{z}/{x}/{y}.pbf`
- **Format:** Protocol Buffers (PBF) — `Content-Type: application/vnd.mapbox-vector-tile`
- **Zasada:** Zero parametrów użytkownika. Wyświetla obrysy i granice. W MapLibre należy zdefiniować zdarzenie `click` na obiektach tej warstwy, by po kliknięciu dynamicznie zmienić filtr na odpytanie konkretnego regionu (Nawigacja Regionalna).
- **Zakazane:** Dodawanie atrybutów statusu turysty (`PeakColor`) do warstwy MVT. Kafelki MVT zawierają wyłącznie atrybuty topograficzne (`name`, `altitude`, `region_id`).

#### Warstwa 2 — Dynamiczna GeoJSON (Punkty PTTK)
- **Źródło:** `/api/v1/map/objects?bbox={min_lon},{min_lat},{max_lon},{max_lat}`
- **Format:** GeoJSON
- **Zasada Responsywności (Zooming):**
  - Dla **małego przybliżenia (Zoom < 10)**: Obiekty renderowane są jako mapa ciepła z użyciem warstwy typu `heatmap` w MapLibre.
  - Dla **dużego przybliżenia (Zoom >= 10)**: Obiekty zamieniają się w warstwę `symbol` (klikalne pinezki z kolorami).

### Kontrakt atrybutów GeoJSON (PeakColor)

Backend zwraca dla każdego punktu atrybut `peak_color` zgodnie z hierarchią z ADR-010:

| Wartość `peak_color` | Kolor | Semantyka dla turysty |
|---------------------|-------|----------------------|
| `GRAY` | Szary | Poza kontekstem — nieprzydatny dla żadnej subskrybowanej odznaki |
| `GREEN` | Zielony | Zaliczone — szczyt wliczony do odznaki |
| `ORANGE` | Pomarańczowy | Zablokowane na dziś — zły sezon, niespełnione reguły |
| `BLUE` | Niebieski | Wymaga powtórki — byłeś tu, ale nie wlicza się do nowego cyklu |
| `RED` | Czerwony | Nowy cel — wymagany, dostępny dziś, nigdy tu nie byłeś |

**Zasada:** Frontend stosuje kolory **wyłącznie** na podstawie wartości `peak_color` z backendu. Zakaz interpretowania po stronie JS czy szczyt "powinien" być zielony na podstawie innych atrybutów.

---

## 3. Zasady HTMX

### Zakaz `useEffect` i pobierania danych przez JS

```html
<!-- ❌ ZAKAZANE — JS fetch w skrypcie inline -->
<script>
  fetch('/api/progress').then(r => r.json()).then(data => { ... })
</script>

<!-- ✅ WYMAGANE — HTMX deklaratywnie -->
<div hx-get="/api/progress" hx-trigger="load" hx-target="#progress-bar">
  Ładowanie...
</div>
```

### Dynamika UI przez HTMX

Wszystkie operacje które zmieniają stan UI (dodanie logu wejścia, zmiana statusu wniosku) muszą być obsługiwane przez atrybuty HTMX (`hx-post`, `hx-put`, `hx-delete`), nie przez ręcznie pisane fetch() w JavaScript.

**Wyjątek:** Inicjalizacja mapy MapLibre i obsługa zdarzeń mapowych (przesunięcie, zoom, kliknięcie w pinezkę) — wymagają Vanilla JS w dedykowanym pliku statycznym.

---

## 4. Zasady JavaScript dla mapy

### Hermetyzacja logiki mapy

Logika inicjalizacji mapy musi być zhermetyzowana w **dedykowanym pliku statycznym** (np. `apps/static/js/map.js`). Zakaz pisania rozbudowanego JavaScript wewnątrz plików HTML.

### Obowiązkowy Debounce dla zapytań mapowych

```javascript
// ✅ WYMAGANE — czekamy 300ms po puszczeniu palca/myszy
let debounceTimer;

map.on('moveend', function() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(function() {
        const bounds = map.getBounds();
        fetchMapObjects(bounds);
    }, 300);
});

function fetchMapObjects(bounds) {
    // Kolejność GeoJSON to [Longitude, Latitude] (X, Y)
    // West=min_lon, South=min_lat, East=max_lon, North=max_lat
    const bbox = `${bounds.getWest()},${bounds.getSouth()},${bounds.getEast()},${bounds.getNorth()}`;
    fetch(`/api/v1/map/objects?bbox=${bbox}`)
        .then(r => r.json())
        .then(data => updateMapLayer(data));
}
```

**Zakaz** odpytywania `/api/map-objects` przy każdym zdarzeniu `move` (ciągłe przesuwanie). Wyłącznie `moveend` z Debounce 300ms.

### Narzędzia UI (Popupy)
Kliknięcie w pinezkę w warstwie `symbol` musi generować wbudowany, systemowy popup w MapLibre. Treść popupu musi zawierać przycisk/link do pełnej podstrony `TouristObject`.

---

## 5. Obsługa błędów API po stronie frontendu

Błędy zwracane przez backend są zgodne ze standardem RFC 7807 (zdefiniowanym w `ERROR_HANDLING.md`).

```javascript
// ✅ WYMAGANE — obsługa błędów RFC 7807
fetch('/api/v1/ascents', { method: 'POST', body: formData })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => {
                if (err.status === 422 && err.errors) {
                    // Błędy walidacji — pokaż przy polach formularza
                    displayFieldErrors(err.errors);
                } else {
                    // Pozostałe błędy — toast lub alert z HTMX
                    showErrorToast(err.detail ?? 'Wystąpił błąd');
                }
            });
        }
        return response.json();
    });
```

**Zakaz** wyświetlania surowego `stacktrace` ani pola `type` z błędu RFC 7807 użytkownikowi końcowemu.

---

## 6. Zasady dostępności (a11y)

- Każdy interaktywny element bez widocznego tekstu musi mieć `aria-label`.
- Przyciski akcji na mapie (np. "Dodaj wejście") muszą być dostępne klawiaturowo.
- Kolory `PeakColor` nie mogą być jedynym nośnikiem informacji — każdy kolor musi mieć towarzyszącą ikonę lub etykietę tekstową (dostępność dla osób z daltonizmem).
- Formularz logu wejścia: każde pole musi mieć `<label>` powiązany przez `for`/`id`.

---

## 7. Zasady dla agenta frontendowego

### Zakazane

- Tworzenie komponentów React / Vue — system nie używa Node.js/NPM.
- Używanie Leafleta poza Django Admin.
- Rozbudowany JavaScript wewnątrz plików HTML (Inline JS) — logika mapy w osobnym `.js`.
- Odpytywanie `/api/map/objects` bez Debounce 300ms.
- Nakładanie koloru `PeakColor` na kafelki MVT — tylko na warstwę GeoJSON punktów.
- Interpretowanie atrybutów GeoJSON po stronie frontendu do obliczenia koloru szczytu.
- Obsługa błędów przez `alert()` — zawsze przez dedykowany komponent UI (toast / inline z HTMX).

### Wymagane

- Warstwa MVT (regiony) i warstwa GeoJSON (szczyty) jako dwie osobne warstwy MapLibre.
- Debounce 300ms dla wszystkich zapytań wyzwalanych zdarzeniami mapy.
- Rewalidacja warstwy GeoJSON po każdej akcji turysty zmieniającej stan (np. dodaniu wejścia).
- Obsługa błędów RFC 7807.
- Transformacja koordynatów BBox musi być zgodna z formatem X,Y (`Longitude, Latitude`).

---

## Historia zmian

| Wersja | Data | Autor | Opis zmiany |
|--------|------|-------|-------------|
| 1.0 | 2026-05-31 | Dominik / AI Architect | Pierwsza wersja (Kontrakt BBox, HTMX, a11y, PeakColor). |
| 1.1 | 2026-06-01 | AI Architect | Usunięcie logiki MVT. Pozostawienie uciętego fragmentu. |
| 1.2 | 2026-06-02 | Dominik / AI Architect | Scalenie wersji 1.0 i 1.1. Przywrócenie rygoru z a11y i HTMX, dodanie architektury 3-warstwowej dla MapLibre (Basemap, MVT, GeoJSON) i weryfikacja współrzędnych BBox. |
