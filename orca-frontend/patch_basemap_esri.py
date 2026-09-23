import re

with open('app.js', 'r', encoding='utf-8') as f:
    app_js = f.read()

# Replace CartoDB with Esri Dark Gray Canvas
carto_old = r"""    const darkLayer = L\.tileLayer\('https://\{s\}\.basemaps\.cartocdn\.com/dark_all/\{z\}/\{x\}/\{y\}\{r\}\.png', \{\s*attribution: '&copy; <a href="https://www\.openstreetmap\.org/copyright">OSM</a> contributors &copy; <a href="https://carto\.com/attributions">CARTO</a>',\s*subdomains: 'abcd',\s*maxZoom: 19\s*\}\)\.addTo\(map\);"""
carto_new = """    const darkLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
        maxZoom: 16
    }).addTo(map);"""

app_js = re.sub(carto_old, carto_new, app_js)

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(app_js)
