document.addEventListener("DOMContentLoaded", function() {

    // Inicjalizacja Mapy
    const map = new maplibregl.Map({
        container: 'map',
        style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json', // Jasny podkład
        center: [19.0, 52.0], // Środek Polski
        zoom: 5
    });

    map.on('load', () => {
        // ----------------------------------------------------
        // WARSTWA 1: STATYCZNA MVT (Z bazy PostGIS, zakechowana)
        // ----------------------------------------------------
        map.addSource('tourist_regions', {
            type: 'vector',
            // Zwróć uwagę na odpytywanie naszego serwera kafelków o warstwę regionów turystycznych
            tiles: [window.location.origin + '/api/v1/tiles/tourist_region/{z}/{x}/{y}.pbf'],
            minzoom: 5,
            maxzoom: 14
        });

        map.addLayer({
            'id': 'regions-fill',
            'type': 'fill',
            'source': 'tourist_regions',
            'source-layer': 'default', // PostGIS ST_AsMVT nazywa tak domyślnie warstwę
            'paint': {
                'fill-color': '#0284c7',
                'fill-opacity': 0.05
            }
        });

        map.addLayer({
            'id': 'regions-line',
            'type': 'line',
            'source': 'tourist_regions',
            'source-layer': 'default',
            'paint': {
                'line-color': '#0369a1',
                'line-width': 1,
                'line-dasharray': [2, 2]
            }
        });

        // ----------------------------------------------------
        // WARSTWA 2: DYNAMICZNA GEOJSON (Szczyty i Kolory Turysty)
        // ----------------------------------------------------
        map.addSource('peaks', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] } // Na start puste
        });

        // Kontrakt Kolorów (Zgodnie z UI_GUIDELINES.md)
        const colorMapping = [
            'match',
            ['get', 'peak_color'],
            'RED', '#ef4444',     // Nowy cel
            'GREEN', '#22c55e',   // Zaliczone
            'BLUE', '#3b82f6',    // Ponowny Cykl
            'ORANGE', '#f97316',  // Zablokowane na dziś
            'GRAY', '#9ca3af',    // Ignorowane
            '#9ca3af'             // Fallback
        ];

        // Wyświetlanie jako Punkty (Pinezki) dla dużego zoomu
        map.addLayer({
            'id': 'peaks-symbol',
            'type': 'circle',
            'source': 'peaks',
            'paint': {
                'circle-radius': ['interpolate', ['linear'], ['zoom'], 5, 3, 12, 7],
                'circle-color': colorMapping,
                'circle-stroke-width': 2,
                'circle-stroke-color': '#ffffff'
            }
        });

        // Pierwsze pobranie danych
        fetchMapObjects(map.getBounds());
    });

    // ----------------------------------------------------
    // INVARIANT M-02: DEBOUNCE (Ochrona bazy danych przed spamem)
    // ----------------------------------------------------
    let debounceTimer;
    map.on('moveend', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            fetchMapObjects(map.getBounds());
        }, 300);
    });

    function fetchMapObjects(bounds) {
        // [West, South, East, North] -> [min_lon, min_lat, max_lon, max_lat]
        const bbox = `${bounds.getWest()},${bounds.getSouth()},${bounds.getEast()},${bounds.getNorth()}`;

        fetch(`/api/v1/map/objects/?bbox=${bbox}`)
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (data && data.type === "FeatureCollection") {
                    map.getSource('peaks').setData(data);
                }
            })
            .catch(err => console.error("Błąd ładowania mapy:", err));
    }

    // ----------------------------------------------------
    // INTERAKCJA: Popupy z HTMX (Wysyłanie wejść z mapy!)
    // ----------------------------------------------------
    map.on('click', 'peaks-symbol', (e) => {
        const coords = e.features[0].geometry.coordinates.slice();
        const props = e.features[0].properties;
        const today = new Date().toISOString().split('T')[0];

        // Tworzymy popup z magicznym przyciskiem HTMX
        const popupHtml = `
            <div class="p-2 min-w-[200px]">
                <h3 class="font-bold text-gray-900">${props.name}</h3>
                <p class="text-xs text-gray-500 uppercase tracking-wide">${props.type}</p>
                <div class="mt-2 mb-3 bg-gray-50 border p-2 rounded text-xs">
                    <span class="block">Zysk: <b>${props.potential_score} pkt</b></span>
                    <span class="block">Status: <b>${props.peak_color}</b></span>
                </div>
                
                <button hx-post="/api/v1/ascents/"
                        hx-ext="json-enc"
                        hx-vals='{"peak_id": ${props.id}, "ascent_date": "${today}"}'
                        hx-swap="none"
                        class="w-full bg-green-600 hover:bg-green-700 text-white font-medium py-1.5 rounded text-sm transition shadow-sm">
                    ✅ Zaloguj wejście (Dziś)
                </button>
            </div>
        `;

        const popup = new maplibregl.Popup({ closeButton: true, offset: 15 })
            .setLngLat(coords)
            .setHTML(popupHtml)
            .addTo(map);

        // Zmuszamy HTMX do "zauważenia" nowego przycisku wstrzykniętego do DOM
        htmx.process(popup.getElement());
    });

    // Kursor
    map.on('mouseenter', 'peaks-symbol', () => map.getCanvas().style.cursor = 'pointer');
    map.on('mouseleave', 'peaks-symbol', () => map.getCanvas().style.cursor = '');
});