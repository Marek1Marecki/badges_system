import { state, colorMapping } from './config.js';

export function initRasterLayers(map) {
    window.MAP_LAYERS.forEach(layer => {
        if (!layer.locked && layer.id !== 'cartodb_positron') {
            map.addSource(layer.id + '-source', { type: 'raster', tiles: [layer.tiles], tileSize: 256 });
            map.addLayer({
                id: layer.id + '-base', type: 'raster', source: layer.id + '-source',
                layout: { visibility: window.PREFERRED_BASE_MAP === layer.id ? 'visible' : 'none' }
            });
        }
    });
}

export function initGeoJsonLayers(map) {
    map.addSource('peaks', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });

    map.addLayer({
        'id': 'peaks-heat', 'type': 'heatmap', 'source': 'peaks',
        'filter': ['>', ['get', 'potential_score'], 0],
        'paint': {
            'heatmap-weight': ['interpolate', ['linear'], ['get', 'potential_score'], 0, 0, 3, 0.5, 20, 0.8, 100, 1.5, 200, 2.0],
            'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 4, 1.5, 9, 3.5],
            'heatmap-color': ['interpolate', ['linear'], ['heatmap-density'], 0, 'rgba(33,102,172,0)', 0.2, 'rgb(103,169,207)', 0.4, 'rgb(209,229,240)', 0.6, 'rgb(253,219,199)', 0.8, 'rgb(239,138,98)', 1, 'rgb(178,24,43)'],
            'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 4, 12, 9, 30],
            'heatmap-opacity': ['interpolate', ['linear'], ['zoom'], 7, 1, 9, 0]
        }
    });

    map.addLayer({
        'id': 'peaks-symbol', 'type': 'circle', 'source': 'peaks',
        'paint': {
            'circle-radius': ['interpolate', ['linear'], ['zoom'], 5, 3, 10, 7],
            'circle-color': colorMapping,
            'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 7, 0, 9, 2],
            'circle-stroke-color': '#ffffff',
            'circle-opacity': ['interpolate', ['linear'], ['zoom'], 5, 0.5, 9, 1],
            'circle-stroke-opacity': ['interpolate', ['linear'], ['zoom'], 7, 0, 9, 1]
        }
    });
}

export function loadMvtLayer(map, layerName) {
    const layersToRemove = ['regions-fill', 'regions-line-neighbors', 'regions-line-active', 'regions-line-global'];
    layersToRemove.forEach(l => {
        if (map.getLayer(l)) map.removeLayer(l);
    });
    if (map.getSource('region_boundaries')) map.removeSource('region_boundaries');

    if (layerName === 'none') return;

    state.currentMvtLayer = layerName;

    map.addSource('region_boundaries', {
        type: 'vector',
        tiles: [window.location.origin + `/api/v1/tiles/${layerName}/{z}/{x}/{y}.pbf?v=8`],
        minzoom: 4,
        maxzoom: 14
    });

    const activeRegionIdNum = state.activeRegionIdStr ? parseInt(state.activeRegionIdStr) : null;
    const isActiveRegion = ['any', ['==', ['id'], activeRegionIdNum], ['==', ['get', 'db_id_str'], state.activeRegionIdStr]];

    const beforeId = map.getLayer('peaks-heat') ? 'peaks-heat' : (map.getLayer('peaks-symbol') ? 'peaks-symbol' : null);

    map.addLayer({
        'id': 'regions-fill', 'type': 'fill', 'source': 'region_boundaries', 'source-layer': layerName,
        'paint': {
            'fill-color': state.activeRegionIdStr ? ['case', isActiveRegion, '#0ea5e9', '#cbd5e1'] : '#0284c7',
            'fill-opacity': state.activeRegionIdStr ? ['case', isActiveRegion, 0.25, 0.0] : 0.05
        }
    }, beforeId);

    if (state.activeRegionIdStr) {
        map.addLayer({
            'id': 'regions-line-neighbors', 'type': 'line', 'source': 'region_boundaries', 'source-layer': layerName,
            'filter': ['!', isActiveRegion], 'paint': { 'line-color': '#94a3b8', 'line-width': 1, 'line-dasharray': [2, 2] }
        }, beforeId);
        map.addLayer({
            'id': 'regions-line-active', 'type': 'line', 'source': 'region_boundaries', 'source-layer': layerName,
            'filter': isActiveRegion, 'paint': { 'line-color': '#0369a1', 'line-width': 4 }
        }, beforeId);
    } else {
        map.addLayer({
            'id': 'regions-line-global', 'type': 'line', 'source': 'region_boundaries', 'source-layer': layerName,
            'paint': { 'line-color': '#0369a1', 'line-width': 1, 'line-dasharray': [2, 2] }
        }, beforeId);
    }
}