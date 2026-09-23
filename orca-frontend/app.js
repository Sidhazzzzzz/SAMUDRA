document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Map
    // Centered on Gulf of Mannar bounding box (lat 9.0–9.5, lon 79.0–79.8)
    const map = L.map('map', {
        zoomControl: false,
        attributionControl: false
    }).setView([10.0, 79.5], 7);
    L.control.zoom({ position: 'bottomright' }).addTo(map);

    // Use Esri World Imagery for a genuine satellite/dark-ocean maritime aesthetic
    const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19
    }).addTo(map);

    const darkLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        className: 'osm-dark-filter',
        maxZoom: 19
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
    }

    // Create custom panes for all data layers
    const allPanes = ['sstPane', 'chlPane', 'eezPane', 'sectorsPane', 'weatherPane', 'pfzPane', 'routePane'];
    allPanes.forEach(p => {
        map.createPane(p);
        map.getPane(p).classList.add('fade-pane');
    });

    // FeatureGroups for each data type
    const eezGroup = L.layerGroup().addTo(map);
    const sectorsGroup = L.layerGroup().addTo(map);
    const pfzGroup = L.featureGroup().addTo(map);
    const weatherGroup = L.featureGroup().addTo(map);
    const routeGroup = L.featureGroup().addTo(map);

    // WMS Layers
    const sstLayer = L.tileLayer.wms('https://incois.gov.in/geoserver/PFZ-TUNA-SST-CHL/wms', {
        layers: 'PFZ-TUNA-SST-CHL:sst',
        format: 'image/png',
        transparent: true,
        pane: 'sstPane'
    }).addTo(map);

    const chlLayer = L.tileLayer.wms('https://incois.gov.in/geoserver/PFZ-TUNA-SST-CHL/wms', {
        layers: 'PFZ-TUNA-SST-CHL:chl',
        format: 'image/png',
        transparent: true,
        pane: 'chlPane'
    }).addTo(map);
    
    sstLayer.on('tileerror', () => markLayerError('toggle-sst'));
    chlLayer.on('tileerror', () => markLayerError('toggle-chl'));
    
    sstLayer.on('tileerror', () => markLayerError('toggle-sst'));
    chlLayer.on('tileerror', () => markLayerError('toggle-chl'));

    // Dynamic layer tracking for bounds
    let currentBounds = null;

    // 2. DOM Elements
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatHistory = document.getElementById('chat-history');
    const sendBtn = document.getElementById('send-btn');
    const loadingIndicator = document.getElementById('loading-indicator');
    
    const verdictPanel = document.getElementById('verdict-panel');
    const verdictBadge = document.getElementById('verdict-badge');
    const verdictReason = document.getElementById('verdict-reason');

    // Fetch EEZ Boundary
    fetchWithTimeout('https://incois.gov.in/geoserver/PFZ_EEZ/wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&TYPENAME=PFZ_EEZ:indiaeez&outputFormat=application/json')
        .then(res => res.json())
        .then(data => {
            L.geoJSON(data, {
                pane: 'eezPane',
                style: {
                    color: '#FF6B6B',
                    weight: 3,
                    dashArray: '10, 15',
                    opacity: 0.8
                }
            }).addTo(eezGroup);
        }).catch(err => {
            console.error(err);
            markLayerError('toggle-eez');
        });

    // Fetch Sectors
    fetchWithTimeout('https://incois.gov.in/geoserver/PFZ_Sectors/wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&TYPENAME=PFZ_Sectors:sector_new&outputFormat=application/json')
        .then(res => res.json())
        .then(data => {
            L.geoJSON(data, {
                pane: 'sectorsPane',
                style: {
                    color: '#A3C4F3',
                    weight: 1,
                    fillOpacity: 0.1,
                    opacity: 0.3
                },
                onEachFeature: function(feature, layer) {
                    if (feature.properties && feature.properties.SECTORNAME) {
                        layer.bindPopup(`<b>Sector:</b> ${feature.properties.SECTORNAME}`);
                    }
                }
            }).addTo(sectorsGroup);
        }).catch(err => {
            console.error(err);
            markLayerError('toggle-sectors');
        });

    // Toggle logic
    const togglePfz = document.getElementById('toggle-pfz');
    const toggleWeather = document.getElementById('toggle-weather');
    const toggleRoute = document.getElementById('toggle-route');
    const toggleSst = document.getElementById('toggle-sst');
    const toggleChl = document.getElementById('toggle-chl');
    const toggleEez = document.getElementById('toggle-eez');
    const toggleSectors = document.getElementById('toggle-sectors');

    const pfzPane = map.getPane('pfzPane');
    const weatherPane = map.getPane('weatherPane');
    const routePane = map.getPane('routePane');
    const sstPane = map.getPane('sstPane');
    const chlPane = map.getPane('chlPane');
    const eezPane = map.getPane('eezPane');
    const sectorsPane = map.getPane('sectorsPane');

    const legendBox = document.getElementById('legend-box');
    const legendImg = document.getElementById('legend-img');
    const legendTitle = document.getElementById('legend-title');

    function syncLayerVisibility() {
        if (togglePfz.checked) pfzPane.classList.remove('hidden-pane');
        else pfzPane.classList.add('hidden-pane');
        
        if (toggleWeather.checked) weatherPane.classList.remove('hidden-pane');
        else weatherPane.classList.add('hidden-pane');
        
        if (toggleRoute.checked) routePane.classList.remove('hidden-pane');
        else routePane.classList.add('hidden-pane');

        if (toggleSst.checked) sstPane.classList.remove('hidden-pane');
        else sstPane.classList.add('hidden-pane');

        if (toggleChl.checked) chlPane.classList.remove('hidden-pane');
        else chlPane.classList.add('hidden-pane');

        if (toggleEez.checked) eezPane.classList.remove('hidden-pane');
        else eezPane.classList.add('hidden-pane');

        if (toggleSectors.checked) sectorsPane.classList.remove('hidden-pane');
        else sectorsPane.classList.add('hidden-pane');

        if (toggleSst.checked) {
            legendBox.classList.remove('hidden');
            legendTitle.textContent = "Sea Surface Temp";
            legendImg.src = "https://incois.gov.in/geoserver/PFZ-TUNA-SST-CHL/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&LAYER=PFZ-TUNA-SST-CHL:sst&LEGEND_OPTIONS=fontAntiAliasing:true;dpi:120";
        } else if (toggleChl.checked) {
            legendBox.classList.remove('hidden');
            legendTitle.textContent = "Chlorophyll";
            legendImg.src = "https://incois.gov.in/geoserver/PFZ-TUNA-SST-CHL/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&LAYER=PFZ-TUNA-SST-CHL:chl&LEGEND_OPTIONS=fontAntiAliasing:true;dpi:120";
        } else {
            legendBox.classList.add('hidden');
        }
    }

    togglePfz.addEventListener('change', syncLayerVisibility);
    toggleWeather.addEventListener('change', syncLayerVisibility);
    toggleRoute.addEventListener('change', syncLayerVisibility);
    toggleEez.addEventListener('change', syncLayerVisibility);
    toggleSectors.addEventListener('change', syncLayerVisibility);
    
    toggleSst.addEventListener('change', () => {
        if (toggleSst.checked) toggleChl.checked = false;
        syncLayerVisibility();
    });
    toggleChl.addEventListener('change', () => {
        if (toggleChl.checked) toggleSst.checked = false;
        syncLayerVisibility();
    });

    // Initialize visibility state on page load
    syncLayerVisibility();


    // Persona Switcher
    let currentMode = "fishing";
    document.querySelectorAll('.persona-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.persona-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentMode = e.target.dataset.mode;
            
            const title = document.getElementById('persona-title');
            const headerTitle = document.querySelector('.sidebar-header h1');
            headerTitle.classList.add('persona-switching');
            chatInput.classList.add('persona-switching');
            
            setTimeout(() => {
                if (currentMode === "commercial") {
                    title.textContent = "COMMERCIAL NAVIGATOR";
                    chatInput.placeholder = "e.g., plan a commercial route from Rameswaram to Mandapam...";
                } else {
                    title.textContent = "FISHERMAN PORTAL";
                    chatInput.placeholder = "Enter coordinates, mission, or ask for a route...";
                }
                headerTitle.classList.remove('persona-switching');
                chatInput.classList.remove('persona-switching');
            }, 300);
        });
    });

    // 3. Chat Form Submit
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        let query = chatInput.value.trim();
        if (!query) return;

        appendMessage('COMMANDER', query, 'user-msg');
        

        chatInput.value = '';
        
        setLoading(true);

        try {
            const response = await fetch('http://localhost:8000/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_query: query, mode: currentMode })
            });

            if (!response.ok) {
                throw new Error(`Backend Error: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            handleSystemResponse(data);

        } catch (error) {
            console.error(error);
            appendMessage('SYSTEM ERROR', error.message + ' (Check if backend is running)', 'system-msg error-msg');
        } finally {
            setLoading(false);
        }
    });

    // 4. Handle Data & Update UI
    function handleSystemResponse(data) {
        // Store lastState for PDF export
        window.lastState = data;
        // Create/move export button to the latest system message
        let exportBtn = document.getElementById('export-btn');
        if (!exportBtn) {
            exportBtn = document.createElement('button');
            exportBtn.id = 'export-btn';
            exportBtn.className = 'primary-btn export-advisory-btn';
            exportBtn.textContent = 'Export Advisory (PDF)';
            
            exportBtn.addEventListener('click', async () => {
                if (!window.lastState) return;
                const originalText = exportBtn.textContent;
                exportBtn.textContent = 'Generating PDF...';
                exportBtn.disabled = true;
                try {
                    const response = await fetch('http://localhost:8000/export-pdf', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(window.lastState)
                    });
                    if (!response.ok) throw new Error('PDF export failed');
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'orca_advisory.pdf';
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    window.URL.revokeObjectURL(url);
                } catch (err) {
                    console.error(err);
                    alert('Failed to export PDF.');
                } finally {
                    exportBtn.textContent = originalText;
                    exportBtn.disabled = false;
                }
            });
        }
        exportBtn.classList.remove('hidden');
        
        // Find the last message (which is the one we just added) and append the button
        const lastMsg = chatHistory.lastElementChild;
        if (lastMsg) {
            lastMsg.appendChild(exportBtn);
        }


        // Update System Trace & Freshness
        if (data.execution_trace) {
            updateTracePanel(data.execution_trace);
            
            const freshnessInd = document.getElementById('freshness-indicator');
            if (freshnessInd) {
                freshnessInd.classList.remove('hidden', 'freshness-live', 'freshness-fallback', 'freshness-error');
                const hasError = data.execution_trace.some(t => t.source_type === 'error');
                const hasFallback = data.execution_trace.some(t => t.source_type === 'fallback' || t.source_type === 'mock');
                
                if (hasError) {
                    freshnessInd.textContent = 'DATA ERROR';
                    freshnessInd.classList.add('freshness-error');
                } else if (hasFallback) {
                    freshnessInd.textContent = 'USING FALLBACK DATA';
                    freshnessInd.classList.add('freshness-fallback');
                } else {
                    freshnessInd.textContent = 'LIVE DATA';
                    freshnessInd.classList.add('freshness-live');
                }
            }
        }

        // A. Update Verdict Panel
        const overallStatus = data.verdict ? data.verdict.verdict : (data.status || 'UNKNOWN');
        if (data.verdict) {
            updateVerdictPanel(overallStatus, data.verdict.reason);
        } else {
            updateVerdictPanel(overallStatus, 'Location out of bounds or no verdict evaluated.');
        }

        // B. Update Chat History
        if (data.final_advisory_text) {
            const formattedText = data.final_advisory_text.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br>');
            appendMessage('ORCA SYSTEM', formattedText, 'system-msg');
        } else if (data.abort_reason) {
            appendMessage('ORCA SYSTEM', `Mission Aborted: ${data.abort_reason}`, 'system-msg error-msg');
        }

        // C. Update Map Layers
        pfzGroup.clearLayers();
        weatherGroup.clearLayers();
        routeGroup.clearLayers();
        
        const boundsList = [];

        // Draw Weather Risks
        if (data.weather_risks && data.weather_risks.length > 0) {
            data.weather_risks.forEach(weather => {
                if (!weather.region_bbox) return;
                // region_bbox is [minLat, minLon, maxLat, maxLon]
                const [minLat, minLon, maxLat, maxLon] = weather.region_bbox;
                const rectBounds = [[minLat, minLon], [maxLat, maxLon]];
                
                let blobColor = '#5C8CA3';
                if (weather.active || overallStatus === 'NO-GO') {
                    blobColor = '#D81B60';
                } else if (overallStatus === 'CAUTION') {
                    blobColor = '#FFD700';
                }

                // Use a standard rectangle but apply a heavy CSS blur to create a soft, geographic heatmap blob
                L.rectangle(rectBounds, {
                    color: 'transparent', // No border
                    fillColor: blobColor,
                    fillOpacity: 0.6,
                    weight: 0,
                    className: 'weather-blob',
                    pane: 'weatherPane'
                }).addTo(weatherGroup).bindPopup(`<b>Weather Bounds</b><br>Active Storm: ${weather.active}<br>Wave Height: ${weather.wave_height_m}m`);
                
                boundsList.push(L.rectangle(rectBounds).getBounds());
            });
        }

        // Draw PFZ Targets (Real INCOIS pfzlines are MultiLineString)
        if (data.pfz_targets && data.pfz_targets.length > 0) {
            const pfzLayer = L.geoJSON(data.pfz_targets, {
                pane: 'pfzPane',
                style: function(feature) {
                    return {
                        color: '#5C8CA3',
                        weight: 4,
                        opacity: 0.8
                    };
                },
                onEachFeature: function(feature, layer) {
                    const props = feature.properties || {};
                    const sector = props.State_Name || 'Unknown';
                    const length = props.Length ? parseFloat(props.Length).toFixed(1) : '?';
                    layer.bindPopup(`<b>PFZ Advisory Line</b><br>Sector: ${sector}<br>Length: ${length} km`);
                }
            }).addTo(pfzGroup);
            
            if (pfzLayer.getBounds().isValid()) {
                boundsList.push(pfzLayer.getBounds());
            }
        }

        // Draw Optimized Route
        if (data.optimized_route && data.optimized_route.length > 0) {
            const rawLatlngs = data.optimized_route.map(wp => [wp.lat, wp.lon]);
            
            // Lightweight Catmull-Rom spline for rendering only
            function catmullRomSpline(points, pointsPerSegment) {
                if (points.length < 2) return points;
                
                function getPoint(p0, p1, p2, p3, t) {
                    const t2 = t * t;
                    const t3 = t2 * t;
                    const lat = 0.5 * (
                        (2 * p1[0]) +
                        (-p0[0] + p2[0]) * t +
                        (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                        (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
                    );
                    const lon = 0.5 * (
                        (2 * p1[1]) +
                        (-p0[1] + p2[1]) * t +
                        (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                        (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
                    );
                    return [lat, lon];
                }

                const smoothed = [];
                for (let i = 0; i < points.length - 1; i++) {
                    const p0 = points[i === 0 ? 0 : i - 1];
                    const p1 = points[i];
                    const p2 = points[i + 1];
                    const p3 = points[i + 2 >= points.length ? points.length - 1 : i + 2];
                    
                    for (let j = 0; j < pointsPerSegment; j++) {
                        const t = j / pointsPerSegment;
                        smoothed.push(getPoint(p0, p1, p2, p3, t));
                    }
                }
                smoothed.push(points[points.length - 1]);
                return smoothed;
            }
            
            const smoothedLatLngs = catmullRomSpline(rawLatlngs, 10);
            
            const routeLine = L.polyline(smoothedLatLngs, {
                color: '#111111',
                weight: 5, // Increased from 4
                dashArray: '5, 10',
                lineJoin: 'round',
                pane: 'routePane'
            }).addTo(routeGroup);

            const start = data.optimized_route[0];
            L.circleMarker([start.lat, start.lon], {
                radius: 6,
                color: '#111111',
                fillColor: '#F4EFEA',
                fillOpacity: 1,
                weight: 3,
                pane: 'routePane'
            }).addTo(routeGroup).bindPopup('<b>Departure</b>');

            const end = data.optimized_route[data.optimized_route.length - 1];
            L.circleMarker([end.lat, end.lon], {
                radius: 6,
                color: '#111111',
                fillColor: '#F4EFEA',
                fillOpacity: 1,
                weight: 3,
                pane: 'routePane'
            }).addTo(routeGroup).bindPopup('<b>Destination</b>');

            boundsList.push(routeLine.getBounds());
        }

        // Update bounds
        if (boundsList.length > 0) {
            const combinedBounds = boundsList[0];
            boundsList.forEach(b => combinedBounds.extend(b));
            map.fitBounds(combinedBounds, { padding: [30, 30] });
        } else {
            map.setView([9.25, 79.4], 10);
        }

        // Initial sync of visibility
        syncLayerVisibility();
    }

    // 5. Helper Functions
    function appendMessage(sender, text, cssClass) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${cssClass}`;
        msgDiv.innerHTML = `<strong>${sender}:</strong> <div>${text}</div>`;
        chatHistory.appendChild(msgDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    function updateMetricsPanel(data) {
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
    }

    function updateVerdictPanel(statusStr, reasonText) {
        verdictPanel.classList.remove('status-safe', 'status-caution', 'status-nogo', 'status-unknown', 'status-distress');
        
        const status = statusStr ? statusStr.toUpperCase() : 'UNKNOWN';
        
        if (status === 'DISTRESS_DETECTED') {
            verdictPanel.classList.add('status-distress');
        } else if (status === 'SAFE') {
            verdictPanel.classList.add('status-safe');
        } else if (status === 'CAUTION') {
            verdictPanel.classList.add('status-caution');
        } else if (status === 'NO-GO' || status === 'NOGO') {
            verdictPanel.classList.add('status-nogo');
        } else {
            verdictPanel.classList.add('status-unknown');
        }

        verdictBadge.textContent = status === 'DISTRESS_DETECTED' ? 'EMERGENCY' : status;
        verdictReason.innerHTML = marked.parse(reasonText || 'No details provided.');
    }

    function setLoading(isLoading) {
        if (isLoading) {
            loadingIndicator.classList.remove('hidden');
            sendBtn.disabled = true;
            chatInput.disabled = true;
        } else {
            loadingIndicator.classList.add('hidden');
            sendBtn.disabled = false;
            chatInput.disabled = false;
            chatInput.focus();
        }
    }
});


    // Trace Toggle Logic
    const traceToggle = document.getElementById('trace-toggle');
    const traceContent = document.getElementById('trace-content');
    const traceIcon = document.getElementById('trace-icon');
    const traceList = document.getElementById('trace-list');

    const dagModal = document.getElementById('dag-modal');
    const dagCloseBtn = document.getElementById('dag-close-btn');
    
    traceToggle.addEventListener('click', () => {
        dagModal.classList.remove('hidden');
        // trigger reflow
        void dagModal.offsetWidth;
        dagModal.classList.add('show');
    });
    
    dagCloseBtn.addEventListener('click', () => {
        dagModal.classList.remove('show');
        setTimeout(() => dagModal.classList.add('hidden'), 400);
    });
    
    dagModal.addEventListener('click', (e) => {
        if (e.target === dagModal) {
            dagModal.classList.remove('show');
            setTimeout(() => dagModal.classList.add('hidden'), 400);
        }
    });

    function updateTracePanel(traceData) {
        const dagNodesContainer = document.getElementById('dag-nodes');
        const dagLineFill = document.getElementById('dag-line-fill');
        if (!dagNodesContainer || !dagLineFill) return;
        dagNodesContainer.innerHTML = '';
        dagLineFill.style.width = '0%';
        
        if (!traceData || traceData.length === 0) {
            dagNodesContainer.innerHTML = '<div style="color:var(--text-muted);">No trace data available.</div>';
            return;
        }

        const totalNodes = traceData.length;
        
        // Find the max duration to scale animation times
        let maxDuration = 10;
        traceData.forEach(step => {
            if (step.duration_ms > maxDuration) maxDuration = step.duration_ms;
        });
        
        // Define animation base speed
        const baseDelay = 400; 
        let cumulativeDelay = 300;
        
        traceData.forEach((step, index) => {
            const node = document.createElement('div');
            
            let sourceClass = 'live';
            const src = step.source_type || step.source || '';
            const summ = step.summary || '';
            if (src === 'error' || src === 'mock_error' || summ.includes('error') || summ.includes('failed') || summ.includes('No valid route')) {
                sourceClass = 'error';
            } else if (src === 'fallback' || src === 'mock_fallback') {
                sourceClass = 'fallback';
            } else if (step.duration_ms > (maxDuration * 0.8) && maxDuration > 1000) {
                // Unusually long relative to others (amber)
                sourceClass = 'fallback'; 
            }
            
            node.className = `dag-node ${sourceClass}`;
            
            // Icons based on stage
            let icon = '⚙️';
            const stageLower = step.stage.toLowerCase();
            if (stageLower.includes('intent')) icon = '🧠';
            else if (stageLower.includes('pfz') || stageLower.includes('weather') || stageLower.includes('route') || stageLower.includes('tool')) icon = '📡';
            else if (stageLower.includes('verdict')) icon = '⚖️';
            else if (stageLower.includes('narrat')) icon = '📝';
            
            node.innerHTML = `
                <div class="dag-node-circle" style="transform: scale(0); transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);">${icon}</div>
                <div class="dag-node-label" style="opacity:0; transition: opacity 0.3s;">${step.stage.replace('_agent', '').replace('_parser', '').replace('tool_execution: ', '')}</div>
                <div class="dag-node-time" style="opacity:0; transition: opacity 0.3s;">${step.duration_ms} ms</div>
                <div class="dag-node-summary" style="opacity:0; transition: opacity 0.3s;">${step.summary}</div>
            `;
            
            dagNodesContainer.appendChild(node);
            
            // Calculate proportional delay based on this step's real duration (scaled)
            let animTime = (step.duration_ms / maxDuration) * 1000;
            if (animTime > 1500) animTime = 1500;
            if (animTime < 200) animTime = 200;
            
            // Animate sequentially
            setTimeout(() => {
                node.classList.add('active');
                
                // Pop-in circle
                const circle = node.querySelector('.dag-node-circle');
                circle.style.transform = 'scale(1.1)';
                
                // Add glowing pulse to current node
                circle.style.boxShadow = sourceClass === 'error' ? '0 0 25px rgba(216, 27, 96, 0.8)' : 
                                         sourceClass === 'fallback' ? '0 0 25px rgba(255, 215, 0, 0.8)' : 
                                         '0 0 25px rgba(58, 107, 140, 0.8)';
                
                // Show text
                node.querySelectorAll('div').forEach(el => el.style.opacity = '1');
                
                setTimeout(() => {
                    // Settle scale and glow
                    circle.style.transform = 'scale(1)';
                    circle.style.boxShadow = sourceClass === 'error' ? '0 0 10px rgba(216, 27, 96, 0.4)' : 
                                         sourceClass === 'fallback' ? '0 0 10px rgba(255, 215, 0, 0.4)' : 
                                         '0 0 10px rgba(58, 107, 140, 0.4)';
                }, 400);

                // Draw line fill smoothly to this node
                const pct = totalNodes > 1 ? (index / (totalNodes - 1)) * 100 : 100;
                dagLineFill.style.transition = `width ${animTime}ms linear`;
                dagLineFill.style.width = `${pct}%`;
                
            }, cumulativeDelay);
            
            cumulativeDelay += animTime + 100;
        });
    }
