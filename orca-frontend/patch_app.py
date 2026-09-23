import re

with open('app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fallback & Tile Layers
layer_init_old = """    const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri'
    }).addTo(map);"""

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

content = content.replace(layer_init_old, layer_init_new)

# WMS Layer Error handlers
wms_old = """    const chlLayer = L.tileLayer.wms('https://incois.gov.in/geoserver/PFZ-TUNA-SST-CHL/wms', {
        layers: 'PFZ-TUNA-SST-CHL:chl',
        format: 'image/png',
        transparent: true,
        pane: 'chlPane'
    }).addTo(map);"""

wms_new = """    const chlLayer = L.tileLayer.wms('https://incois.gov.in/geoserver/PFZ-TUNA-SST-CHL/wms', {
        layers: 'PFZ-TUNA-SST-CHL:chl',
        format: 'image/png',
        transparent: true,
        pane: 'chlPane'
    }).addTo(map);
    
    sstLayer.on('tileerror', () => markLayerError('toggle-sst'));
    chlLayer.on('tileerror', () => markLayerError('toggle-chl'));"""

content = content.replace(wms_old, wms_new)

# EEZ Fetch
eez_old = """    fetch('https://incois.gov.in/geoserver/PFZ_EEZ/wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&TYPENAME=PFZ_EEZ:indiaeez&outputFormat=application/json')
        .then(res => res.json())
        .then(data => {
            L.geoJSON(data, {
                style: {
                    color: '#FF5A5F',
                    weight: 2,
                    dashArray: '5, 5',
                    fillOpacity: 0
                }
            }).addTo(eezGroup);
        }).catch(err => console.error(err));"""

eez_new = """    fetchWithTimeout('https://incois.gov.in/geoserver/PFZ_EEZ/wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&TYPENAME=PFZ_EEZ:indiaeez&outputFormat=application/json')
        .then(res => res.json())
        .then(data => {
            L.geoJSON(data, {
                style: {
                    color: '#FF5A5F',
                    weight: 2,
                    dashArray: '5, 5',
                    fillOpacity: 0
                }
            }).addTo(eezGroup);
        }).catch(err => {
            console.error(err);
            markLayerError('toggle-eez');
        });"""

content = content.replace(eez_old, eez_new)

# Sectors Fetch
sectors_old = """    fetch('https://incois.gov.in/geoserver/PFZ_Sectors/wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&TYPENAME=PFZ_Sectors:sector_new&outputFormat=application/json')
        .then(res => res.json())
        .then(data => {
            L.geoJSON(data, {
                style: {
                    color: '#8F9BB3',
                    weight: 1,
                    fillOpacity: 0.1
                },
                onEachFeature: function (feature, layer) {
                    if (feature.properties && feature.properties.SECTORNAME) {
                        layer.bindPopup("Sector: " + feature.properties.SECTORNAME);
                    }
                }
            }).addTo(sectorsGroup);
        }).catch(err => console.error(err));"""

sectors_new = """    fetchWithTimeout('https://incois.gov.in/geoserver/PFZ_Sectors/wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&TYPENAME=PFZ_Sectors:sector_new&outputFormat=application/json')
        .then(res => res.json())
        .then(data => {
            L.geoJSON(data, {
                style: {
                    color: '#8F9BB3',
                    weight: 1,
                    fillOpacity: 0.1
                },
                onEachFeature: function (feature, layer) {
                    if (feature.properties && feature.properties.SECTORNAME) {
                        layer.bindPopup("Sector: " + feature.properties.SECTORNAME);
                    }
                }
            }).addTo(sectorsGroup);
        }).catch(err => {
            console.error(err);
            markLayerError('toggle-sectors');
        });"""

content = content.replace(sectors_old, sectors_new)

# Persona Transition
persona_old = """            if (currentMode === 'commercial') {
                personaTitle.textContent = 'COMMERCIAL NAVIGATOR';
                chatInput.placeholder = "Enter origin and destination ports...";
            } else {
                personaTitle.textContent = 'FISHERMAN PORTAL';
                chatInput.placeholder = "Enter coordinates, mission, or ask for a route...";
            }"""

persona_new = """        const headerTitle = document.querySelector('.sidebar-header h1');
        headerTitle.classList.add('persona-switching');
        chatInput.classList.add('persona-switching');
        
        setTimeout(() => {
            if (currentMode === 'commercial') {
                personaTitle.textContent = 'COMMERCIAL NAVIGATOR';
                chatInput.placeholder = "Enter origin and destination ports...";
            } else {
                personaTitle.textContent = 'FISHERMAN PORTAL';
                chatInput.placeholder = "Enter coordinates, mission, or ask for a route...";
            }
            headerTitle.classList.remove('persona-switching');
            chatInput.classList.remove('persona-switching');
        }, 300);"""

content = content.replace(persona_old, persona_new)

# Trace Panel Animation
trace_old = """            li.appendChild(header);
            li.appendChild(summaryDiv);
            traceList.appendChild(li);
        });
    }"""

trace_new = """            li.appendChild(header);
            li.appendChild(summaryDiv);
            traceList.appendChild(li);
            
            setTimeout(() => {
                li.classList.add('visible');
            }, 100 + (index * 200));
        });
    }"""

content = content.replace(trace_old, trace_new)

# Metrics updating
metrics_logic = """    function updateMetricsPanel(data) {
        const strip = document.getElementById('metrics-strip');
        if (!data.optimized_route || data.optimized_route.length === 0) {
            strip.classList.add('hidden');
            return;
        }
        strip.classList.remove('hidden');

        let hmiScore = 100;
        let hmiColor = "var(--status-safe)";
        const verdict = (data.verdict && data.verdict.verdict) ? data.verdict.verdict.toUpperCase() : 'UNKNOWN';
        if (verdict === 'CAUTION') { hmiScore = 50; hmiColor = "var(--status-caution)"; }
        else if (verdict === 'NO-GO' || verdict === 'NOGO' || data.status === 'DISTRESS_DETECTED') { hmiScore = 5; hmiColor = "var(--status-nogo)"; }
        
        document.getElementById('hmi-val').textContent = hmiScore;
        document.getElementById('hmi-val').style.color = hmiColor;
        const hmiArc = document.getElementById('hmi-arc');
        if (hmiArc) {
            hmiArc.style.stroke = hmiColor;
            hmiArc.style.strokeDasharray = `${hmiScore}, 100`;
        }

        const start = data.optimized_route[0];
        const end = data.optimized_route[data.optimized_route.length - 1];
        let straightLine = 0;
        let totalDist = 0;
        if (start && end) {
            straightLine = map.distance([start.lat, start.lon], [end.lat, end.lon]);
            for (let i = 0; i < data.optimized_route.length - 1; i++) {
                const p1 = data.optimized_route[i];
                const p2 = data.optimized_route[i+1];
                totalDist += map.distance([p1.lat, p1.lon], [p2.lat, p2.lon]);
            }
        }
        
        let eff = 100;
        if (totalDist > 0 && straightLine > 0) {
            eff = Math.round((straightLine / totalDist) * 100);
            if (eff > 100) eff = 100;
        }
        
        let effColor = eff >= 90 ? "var(--status-safe)" : (eff >= 75 ? "var(--status-caution)" : "var(--status-nogo)");
        document.getElementById('eff-val').textContent = eff + '%';
        document.getElementById('eff-val').style.color = effColor;
        const effArc = document.getElementById('eff-arc');
        if (effArc) {
            effArc.style.stroke = effColor;
            effArc.style.strokeDasharray = `${eff}, 100`;
        }
    }"""

# Insert metrics_logic before updateVerdictPanel
content = content.replace('    function updateVerdictPanel(statusStr, reasonText) {', metrics_logic + '\n\n    function updateVerdictPanel(statusStr, reasonText) {')

# Call updateMetricsPanel inside form submit
query_fetch_old = """                updateVerdictPanel(data.verdict?.verdict, data.verdict?.reason || data.final_advisory_text);
                updateTracePanel(data.execution_trace);"""

query_fetch_new = """                updateVerdictPanel(data.verdict?.verdict, data.verdict?.reason || data.final_advisory_text);
                updateMetricsPanel(data);
                updateTracePanel(data.execution_trace);"""

content = content.replace(query_fetch_old, query_fetch_new)

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(content)
