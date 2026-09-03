import { state } from './config.js';
import { initRasterLayers, initGeoJsonLayers, loadMvtLayer } from './layers.js';
import { LayerSwitcherControl, GridSwitcherControl } from './controls.js';
import { attachMapEvents } from './events.js';
import { fetchMapObjects } from './api.js';

document.addEventListener("DOMContentLoaded", function() {

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

    map.addControl(new LayerSwitcherControl(), 'bottom-left');
    map.addControl(new GridSwitcherControl(), 'top-left');

    map.on('error', (e) => {
        console.error('Map error:', e);
        const isRateLimit = [429, 403].includes(e?.eventData?.status) ||
            e?.message?.includes('429') ||
            e?.message?.includes('403');
        if (isRateLimit) {
            const fallbackStyle = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json';
            if (map.getStyle().stylesheet.uri !== fallbackStyle) {
                map.setStyle(fallbackStyle);
            }
        }
    });

    map.on('load', () => {
        initRasterLayers(map);
        initGeoJsonLayers(map);

        if (!state.isGridHidden) {
            loadMvtLayer(map, state.currentMvtLayer);
        }

        attachMapEvents(map);
        fetchMapObjects(map, map.getBounds());
    });
});