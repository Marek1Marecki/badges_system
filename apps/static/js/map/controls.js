import { state } from './config.js';
import { updatePreferredBaseMap } from './api.js';
import { loadMvtLayer } from './layers.js';

export class LayerSwitcherControl {
    onAdd(map) {
        this._map = map;
        this._container = document.createElement('div');
        this._container.className = 'maplibregl-ctrl maplibregl-ctrl-group bg-white shadow-md flex flex-col transition-all relative';

        let radiosHtml = '';
        window.MAP_LAYERS.forEach(layer => {
            const isChecked = window.PREFERRED_BASE_MAP === layer.id ? "checked" : "";
            const isDisabled = layer.locked ? "disabled" : "";
            const textClass = layer.locked ? "text-gray-400" : "text-gray-800";
            const lockIcon = layer.locked ? " 🔒" : "";

            radiosHtml += `
            <label class="text-sm flex items-center gap-2 cursor-pointer hover:bg-gray-100 px-2 py-1.5 rounded font-medium transition ${textClass} whitespace-nowrap m-0">
                <input type="radio" name="basemap" value="${layer.id}" class="text-sky-600 focus:ring-sky-500" ${isDisabled} ${isChecked}> 
                ${layer.name}${lockIcon}
            </label>`;
        });

        const iconSvg = `<svg class="w-5 h-5 text-gray-700" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 2L2 7l10 5 10-5-10-5zm0 7.5l-10-5v2.5l10 5 10-5V9.5l-10 5zm0 5l-10-5v2.5l10 5 10-5V14.5l-10 5z"/></svg>`;

        this._container.innerHTML = `
            <div id="ls-button" class="w-8 h-8 flex items-center justify-center cursor-pointer bg-white rounded-md hover:bg-gray-100">${iconSvg}</div>
            <div id="ls-menu" class="hidden absolute bottom-0 left-full ml-2 bg-white rounded-lg shadow-xl border border-gray-200 flex-col p-2 z-50">
                <span class="text-[10px] font-black text-sky-900 uppercase tracking-wider mb-1 block px-2">Podkład Mapy</span>
                ${radiosHtml}
            </div>
        `;

        const menu = this._container.querySelector('#ls-menu');
        this._container.addEventListener('mouseenter', () => { menu.classList.remove('hidden'); menu.classList.add('flex'); });
        this._container.addEventListener('mouseleave', () => { menu.classList.add('hidden'); menu.classList.remove('flex'); });

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
                updatePreferredBaseMap(selectedId);
            });
        });

        this._container.querySelectorAll('label').forEach(label => {
            const input = label.querySelector('input');
            if (input && input.disabled) {
                label.addEventListener('click', (e) => {
                    if (e.target.tagName !== 'INPUT') alert("🗺️ Opcja Premium. Przejdź do Ustawień Profilu.");
                });
            }
        });
        return this._container;
    }
    onRemove() { this._container.parentNode.removeChild(this._container); this._map = undefined; }
}

export class GridSwitcherControl {
    onAdd(map) {
        this._map = map;
        this._container = document.createElement('div');
        this._container.className = 'maplibregl-ctrl maplibregl-ctrl-group bg-white shadow-md flex flex-col transition-all relative';

        const iconSvg = `<svg class="w-5 h-5 text-gray-700" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"></path></svg>`;

        const isAuto = !state.isManualOverride && !state.isGridHidden ? "checked" : "";
        const isV = state.isManualOverride && state.currentMvtLayer === 'voivodeship' ? "checked" : "";
        const isMa = state.isManualOverride && state.currentMvtLayer === 'macroregion' ? "checked" : "";
        const isMe = state.isManualOverride && state.currentMvtLayer === 'mesoregion' ? "checked" : "";
        const isNone = state.isGridHidden ? "checked" : "";

        this._container.innerHTML = `
            <div class="w-8 h-8 flex items-center justify-center cursor-pointer bg-white rounded-md hover:bg-gray-100">${iconSvg}</div>
            <div id="grid-menu" class="hidden absolute top-0 left-full ml-2 bg-white rounded-lg shadow-xl border border-gray-200 flex-col p-2 z-50 w-40">
                <span class="text-[10px] font-black text-sky-900 uppercase tracking-wider mb-1 block px-2">Siatka PTTK</span>
                <label class="text-sm flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1.5 rounded font-medium text-gray-800 transition">
                    <input type="radio" name="grid_map" value="auto" class="text-sky-600" ${isAuto}> Auto-Zoom
                </label>
                <hr class="my-1 border-gray-100">
                <label class="text-sm flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1.5 rounded font-medium text-gray-800 transition">
                    <input type="radio" name="grid_map" value="voivodeship" class="text-sky-600" ${isV}> Województwa
                </label>
                <label class="text-sm flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1.5 rounded font-medium text-gray-800 transition">
                    <input type="radio" name="grid_map" value="macroregion" class="text-sky-600" ${isMa}> Makroregiony
                </label>
                <label class="text-sm flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1.5 rounded font-medium text-gray-800 transition">
                    <input type="radio" name="grid_map" value="mesoregion" class="text-sky-600" ${isMe}> Mezoregiony
                </label>
                <hr class="my-1 border-gray-100">
                <label class="text-sm flex items-center gap-2 cursor-pointer hover:bg-red-50 p-1.5 rounded font-bold text-red-600 transition">
                    <input type="radio" name="grid_map" value="none" class="text-red-500" ${isNone}> ❌ Ukryj granice
                </label>
            </div>
        `;

        const menu = this._container.querySelector('#grid-menu');
        this._container.addEventListener('mouseenter', () => { menu.classList.remove('hidden'); menu.classList.add('flex'); });
        this._container.addEventListener('mouseleave', () => { menu.classList.add('hidden'); menu.classList.remove('flex'); });

        this._container.querySelectorAll('input').forEach(radio => {
            radio.addEventListener('change', (e) => {
                const val = e.target.value;
                if (val === 'auto') {
                    state.isManualOverride = false; state.isGridHidden = false;
                    this._map.fire('triggerAutoZoom');
                } else if (val === 'none') {
                    state.isManualOverride = true; state.isGridHidden = true; loadMvtLayer(this._map, 'none');
                } else {
                    state.isManualOverride = true; state.isGridHidden = false; loadMvtLayer(this._map, val);
                }
            });
        });

        return this._container;
    }
    onRemove() { this._container.parentNode.removeChild(this._container); this._map = undefined; }
}