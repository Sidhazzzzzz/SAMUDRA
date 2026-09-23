import re

with open('app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fallback / timeout function
layer_init_old = r"""    const satelliteLayer = L.tileLayer\('https://server\.arcgisonline\.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/\{z\}/\{y\}/\{x\}', \{\s*attribution: 'Tiles &copy; Esri'\s*\}\)\.addTo\(map\);"""

layer_init_new = """    const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri'
    }).addTo(map);

    const darkLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap &copy; CARTO'
    }).addTo(map);

    satelliteLayer.on('add', function() { if (this._container) this._container.style.transition = 'opacity var(--transition-slow) var(--ease-curve)'; });
    darkLayer.on('add', function() { if (this._container) this._container.style.transition = 'opacity var(--transition-slow) var(--ease-curve)'; });

    satelliteLayer.setOpacity(1);
    darkLayer.setOpacity(0);

    document.querySelectorAll('input[name="basemap"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            if (e.target.value === 'satellite') {
                satelliteLayer.setOpacity(1);
                darkLayer.setOpacity(0);
            } else {
                satelliteLayer.setOpacity(0);
                darkLayer.setOpacity(1);
            }
        });
    });

    async function fetchWithTimeout(url, options = {}, timeoutMs = 5000) {
        const controller = new AbortController();
        const id = setTimeout(() => controller.abort(), timeoutMs);
        try {
            const response = await fetch(url, { ...options, signal: controller.signal });
            clearTimeout(id);
            return response;
        } catch (err) {
            clearTimeout(id);
            throw err;
        }
    }

    function markLayerError(toggleId) {
        const label = document.querySelector(`label[for="${toggleId}"]`);
        if (label && !label.querySelector('.layer-error')) {
            label.innerHTML += ' <span class="layer-error" title="Layer unavailable">⚠️ unavailable</span>';
        }
    }"""

content = re.sub(layer_init_old, layer_init_new, content)

# WMS Layer Error handlers
content = content.replace("pane: 'chlPane'\n    }).addTo(map);", "pane: 'chlPane'\n    }).addTo(map);\n    \n    sstLayer.on('tileerror', () => markLayerError('toggle-sst'));\n    chlLayer.on('tileerror', () => markLayerError('toggle-chl'));")


# EEZ Fetch
eez_old = r"fetch\('https://incois\.gov\.in/geoserver/PFZ_EEZ/wfs\?SERVICE=WFS&VERSION=1\.1\.0&REQUEST=GetFeature&TYPENAME=PFZ_EEZ:indiaeez&outputFormat=application/json'\)"
eez_new = "fetchWithTimeout('https://incois.gov.in/geoserver/PFZ_EEZ/wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&TYPENAME=PFZ_EEZ:indiaeez&outputFormat=application/json')"
content = re.sub(eez_old, eez_new, content)

content = re.sub(r"\}\)\.addTo\(eezGroup\);\n\s*\}\)\.catch\(err => console\.error\(err\)\);", 
                 "}).addTo(eezGroup);\n        }).catch(err => {\n            console.error(err);\n            markLayerError('toggle-eez');\n        });", content)

# Sectors Fetch
sec_old = r"fetch\('https://incois\.gov\.in/geoserver/PFZ_Sectors/wfs\?SERVICE=WFS&VERSION=1\.1\.0&REQUEST=GetFeature&TYPENAME=PFZ_Sectors:sector_new&outputFormat=application/json'\)"
sec_new = "fetchWithTimeout('https://incois.gov.in/geoserver/PFZ_Sectors/wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&TYPENAME=PFZ_Sectors:sector_new&outputFormat=application/json')"
content = re.sub(sec_old, sec_new, content)

content = re.sub(r"\}\)\.addTo\(sectorsGroup\);\n\s*\}\)\.catch\(err => console\.error\(err\)\);", 
                 "}).addTo(sectorsGroup);\n        }).catch(err => {\n            console.error(err);\n            markLayerError('toggle-sectors');\n        });", content)


with open('app.js', 'w', encoding='utf-8') as f:
    f.write(content)
