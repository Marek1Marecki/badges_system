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

### Integracja HTMX z zewnętrznymi bibliotekami JS (MapLibre)
Zabrania się używania standardowego `fetch()` w JavaScripcie do wykonywania mutacji stanu (POST, PATCH) z poziomu mapy, jeśli można użyć HTMX. 
Zamiast tego, kontrolki mapy (np. Popupy) powinny być generowane jako ciągi HTML zawierające atrybuty `hx-`. 
**Wymóg:** Po wstrzyknięciu takiego HTML-a do DOM przez zewnętrzną bibliotekę (MapLibre), należy natychmiast wywołać `htmx.process(element);`, aby ożywić wygenerowane przyciski. Zapewnia to spójność obsługi błędów (RFC 7807) zdefiniowanej w globalnych event listenerach HTMX.

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

### Automatyczne kadrowanie mapy (Auto-Zoom / Fly-to)
Wszelkie widoki detali (np. Strona Regionu, Strona Obiektu), które posiadają kontekst przestrzenny, muszą instruować mapę o swoim obszarze brzegowym (Bounding Box).
**Wymóg:** Backend (Django) wstrzykuje współrzędne obrysu jako `window.REGION_EXTENT = [min_lon, min_lat, max_lon, max_lat]`. Skrypt `map.js` na starcie sprawdza istnienie tej zmiennej i wywołuje asynchronicznie `map.fitBounds(..., { padding: 50 })`. Zakazuje się ręcznego "zgadywania" zoomu i środka mapy w kodzie JavaScript dla widoków szczegółowych.

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

## 6. Zasady dostępności (a11y) i Kontrastu (WCAG)

System jest okresowo skanowany narzędziem `Axe-Playwright`. Każdy kod HTML wprowadzany do aplikacji musi bezwzględnie spełniać następujące wymogi:
- **Zasada Minimalnego Kontrastu:** Tło elementu interaktywnego i kolor tekstu muszą posiadać wysoki współczynnik kontrastu. W palecie Tailwind CSS zakazuje się używania kombinacji `bg-*-600` z białym tekstem dla mniejszych elementów. Należy domyślnie podbijać ciężar tła do `bg-*-700 text-white` (np. `bg-sky-700`, `bg-green-700`). Teksty pomocnicze (np. opisy, wyciszone ID) muszą mieć przynajmniej `text-gray-500` lub `text-slate-600` (zakaz używania `text-gray-400` na białym tle).
- **Semantyka Formularzy:** Każde pole wejściowe `<input>` lub `<select>` musi posiadać przypisaną etykietę `<label>`. Przypisanie musi być bezwzględnie, fizycznie powiązane za pomocą atrybutów `for="id_pola"` w labelu oraz `id="id_pola"` w inpucie. 
- **Atrybuty ARIA:** Każdy interaktywny element bez widocznego tekstu (np. ikona krzyżyka zamykającego modal) musi posiadać twardo wpisany atrybut `aria-label="..."`.
- **Nawigacja:** Przyciski akcji na mapie oraz w formularzach HTMX muszą być dostępne klawiaturowo (fokusowalne). Kolory (np. wskaźnik `PeakColor`) nie mogą być jedynym nośnikiem informacji – wymusza się stosowanie ikon lub etykiet tekstowych wspierających daltonistów.

---

## 7. Architektura Informacji i Sieć Nawigacyjna (Hyperlinking)

System PTTK Badges funkcjonuje jako gęsta "Wikipedia Turystyczna". Wymaga to ścisłego przestrzegania zasady spłaszczania nawigacji:
- **Zasada Klikalności Encji:** Każda referencja do bytu domenowego wyświetlana w interfejsie użytkownika (np. nazwa odznaki, nazwa szczytu, nazwa regionu w tabeli lub dymku na mapie) **musi** być klikalnym hiperłączem prowadzącym do strony detali tego obiektu. 
- **Zabezpieczenie przed N+1 w Szablonach:** Aby uniknąć przeciążenia bazy przez ORM przy generowaniu linków, widoki Django przygotowujące dane dla szablonów HTML muszą używać `.select_related()` i `.prefetch_related()`. Jeśli widok przekazuje encję do szablonu, musi ona zostać spakowana jako słownik zawierający odpowiedni atrybut rutingu (np. `code` dla odznak, `id` dla szczytów), a nie spłaszczona do samego tekstu.

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

## 8. Prezentacja Danych Zagnieżdżonych (Klastrowanie Wizualne)

Obiekty turystyczne mogą tworzyć Klastry przestrzenne (Rodzic -> Dzieci, ADR-006). Aplikacja kategorycznie unika "Fałszywych Obietnic" (Fałszywych pozytywów) na mapach, gdzie punkty liczą się osobno. 
Jednakże w widokach tabelarycznych (np. Ranking Celów `poi_ranking_view`), system **musi** stosować wzorzec Grouping (Klastrowanie Wizualne):

