document.addEventListener("DOMContentLoaded", function() {

    // Inicjalizacja Mapy (Podkład ładujemy później przez zmienną z Django)
    const map = new maplibregl.Map({
        container: 'map',
        style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
        center: [19.0, 52.0],
        zoom: 5
    });

    // Zmienne śledzące aktualny stan UI mapy
    let currentMvtLayer = window.REGION_FILTER_LEVEL ? window.REGION_FILTER_LEVEL.toLowerCase() : 'voivodeship';
    const activeRegionIdStr = window.REGION_FILTER_ID ? String(window.REGION_FILTER_ID) : null;
    let isManualOverride = false; // Flaga blokująca auto-zoom, gdy user sam wybierze siatkę

    if (window.REGION_EXTENT && window.REGION_EXTENT.length === 4) {
        map.fitBounds([
            [window.REGION_EXTENT[0], window.REGION_EXTENT[1]],
            [window.REGION_EXTENT[2], window.REGION_EXTENT[3]]
        ], { padding: 50 });
    }

    // =====================================================================
    // WIDŻET: DYNAMICZNY PRZEŁĄCZNIK PODKŁADÓW (Z Backendem)
    // =====================================================================
    class LayerSwitcherControl {
        onAdd(map) {
            this._map = map;
            this._container = document.createElement('div');
            this._container.className = 'maplibregl-ctrl maplibregl-ctrl-group bg-white p-3 shadow-md flex flex-col gap-2 rounded-lg border border-gray-200';

            let html = `<span class="text-xs font-black text-sky-900 uppercase tracking-wider mb-1 block border-b border-gray-100 pb-1">Podkład Mapy</span>`;

            window.MAP_LAYERS.forEach(layer => {
                const isChecked = window.PREFERRED_BASE_MAP === layer.id ? "checked" : "";
                const isDisabled = layer.locked ? "disabled" : "";
                const textClass = layer.locked ? "text-gray-400" : "text-gray-800";
                const lockIcon = layer.locked ? " 🔒" : "";

                html += `
                <label class="text-sm flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded font-medium transition ${textClass}">
                    <input type="radio" name="basemap" value="${layer.id}" class="text-sky-600 focus:ring-sky-500" ${isDisabled} ${isChecked}> 
                    ${layer.name}${lockIcon}
                </label>`;
            });

            this._container.innerHTML = html;

            this._container.querySelectorAll('input').forEach(radio => {
                radio.addEventListener('change', (e) => {
                    const selectedId = e.target.value;

                    window.MAP_LAYERS.forEach(l => {
                        if (l.id !== 'cartodb_positron' && this._map.getLayer(l.id + '-base')) {
                            this._map.setLayoutProperty(l.id + '-base', 'visibility', 'none');
                        }
                    });

                    if (selectedId !== 'cartodb_positron' && this._map.getLayer(selectedId + '-base')) {
                        this._map.setLayoutProperty(selectedId + '-base', 'visibility', 'visible');
                    }

                    // PATCH do API - zapis profilu!
                    fetch(`/api/v1/profiles/${window.ACTIVE_PROFILE_ID || ''}/`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ preferred_base_map: selectedId })
                    }).catch(err => console.error("Nie udało się zapisać preferencji:", err));
                });
            });

            this._container.querySelectorAll('label').forEach(label => {
                const input = label.querySelector('input');
                if (input && input.disabled) {
                    label.addEventListener('click', (e) => {
                        if (e.target.tagName !== 'INPUT') {
                            alert("🗺️ Ten podkład to opcja Premium.\nPrzejdź do Ustawień Profilu i zmień swój pakiet na PRO lub FAMILY, aby odblokować poziomice i szlaki!");
                        }
                    });
                }
            });

            return this._container;
        }
        onRemove() {
            this._container.parentNode.removeChild(this._container);
            this._map = undefined;
        }
    }

    map.addControl(new LayerSwitcherControl(), 'bottom-left');

    // --- FUNKCJA ZARZĄDZAJĄCA SIATKĄ REGIONÓW (MVT) ---
    function loadMvtLayer(layerName) {
        if (currentMvtLayer === layerName && map.getSource('region_boundaries')) return;

        currentMvtLayer = layerName;

        const layersToRemove = ['regions-fill', 'regions-line-neighbors', 'regions-line-active', 'regions-line-global'];
        layersToRemove.forEach(l => {
            if (map.getLayer(l)) map.removeLayer(l);
        });
        if (map.getSource('region_boundaries')) map.removeSource('region_boundaries');

        map.addSource('region_boundaries', {
            type: 'vector',
            tiles: [window.location.origin + `/api/v1/tiles/${layerName}/{z}/{x}/{y}.pbf?v=7`],
            minzoom: 4,
            maxzoom: 14
        });

        const activeRegionIdNum = activeRegionIdStr ? parseInt(activeRegionIdStr) : null;
        const isActiveRegion = ['any',
            ['==', ['id'], activeRegionIdNum],
            ['==', ['get', 'db_id_str'], activeRegionIdStr]
        ];

        map.addLayer({
            'id': 'regions-fill',
            'type': 'fill',
            'source': 'region_boundaries',
            'source-layer': layerName,
            'paint': {
                'fill-color': activeRegionIdStr ? ['case', isActiveRegion, '#0ea5e9', '#cbd5e1'] : '#0284c7',
                'fill-opacity': activeRegionIdStr ? ['case', isActiveRegion, 0.25, 0.0] : 0.05
            }
        });

        if (activeRegionIdStr) {
            map.addLayer({
                'id': 'regions-line-neighbors', 'type': 'line', 'source': 'region_boundaries', 'source-layer': layerName,
                'filter': ['!', isActiveRegion],
                'paint': { 'line-color': '#94a3b8', 'line-width': 1, 'line-dasharray': [2, 2] }
            });
            map.addLayer({
                'id': 'regions-line-active', 'type': 'line', 'source': 'region_boundaries', 'source-layer': layerName,
                'filter': isActiveRegion,
                'paint': { 'line-color': '#0369a1', 'line-width': 3 }
            });
        } else {
            map.addLayer({
                'id': 'regions-line-global', 'type': 'line', 'source': 'region_boundaries', 'source-layer': layerName,
                'paint': { 'line-color': '#0369a1', 'line-width': 1, 'line-dasharray': [2, 2] }
            });
        }

        document.querySelectorAll('.grid-btn').forEach(b => {
            if (b.getAttribute('onclick') && b.getAttribute('onclick').includes(layerName)) {
                b.className = "grid-btn px-3 py-1.5 rounded-md bg-sky-600 text-white shadow-sm transition";
            } else {
                b.className = "grid-btn px-3 py-1.5 rounded-md hover:bg-sky-50 text-gray-600 transition";
            }
        });
    }

    window.changeMapGrid = function(layerName, btn) {
        isManualOverride = true;
        loadMvtLayer(layerName);
    };

    map.on('load', () => {
        // --- WARSTWY RASTEROWE Z BACKENDU ---
        window.MAP_LAYERS.forEach(layer => {
            if (!layer.locked && layer.id !== 'cartodb_positron') {
                map.addSource(layer.id + '-source', { type: 'raster', tiles: [layer.tiles], tileSize: 256 });
                map.addLayer({
                    id: layer.id + '-base',
                    type: 'raster',
                    source: layer.id + '-source',
                    layout: { visibility: window.PREFERRED_BASE_MAP === layer.id ? 'visible' : 'none' }
                });
            }
        });

        loadMvtLayer(currentMvtLayer);

        // AUTO-ZOOM DLA GŁÓWNEGO PULPITU
        if (!activeRegionIdStr) {
            map.on('zoomend', () => {
                if (isManualOverride) return;

                const z = map.getZoom();
                let targetLayer = 'mesoregion';

                if (z < 6.5) {
                    targetLayer = 'voivodeship';
                } else if (z < 8.5) {
                    targetLayer = 'macroregion';
                }

                if (targetLayer !== currentMvtLayer) {
                    loadMvtLayer(targetLayer);
                }
            });
        }

        map.on('click', 'regions-fill', (e) => {
            const feature = e.features[0];
            const props = feature.properties;

            const rawId = props.db_id_str || props.db_id || props.id || feature.id;
            if (!rawId) return;

            const clickedIdStr = String(rawId);

            if (activeRegionIdStr) {
                if (clickedIdStr !== activeRegionIdStr) {
                    window.location.href = `/region/${currentMvtLayer.toUpperCase()}/${clickedIdStr}/`;
                }
            } else {
                const coords = e.lngLat;
                const displayLayerName = currentMvtLayer.charAt(0).toUpperCase() + currentMvtLayer.slice(1);

                const regionPopupHtml = `
                    <div class="p-2 min-w-[180px] text-center">
                        <p class="text-xs text-teal-600 uppercase tracking-wide font-bold mb-1">${displayLayerName}</p>
                        <h3 class="font-bold text-slate-800 text-lg mb-3">${props.name || "Nieznany Region"}</h3>
                        <a href="/region/${currentMvtLayer.toUpperCase()}/${clickedIdStr}/" class="block w-full bg-teal-600 hover:bg-teal-700 text-white font-bold py-2 rounded-lg text-sm transition shadow-md">
                            🧭 Odkrywaj obiekty
                        </a>
                    </div>
                `;

                new maplibregl.Popup({ closeButton: true })
                    .setLngLat(coords)
                    .setHTML(regionPopupHtml)
                    .addTo(map);
            }
        });

        map.on('mouseenter', 'regions-fill', () => map.getCanvas().style.cursor = 'pointer');
        map.on('mouseleave', 'regions-fill', () => map.getCanvas().style.cursor = '');


        // ----------------------------------------------------
        // WARSTWA 2: DYNAMICZNA GEOJSON (Szczyty i Kolory)
        // ----------------------------------------------------
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

        fetchMapObjects(map.getBounds());
    });

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
            .catch(err => console.error("Błąd ładowania punktów mapy:", err));
    }

    map.on('click', 'peaks-symbol', (e) => {
        const props = e.features[0].properties;
        const today = new Date().toISOString().split('T')[0];
        const coords = e.features[0].geometry.coordinates.slice();

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

        new maplibregl.Popup({ closeButton: true, offset: 15 })
            .setLngLat(coords)
            .setHTML(popupHtml)
            .addTo(map);

        htmx.process(document.body);
    });

    map.on('mouseenter', 'peaks-symbol', () => map.getCanvas().style.cursor = 'pointer');
    map.on('mouseleave', 'peaks-symbol', () => map.getCanvas().style.cursor = '');
});