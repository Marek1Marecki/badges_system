export const state = {
    currentMvtLayer: window.REGION_FILTER_LEVEL ? window.REGION_FILTER_LEVEL.toLowerCase() : 'mesoregion',
    activeRegionIdStr: window.REGION_FILTER_ID ? String(window.REGION_FILTER_ID) : null,
    isManualOverride: window.REGION_FILTER_ID ? true : false,
    isGridHidden: false,
    debounceTimer: null
};

export const colorMapping = [
    'match', ['get', 'peak_color'],
    'RED', '#ef4444',
    'GREEN', '#22c55e',
    'BLUE', '#3b82f6',
    'ORANGE', '#f97316',
    'GRAY', '#9ca3af',
    '#9ca3af' // Fallback
];
