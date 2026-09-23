import re

with open('app.js', 'r', encoding='utf-8') as f:
    app_js = f.read()

esri_old = r"""    const darkLayer = L\.tileLayer\('https://server\.arcgisonline\.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/\{z\}/\{y\}/\{x\}', \{\s*attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',\s*maxNativeZoom: 16,\s*maxZoom: 19\s*\}\)\.addTo\(map\);"""
osm_new = """    const darkLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        className: 'osm-dark-filter',
        maxZoom: 19
    }).addTo(map);"""

app_js = re.sub(esri_old, osm_new, app_js)

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(app_js)
