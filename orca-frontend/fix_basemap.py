import re

with open('app.js', 'r', encoding='utf-8') as f:
    content = f.read()

basemap_old = r"    L\.tileLayer\('https://server\.arcgisonline\.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/\{z\}/\{y\}/\{x\}', \{\s*maxZoom: 19\s*\}\)\.addTo\(map\);"

basemap_new = """    const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19
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

content = re.sub(basemap_old, basemap_new, content)

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(content)
