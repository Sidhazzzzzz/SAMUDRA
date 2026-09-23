import re

# 1. Patch app.js
with open('app.js', 'r', encoding='utf-8') as f:
    app_js = f.read()

osm_old = r"""    const darkLayer = L\.tileLayer\('https://\{s\}\.tile\.openstreetmap\.org/\{z\}/\{x\}/\{y\}\.png', \{\s*attribution: '&copy; OpenStreetMap contributors',\s*className: 'osm-dark-filter',\s*maxZoom: 19\s*\}\)\.addTo\(map\);"""
esri_new = """    const darkLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
        maxNativeZoom: 16,
        maxZoom: 19
    }).addTo(map);"""

app_js = re.sub(osm_old, esri_new, app_js)

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(app_js)

