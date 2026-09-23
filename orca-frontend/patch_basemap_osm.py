import re

# 1. Patch app.js
with open('app.js', 'r', encoding='utf-8') as f:
    app_js = f.read()

esri_old = r"""    const darkLayer = L\.tileLayer\('https://server\.arcgisonline\.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/\{z\}/\{y\}/\{x\}', \{\s*attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',\s*maxZoom: 16\s*\}\)\.addTo\(map\);"""
osm_new = """    const darkLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        className: 'osm-dark-filter',
        maxZoom: 19
    }).addTo(map);"""

app_js = re.sub(esri_old, osm_new, app_js)

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(app_js)

# 2. Patch style.css
with open('style.css', 'r', encoding='utf-8') as f:
    css = f.read()

if '.osm-dark-filter' not in css:
    css += "\n\n.osm-dark-filter { filter: invert(100%) hue-rotate(180deg) brightness(95%) contrast(90%); }\n"

with open('style.css', 'w', encoding='utf-8') as f:
    f.write(css)
