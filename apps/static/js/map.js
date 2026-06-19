document.addEventListener("DOMContentLoaded", function() {

    // Inicjalizacja Mapy
    const map = new maplibregl.Map({
        container: 'map',
        style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
        center: [19.0, 52.0],
        zoom: 5
    });

    if (window.REGION_EXTENT && window.REGION_EXTENT.length === 4) {
        map.fitBounds([
            [window.REGION_EXTENT[0], window.REGION_EXTENT[1]],
            [window.REGION_EXTENT[2], window.REGION_EXTENT[3]]
        ], { padding: 50 });
    }

    map.on('load', () => {
        // --- WARSTWA 1: MVT ---
        const mvtLayerName = window.REGION_FILTER_LEVEL ? window.REGION_FILTER_LEVEL.toLowerCase() : 'mesoregion';
        const activeRegionIdStr = window.REGION_FILTER_ID ? String(window.REGION_FILTER_ID) : null;

        map.addSource('region_boundaries', {
            type: 'vector',
            tiles: [window.location.origin + `/api/v1/tiles/${mvtLayerName}/{z}/{x}/{y}.pbf`],
            minzoom: 4,
            maxzoom: 14
        });

        map.addLayer({
            'id': 'regions-fill',
            'type': 'fill',
            'source': 'region_boundaries',
            'source-layer': mvtLayerName,
            'paint': {
                'fill-color': activeRegionIdStr ? ['case', ['==', ['to-string', ['get', 'id']], activeRegionIdStr], '#0ea5e9', '#cbd5e1'] : '#0284c7',
                'fill-opacity': activeRegionIdStr ? ['case', ['==', ['to-string', ['get', 'id']], activeRegionIdStr], 0.25, 0.05] : 0.05
            }
        });

        if (activeRegionIdStr) {
            map.addLayer({
                'id': 'regions-line-neighbors', 'type': 'line', 'source': 'region_boundaries', 'source-layer': mvtLayerName,
                'filter': ['!=', ['to-string', ['get', 'id']], activeRegionIdStr],
                'paint': { 'line-color': '#94a3b8', 'line-width': 1, 'line-dasharray': [2, 2] }
            });
            map.addLayer({
                'id': 'regions-line-active', 'type': 'line', 'source': 'region_boundaries', 'source-layer': mvtLayerName,
                'filter': ['==', ['to-string', ['get', 'id']], activeRegionIdStr],
                'paint': { 'line-color': '#0369a1', 'line-width': 3 }
            });
        } else {
            map.addLayer({
                'id': 'regions-line-global', 'type': 'line', 'source': 'region_boundaries', 'source-layer': mvtLayerName,
                'paint': { 'line-color': '#0369a1', 'line-width': 1, 'line-dasharray': [2, 2] }
            });
        }

        map.on('click', 'regions-fill', (e) => {
            const props = e.features[0].properties;
            const clickedIdStr = String(props.id);
            if (activeRegionIdStr && clickedIdStr !== activeRegionIdStr) {
                window.location.href = `/region/${mvtLayerName.toUpperCase()}/${clickedIdStr}/`;
            }
        });

        // --- WARSTWA 2: GEOJSON (Szczyty, Kolory, Heatmapa) ---
        map.addSource('peaks', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] }
        });

        const colorMapping = [
            'match', ['get', 'peak_color'],
            'RED', '#ef4444',
            'GREEN', '#22c55e',
            'BLUE', '#3b82f6',
            'ORANGE', '#f97316',
            'GRAY', '#9ca3af',
            '#9ca3af'
        ];

        // HEATMAPA (Tylko dla punktujących celów)
        map.addLayer({
            'id': 'peaks-heat',
            'type': 'heatmap',
            'source': 'peaks',
            'filter': ['>', ['get', 'potential_score'], 0],
            'paint': {
                'heatmap-weight': ['interpolate', ['linear'], ['get', 'potential_score'], 0, 0, 10, 0.2, 50, 0.6, 100, 1.0, 200, 2.0],
                'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 4, 1, 9, 3],
                'heatmap-color': ['interpolate', ['linear'], ['heatmap-density'], 0, 'rgba(33,102,172,0)', 0.2, 'rgb(103,169,207)', 0.4, 'rgb(209,229,240)', 0.6, 'rgb(253,219,199)', 0.8, 'rgb(239,138,98)', 1, 'rgb(178,24,43)'],
                'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 4, 10, 9, 25],
                'heatmap-opacity': ['interpolate', ['linear'], ['zoom'], 8, 1, 10, 0]
            }
        });

        // PINEZKI (Wyłaniają się z heatmapy na zbliżeniu)
        map.addLayer({
            'id': 'peaks-symbol',
            'type': 'circle',
            'source': 'peaks',
            'paint': {
                'circle-radius': ['interpolate', ['linear'], ['zoom'], 5, 2, 10, 7],
                'circle-color': colorMapping,
                'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 7, 0, 9, 2],
                'circle-stroke-color': '#ffffff',
                'circle-opacity': ['interpolate', ['linear'], ['zoom'], 5, 0.4, 9, 1],
                'circle-stroke-opacity': ['interpolate', ['linear'], ['zoom'], 7, 0, 9, 1]
            }
        });

        // INICJALIZACJA
        fetchMapObjects(map.getBounds());
    });

    // --- LOGIKA POBIERANIA (Debounce 300ms) ---
    let debounceTimer;
    map.on('moveend', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            fetchMapObjects(map.getBounds());
        }, 300);
    });

    function fetchMapObjects(bounds) {
        if (!bounds) return;
        const bbox = `${bounds.getWest()},${bounds.getSouth()},${bounds.getEast()},${bounds.getNorth()}`;

        let url = `/api/v1/map/objects/?bbox=${bbox}`;
        if (window.BADGE_FILTER_CODE) url += `&badge_code=${window.BADGE_FILTER_CODE}`;
        if (window.REGION_FILTER_LEVEL && window.REGION_FILTER_ID) url += `&region_level=${window.REGION_FILTER_LEVEL}&region_id=${window.REGION_FILTER_ID}`;

        fetch(url)
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (data && data.type === "FeatureCollection") {
                    map.getSource('peaks').setData(data);
                }
            })
            .catch(err => console.error("Błąd ładowania punktów:", err));
    }

    // --- POPUPY HTMX ---
    map.on('click', 'peaks-symbol', (e) => {
        const coords = e.features[0].geometry.coordinates.slice();
        const props = e.features[0].properties;
        const today = new Date().toISOString().split('T')[0];

        const popupHtml = `
            <div class="p-2 min-w-[200px]">
                <h3 class="font-bold text-gray-900">${props.name}</h3>
                <p class="text-xs text-gray-500 uppercase tracking-wide">${props.type}</p>
                <div class="mt-2 mb-3 bg-gray-50 border p-2 rounded text-xs">
                    <span class="block">Zysk: <b>${props.potential_score} pkt</b></span>
                    <span class="block">Status: <b>${props.peak_color}</b></span>
                </div>
                
                <a href="/object/${props.id}/" class="block text-center mb-2 w-full bg-sky-100 hover:bg-sky-200 text-sky-800 font-bold py-1.5 rounded text-sm transition border border-sky-300">
                    👁️ Zobacz szczegóły
                </a>
                
                <button hx-post="/api/v1/ascents/"
                        hx-ext="json-enc"
                        hx-vals='{"peak_id": ${props.id}, "ascent_date": "${today}"}'
                        hx-swap="none"
                        hx-on::after-request="if(event.detail.successful) location.reload();"
                        class="w-full bg-green-600 hover:bg-green-700 text-white font-medium py-1.5 rounded text-sm transition shadow-sm">
                    ✅ Zaloguj wejście (Dziś)
                </button>
            </div>
        `;

        const popup = new maplibregl.Popup({ closeButton: true, offset: 15 })
            .setLngLat(coords)
            .setHTML(popupHtml)
            .addTo(map);

        htmx.process(popup.getElement());
    });

    map.on('mouseenter', 'peaks-symbol', () => map.getCanvas().style.cursor = 'pointer');
    map.on('mouseleave', 'peaks-symbol', () => map.getCanvas().style.cursor = '');
});