"""Konfiguracja dostępnych podkładów mapowych (Raster Base Maps)."""

AVAILABLE_MAP_LAYERS = [
    {
        "id": "osm_standard",
        "name": "OpenStreetMap (Standard)",
        "tiles": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attr": '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        "is_paid": False,
    },
    {
        "id": "opentopomap",
        "name": "OpenTopoMap (Topograficzna)",
        "tiles": "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        "attr": "Map data: &copy; OpenStreetMap contributors, SRTM | Map style: &copy; OpenTopoMap (CC-BY-SA)",
        "is_paid": False,
    },
    {
        "id": "esri_satellite",
        "name": "Esri Satellite (Satelitarna)",
        "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attr": "Tiles &copy; Esri",
        "is_paid": False,
    },
    {
        "id": "esri_topo",
        "name": "Esri Topo (Stonowana)",
        "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
        "attr": "Tiles &copy; Esri",
        "is_paid": False,
    },
    {
        "id": "cartodb_positron",
        "name": "CartoDB Positron (Minimalistyczna)",
        "tiles": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
        "attr": '&copy; OpenStreetMap contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        "is_paid": False,
    },
    {
        "id": "mtb_map",
        "name": "MTB Map (Szlaki Rowerowe)",
        "tiles": "https://tile.mtbmap.cz/mtbmap_tiles/{z}/{x}/{y}.png",
        "attr": '&copy; OpenStreetMap contributors &amp; <a href="https://www.mtbmap.cz">MTBmap.cz</a>',
        "is_paid": False,
    },
    {
        "id": "cyclosm",
        "name": "CyclOSM (Poziomice i Szlaki)",
        "tiles": "https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png",
        "attr": (
            '<a href="https://github.com/cyclosm/cyclosm-cartocss-style/releases" '
            'title="CyclOSM - Open Bicycle render">CyclOSM</a> | '
            "Map data: &copy; OpenStreetMap contributors"
        ),
        "is_paid": False,
    },
    {
        "id": "mapycz_outdoor",
        "name": "Mapy.cz (Turystyczna)",
        "tiles": "https://api.mapy.cz/v1/maptiles/outdoor/256/{z}/{x}/{y}?apikey={api_key}",
        "attr": '<a href="https://api.mapy.cz/copyright" target="_blank">&copy; Seznam.cz a.s. a další</a>',
        "is_paid": True,
    },
]