1. **Logika Zapytania (SQL):** Widok przygotowujący tabelę dla klastrów musi zawsze pobierać **całą rodzinę** obiektów. Jeśli filtrowanie wyłapuje Dziecko (np. Schronisko ma punkty), zapytanie używając `Q` musi dociągnąć również jego Rodzica, i odwrotnie.
2. **Budowa Paczki w Pythonie:** Zamiast płaskiej listy obiektów, widok wysyła do szablonu zgrupowane słowniki (np. `[{"cluster_id": 1, "cluster_score": 15, "items": [...]}]`).
3. **Renderowanie HTML (UX):**
   - Jeśli obiekt jest singlem (brak klastra), renderuje się jako zwykły wiersz tabeli.
   - Jeśli obiekt jest częścią klastra (`is_family = True`), system generuje wiersz-nagłówek (Klaster) z pogrubioną sumą punktów dla całego gniazda, a pod nim wylistowuje członków z wcięciami (`pl-10`) i znakami podrzędności (`↳`). 
   - Wymaga to odpowiedniego zarządzania `colspan` dla nagłówka klastra, aby suma punktów była idealnie wyrównana z kolumną "Punktacja" wierszy podrzędnych.

---

### 3. Zasady HTMX

### Reużywalność REST API jako serwisu dla HTMX
Wszelkie akcje mutujące stan (jak zmiana statusu w Kanbanie, logowanie wejść, aktualizacja profilu) nie mogą być realizowane przez klasyczne widoki Django zwracające formularze (`FormViews`).
**Wymóg:** Interfejs HTML zasilany HTMX musi działać jak aplikacja Single-Page, tzn. w atrybutach takich jak `hx-patch` lub `hx-post` uderza bezpośrednio w dedykowane punkty końcowe REST API (`/api/v1/...`). Widoki te zwracają JSON. 
HTMX następnie przechwytuje odpowiedź JSON. W przypadku powodzenia następuje ciche odświeżenie strony lub podmiana węzła DOM (np. `hx-on::after-request="if(event.detail.successful) location.reload();"`). W przypadku błędu z API, uruchamiany jest globalny skrypt nasłuchujący na event `htmx:responseError`, który parsuje format RFC 7807 i wyświetla turystyczny komunikat błędu (Toast).

---

### 8. Wzorce Komponentów Interfejsu

### Wzorzec Click-Driven Kanban (Bez Drag & Drop)
Wszelkie tablice typu Kanban (np. Osobista Logistyka Turysty) są projektowane w oparciu o filozofię **Mobile-First**. 
- **Zakazane:** Wdrażanie ciężkich bibliotek do przeciągania i upuszczania elementów (Drag & Drop), które często konfliktują ze scrollowaniem na ekranach dotykowych.
- **Wymagane:** Zastosowanie wzorca **Click-Driven Kanban**. Zmiana stanu karty odbywa się poprzez wbudowane w nią przyciski akcji (np. "Wysłano pocztą ➔", "⬅ Cofnij").
- **Implementacja:** Przycisk korzysta z HTMX (np. `hx-patch="/api/v1/progress/.../logistics/"`) przekazując nowy stan w atrybucie `hx-vals`. Po sukcesie wywoływane jest przeładowanie strony lub węzła DOM (np. `hx-on::after-request="location.reload();"`), co natychmiast "przesuwa" kartę do odpowiedniej kolumny CSS Grid w nowym cyklu renderowania.

---

### 4. Zasady JavaScript dla mapy

### Dynamiczna konfiguracja warstw mapy (Data-Driven Configuration)
Zabrania się "hardkodowania" adresów URL podkładów rastrowych (Base Maps) bezpośrednio w plikach JavaScript (np. w kontrolkach zmiany warstwy).
**Wymóg:** Lista dostępnych podkładów mapowych (wraz z ich ograniczeniami Paywall) jest definiowana jako Słownik Prawdy w backendzie (`infrastructure/config/map_layers.py`). Następnie jest wstrzykiwana do globalnego obiektu JS (`window.MAP_LAYERS`) za pomocą `Context Processor`. Kod frontendowy odpowiada jedynie za iterację po tej liście i generowanie kontrolek UI. Zabezpiecza to klucze API przed wyciekiem do nieuprawnionych klientów.

### Zasada Minimalizmu Interfejsu Mapowego (Map Controls)
Mapa jest najważniejszym elementem eksploracji. Wszystkie widgety nakładane na kanwę MapLibre (np. przełącznik warstw, wybór siatki MVT) podlegają **Zasadzie Zwijania na Hover (Folium/Leaflet Style)**.
**Wymóg:** Kontrolki muszą być domyślnie ukryte pod pojedynczą, małą ikoną w rogu ekranu (np. stosem warstw). Główne menu z wyborami (radia, pastylki) wysuwa się wyłącznie przy zdarzeniu `mouseenter` na obszarze kontrolki i chowa się po zdarzeniu `mouseleave`. Zabrania się przypinania do mapy statycznych, rozwartych paneli zajmujących cenne miejsce (szczególnie w kontekście Mobile-First).

---

### 7. Architektura Informacji i Nawigacja

- **Wizualny Kontekst Subskrypcji (Visual State Context):** Każdy widok w aplikacji renderujący listę odznak powiązanych z jakimkolwiek obiektem lub terytorium (np. na Stronie Obiektu lub w Rankingu Celów) **musi** jawnie odróżniać odznaki aktualnie subskrybowane przez Turystę od odznak, których Turysta nie zdobywa. 
  - **Mechanizm:** Zawsze przekazuj do szablonu zmienną `subscribed_badge_codes`.
  - **Prezentacja (Tailwind):** Odznaka subskrybowana musi być wyróżniona kolorystycznie (np. jasna zieleń `bg-green-100 text-green-800`), fontem (`font-bold`) oraz znacznikem graficznym (np. `✓`), ułatwiając szybkie skanowanie wzrokiem długich tabel danych. Niesubskrybowane odznaki zachowują neutralny, szary odcień.

---