export function fetchMapObjects(map, bounds) {
    if (!bounds) return;
    const bbox = `${bounds.getWest()},${bounds.getSouth()},${bounds.getEast()},${bounds.getNorth()}`;

    let url = `/api/v1/map/objects/?bbox=${bbox}`;
    if (window.BADGE_FILTER_CODE) url += `&badge_code=${window.BADGE_FILTER_CODE}`;
    if (window.REGION_FILTER_LEVEL && window.REGION_FILTER_ID) {
        url += `&region_level=${window.REGION_FILTER_LEVEL}&region_id=${window.REGION_FILTER_ID}`;
    }

    fetch(url)
        .then(r => r.ok ? r.json() : null)
        .then(data => {
            if (data && data.type === "FeatureCollection") {
                const source = map.getSource('peaks');
                if (source) source.setData(data);
            }
        })
        .catch(err => console.error("Błąd ładowania punktów mapy:", err));
}

export function updatePreferredBaseMap(selectedId) {
    fetch(`/api/v1/profiles/${window.ACTIVE_PROFILE_ID || ''}/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preferred_base_map: selectedId })
    }).catch(err => console.error("Nie udało się zapisać preferencji:", err));
}