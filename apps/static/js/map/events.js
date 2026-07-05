import { state } from './config.js';
import { fetchMapObjects } from './api.js';
import { loadMvtLayer } from './layers.js';

export function attachMapEvents(map) {

    // Auto Zoom logic
    const triggerAutoZoom = () => {
        if (state.isManualOverride || state.isGridHidden || state.activeRegionIdStr) return;
        const z = map.getZoom();
        let targetLayer = z < 6.5 ? 'voivodeship' : (z < 8.5 ? 'macroregion' : 'mesoregion');
        if (targetLayer !== state.currentMvtLayer) loadMvtLayer(map, targetLayer);
    };

    if (!state.activeRegionIdStr) {
        map.on('zoomend', triggerAutoZoom);
        map.on('triggerAutoZoom', triggerAutoZoom);
    }

    // Debounce fetching
    map.on('moveend', () => {
        clearTimeout(state.debounceTimer);
        state.debounceTimer = setTimeout(() => { fetchMapObjects(map, map.getBounds()); }, 300);
    });

    // Clicks (Unified)
    map.on('click', (e) => {
        const peaks = map.queryRenderedFeatures(e.point, { layers: ['peaks-symbol'] });
        if (peaks.length > 0) {
            const props = peaks[0].properties;
            const today = new Date().toISOString().split('T')[0];
            const coords = peaks[0].geometry.coordinates.slice();

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
                    <button hx-post="/api/v1/ascents/" hx-ext="json-enc" hx-vals='{"peak_id": ${props.id}, "ascent_date": "${today}"}' hx-swap="none" hx-on::after-request="if(event.detail.successful) location.reload();" class="w-full bg-green-600 hover:bg-green-700 text-white font-medium py-1.5 rounded text-sm transition shadow-sm">
                        ✅ Zaloguj wejście (Dziś)
                    </button>
                </div>
            `;
            new maplibregl.Popup({ closeButton: true, offset: 15 }).setLngLat(coords).setHTML(popupHtml).addTo(map);
            htmx.process(document.body);
            return;
        }

        if (state.isGridHidden) return;

        const regions = map.queryRenderedFeatures(e.point, { layers: ['regions-fill'] });
        if (regions.length > 0) {
            const feature = regions[0];
            const props = feature.properties;
            const rawId = props.db_id_str || props.db_id || props.id || feature.id;
            if (!rawId) return;

            const clickedIdStr = String(rawId);

            if (state.activeRegionIdStr) {
                if (clickedIdStr !== state.activeRegionIdStr) {
                    window.location.href = `/region/${state.currentMvtLayer.toUpperCase()}/${clickedIdStr}/`;
                }
            } else {
                const coords = e.lngLat;
                const displayLayerName = state.currentMvtLayer.charAt(0).toUpperCase() + state.currentMvtLayer.slice(1);
                const regionPopupHtml = `
                    <div class="p-2 min-w-[180px] text-center">
                        <p class="text-xs text-teal-600 uppercase tracking-wide font-bold mb-1">${displayLayerName}</p>
                        <h3 class="font-bold text-slate-800 text-lg mb-3">${props.name || "Nieznany Region"}</h3>
                        <a href="/region/${state.currentMvtLayer.toUpperCase()}/${clickedIdStr}/" class="block w-full bg-teal-600 hover:bg-teal-700 text-white font-bold py-2 rounded-lg text-sm transition shadow-md">
                            🧭 Odkrywaj obiekty
                        </a>
                    </div>
                `;
                new maplibregl.Popup({ closeButton: true }).setLngLat(coords).setHTML(regionPopupHtml).addTo(map);
            }
        }
    });

    map.on('mousemove', (e) => {
        const peaks = map.queryRenderedFeatures(e.point, { layers: ['peaks-symbol'] });
        if (peaks.length > 0) { map.getCanvas().style.cursor = 'pointer'; return; }

        if (!state.isGridHidden) {
            const regions = map.queryRenderedFeatures(e.point, { layers: ['regions-fill'] });
            if (regions.length > 0) {
                const rawId = regions[0].properties.db_id_str || regions[0].properties.db_id || regions[0].properties.id || regions[0].id;
                if (!state.activeRegionIdStr || String(rawId) !== state.activeRegionIdStr) {
                    map.getCanvas().style.cursor = 'pointer';
                    return;
                }
            }
        }
        map.getCanvas().style.cursor = '';
    });
}