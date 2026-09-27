// Global Error Handler
(function() {
    function showErrorOverlay(msg, source, lineno, colno, error) {
        if (document.getElementById('global-error-overlay')) return;

        const overlay = document.createElement('div');
        overlay.id = 'global-error-overlay';
        overlay.style.position = 'fixed';
        overlay.style.top = '0';
        overlay.style.left = '0';
        overlay.style.width = '100vw';
        overlay.style.height = '100vh';
        overlay.style.backgroundColor = 'rgba(11, 16, 30, 0.9)';
        overlay.style.zIndex = '9999';
        overlay.style.display = 'flex';
        overlay.style.flexDirection = 'column';
        overlay.style.alignItems = 'center';
        overlay.style.justifyContent = 'center';
        overlay.style.color = '#FFFFFF';
        overlay.style.fontFamily = 'var(--font-body, Inter, sans-serif)';

        const box = document.createElement('div');
        box.style.background = 'var(--bg-panel, #1C2541)';
        box.style.border = '1px solid var(--alert-nogo, #D81B60)';
        box.style.borderRadius = '8px';
        box.style.padding = '30px';
        box.style.maxWidth = '600px';
        box.style.boxShadow = '0 10px 30px rgba(0,0,0,0.5)';
        
        box.innerHTML = `
            <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 20px;">
                <div style="background: rgba(216, 27, 96, 0.2); padding: 10px; border-radius: 50%;">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--alert-nogo, #D81B60)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                        <line x1="12" y1="9" x2="12" y2="13"></line>
                        <line x1="12" y1="17" x2="12.01" y2="17"></line>
                    </svg>
                </div>
                <h2 style="margin: 0; color: var(--alert-nogo, #D81B60); font-size: 1.5rem;">System Exception</h2>
            </div>
            <p style="color: var(--text-muted, #8D99AE); font-size: 0.9rem; margin-bottom: 20px;">
                An unexpected frontend error occurred and halted the dashboard.
            </p>
            <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 4px; font-family: monospace; font-size: 0.85rem; color: #E0E0E0; overflow-x: auto; margin-bottom: 25px; border-left: 3px solid var(--alert-nogo, #D81B60);">
                ${msg}
            </div>
            <button id="error-reload-btn" style="background: var(--alert-nogo, #D81B60); color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: 600; width: 100%; transition: opacity 0.2s;">
                RELOAD DASHBOARD
            </button>
        `;

        overlay.appendChild(box);
        document.body.appendChild(overlay);

        document.getElementById('error-reload-btn').addEventListener('click', () => {
            window.location.reload();
        });
    }

    window.addEventListener('error', function(e) {
        showErrorOverlay(e.message, e.filename, e.lineno, e.colno, e.error);
    });

    window.addEventListener('unhandledrejection', function(e) {
        showErrorOverlay(e.reason ? e.reason.message || e.reason : 'Promise Rejected', '', 0, 0, e.reason);
    });
})();
document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Map
    // Centered on Gulf of Mannar bounding box (lat 9.0–9.5, lon 79.0–79.8)
    const map = L.map('map', {
        zoomControl: false,
        attributionControl: false
    }).setView([10.0, 79.5], 7);
    L.control.zoom({ position: 'bottomright' }).addTo(map);

    // Disable click/scroll propagation for floating UI elements
    const layerControls = document.getElementById('layer-controls');
    const legendBox = document.getElementById('legend-box');
    if (layerControls) {
        L.DomEvent.disableClickPropagation(layerControls);
        L.DomEvent.disableScrollPropagation(layerControls);
    }
    if (legendBox) {
        L.DomEvent.disableClickPropagation(legendBox);
        L.DomEvent.disableScrollPropagation(legendBox);
    }


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
    const riskFieldLayer = L.layerGroup();
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
                        layer.bindPopup(`<b>Sector:</b> ${feature.properties.SECTORNAME}`, {className: 'marine-popup'});
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
    const toggleRiskField = document.getElementById('toggle-risk-field');

    const pfzPane = map.getPane('pfzPane');
    const weatherPane = map.getPane('weatherPane');
    const routePane = map.getPane('routePane');
    const sstPane = map.getPane('sstPane');
    const chlPane = map.getPane('chlPane');
    const eezPane = map.getPane('eezPane');
    const sectorsPane = map.getPane('sectorsPane');
    map.createPane('riskFieldPane');
    map.getPane('riskFieldPane').style.zIndex = 450;
    map.getPane('riskFieldPane').style.filter = 'blur(12px)';
    const riskFieldPane = map.getPane('riskFieldPane');

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
    
    toggleRiskField.addEventListener('change', async () => {
        if (toggleRiskField.checked) {
            riskFieldLayer.addTo(map);
            
            // Show loading state...
            riskFieldLayer.clearLayers();
            const loadingHtml = '<div style="background: var(--bg-navy); padding: 5px 10px; border-radius: 4px; color: white;">Loading Risk Field...</div>';
            const loadingMarker = L.marker(map.getCenter(), {
                icon: L.divIcon({className: 'loading-icon', html: loadingHtml, iconSize: [120, 30]})
            }).addTo(riskFieldLayer);

            try {
                let url = 'http://127.0.0.1:8000/risk-field';
                if (window.lastState && window.lastState.origin) {
                    url += `?origin_lat=${window.lastState.origin.lat}&origin_lon=${window.lastState.origin.lon}`;
                }
                
                const response = await fetch(url);
                const data = await response.json();
                
                riskFieldLayer.clearLayers();
                
                if (data.status === 'success' && data.grid) {
                    data.grid.forEach(cell => {
                        const bounds = [
                            [cell.lat, cell.lon],
                            [cell.lat + 0.025, cell.lon + 0.025]
                        ];
                        
                        let fillColor = 'rgba(0, 191, 165, 0.1)'; // Calm green/blue
                        let strokeColor = 'rgba(255, 255, 255, 0.02)';
                        
                        if (!cell.is_traversable) {
                            fillColor = 'rgba(0, 0, 0, 0.3)'; // Land/Shallows
                            strokeColor = 'transparent';
                        } else if (cell.static_imbl_penalty > 0) {
                            fillColor = 'rgba(255, 107, 107, 0.6)'; // Hazard red
                        } else if (cell.accumulated && cell.accumulated.imbl_penalty > 0) {
                            fillColor = 'rgba(255, 107, 107, 0.4)'; // Hazard red (path)
                        } else if (cell.accumulated) {
                            fillColor = 'rgba(0, 191, 165, 0.3)'; // Explored water
                        }
                        
                        const rect = L.rectangle(bounds, {
                            color: strokeColor,
                            weight: 0,
                            fillColor: fillColor,
                            fillOpacity: 1,
                            pane: 'riskFieldPane',
                            className: 'risk-field-cell'
                        });
                        
                        // Popup logic
                        let popupContent = `<div style="font-family: var(--font-main); font-size: 13px;">`;
                        popupContent += `<strong>Cell:</strong> ${cell.lat.toFixed(4)}, ${cell.lon.toFixed(4)}<br/>`;
                        popupContent += `<strong>Depth:</strong> ${cell.depth ? cell.depth + 'm' : 'Unknown'}<br/>`;
                        
                        if (!cell.is_traversable) {
                            popupContent += `<span style="color: var(--alert-danger)">Not Traversable (Land/Shallows)</span>`;
                        } else {
                            if (cell.static_imbl_penalty > 0) {
                                popupContent += `<span style="color: var(--alert-danger)">IMBL Penalty: ${cell.static_imbl_penalty}</span><br/>`;
                            } else {
                                popupContent += `<span style="color: var(--alert-safe)">IMBL Penalty: 0</span><br/>`;
                            }
                            
                            if (cell.accumulated) {
                                popupContent += `<hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.2); margin: 5px 0;" />`;
                                popupContent += `<strong>Total Accumulated Cost:</strong> ${cell.accumulated.total.toFixed(1)}<br/>`;
                                popupContent += `• Distance: ${cell.accumulated.distance.toFixed(1)} km<br/>`;
                                popupContent += `• Acc. Penalty: ${cell.accumulated.imbl_penalty.toFixed(1)}`;
                            }
                        }
                        popupContent += `</div>`;
                        
                        rect.bindPopup(popupContent, {
                            className: 'marine-popup'
                        });
                        
                        rect.addTo(riskFieldLayer);
                    });
                }
            } catch (error) {
                console.error("Failed to load risk field:", error);
                riskFieldLayer.clearLayers();
            }
        } else {
            map.removeLayer(riskFieldLayer);
        }
    });

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
    document.body.setAttribute('data-persona', currentMode);
            setLoading(false);
            document.getElementById('scientist-loading-indicator').classList.add('hidden');
            document.getElementById('scientist-send-btn').disabled = false;
            document.getElementById('scientist-input').disabled = false;
    document.querySelectorAll('.persona-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.persona-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentMode = e.target.dataset.mode;
            document.body.setAttribute('data-persona', currentMode);
            setLoading(false);
            document.getElementById('scientist-loading-indicator').classList.add('hidden');
            document.getElementById('scientist-send-btn').disabled = false;
            document.getElementById('scientist-input').disabled = false;
            
            const title = document.getElementById('persona-title');
            const headerTitle = document.querySelector('.sidebar-header h1');
            headerTitle.classList.add('persona-switching');
            // chatInput.classList.add('persona-switching');
            
            setTimeout(() => {
                try {
                    const chatModeView = document.getElementById('chat-mode-view');
                    const authModeView = document.getElementById('authority-mode-view');
                    const scientistModeView = document.getElementById('scientist-mode-view');

                    if (currentMode === "authority") {
                        title.textContent = "COASTAL AUTHORITY";
                        if (chatModeView) chatModeView.classList.add('hidden');
                        if (scientistModeView) scientistModeView.classList.add('hidden');
                        if (authModeView) authModeView.classList.remove('hidden');
                        initAuthorityMode();
                    } else if (currentMode === "scientist") {
                        title.textContent = "SCIENTIST / RESEARCH";
                        if (chatModeView) chatModeView.classList.add('hidden');
                        if (authModeView) authModeView.classList.add('hidden');
                        if (scientistModeView) scientistModeView.classList.remove('hidden');
                        exitAuthorityMode();
                        renderDepthCrossSection(); // Render the depth chart if a route exists
                    } else {
                        if (currentMode === "commercial") {
                            title.textContent = "COMMERCIAL NAVIGATOR";
                            if (chatInput) chatInput.placeholder = "e.g., plan a commercial route from Rameswaram to Mandapam...";
                        } else {
                            title.textContent = "FISHERMAN PORTAL";
                            if (chatInput) chatInput.placeholder = "Enter coordinates, mission, or ask for a route...";
                        }
                        if (chatModeView) chatModeView.classList.remove('hidden');
                        if (authModeView) authModeView.classList.add('hidden');
                        if (scientistModeView) scientistModeView.classList.add('hidden');
                        exitAuthorityMode();
                    }
                } catch(e) {
                    console.error('Error during persona switch:', e);
                } finally {
                    if (headerTitle) headerTitle.classList.remove('persona-switching');
                    if (chatInput) chatInput.classList.remove('persona-switching');
                }
            }, 300);
        });
    });

    // 3. Chat Form Submit
    // Track conversation turns for multi-turn context (last 6 messages = 3 full turns)
    const conversationTurns = [];

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        let query = chatInput.value.trim();
        if (!query) return;

        appendMessage('COMMANDER', query, 'user-msg');
        conversationTurns.push({ role: 'user', content: query });
        

        chatInput.value = '';
        
        setLoading(true);

        try {
            const response = await fetch('http://127.0.0.1:8000/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_query: query,
                    mode: currentMode,
                    chat_history: conversationTurns.slice(-6)
                })
            });

            if (!response.ok) {
                throw new Error(`Backend Error: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            // Track assistant response for multi-turn context
            if (data.final_advisory_text) {
                conversationTurns.push({ role: 'assistant', content: data.final_advisory_text });
            }
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
                    const response = await fetch('http://127.0.0.1:8000/export-pdf', {
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
        
        // Pin the export button to the status card so it's always visible without scrolling
        const statusCard = document.querySelector('.sidebar-status-card');
        if (statusCard && !document.getElementById('export-btn')) {
            // Only append once
            statusCard.appendChild(exportBtn);
        } else if (statusCard) {
            statusCard.appendChild(exportBtn);
        }


        // Update System Trace & Freshness
        if (data.execution_trace) {
            updateTracePanel(data.execution_trace);
            // Add ready pulse to trace button
            const traceToggle = document.getElementById('trace-toggle');
            if (traceToggle) {
                traceToggle.classList.add('ready-pulse');
            }            
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
                }).addTo(weatherGroup).bindPopup(`<b>Weather Bounds</b><br>Active Storm: ${weather.active}<br>Wave Height: ${weather.wave_height_m}m`, {className: 'marine-popup'});
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
                        opacity: 0.8,
                        className: 'interactive-map-element'
                    };
                },
                onEachFeature: function(feature, layer) {
                    const props = feature.properties || {};
                    const sector = props.State_Name || 'Unknown';
                    const length = props.Length ? parseFloat(props.Length).toFixed(1) : '?';
                    layer.bindPopup(`<b>PFZ Advisory Line</b><br>Sector: ${sector}<br>Length: ${length} km`, {className: 'marine-popup'});
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
                pane: 'routePane',
                className: 'interactive-map-element'
            }).addTo(routeGroup);

            const start = data.optimized_route[0];
            L.circleMarker([start.lat, start.lon], {
                radius: 6,
                color: '#111111',
                fillColor: '#F4EFEA',
                fillOpacity: 1,
                weight: 3,
                pane: 'routePane'
            }).addTo(routeGroup).bindPopup('<b>Departure</b>', {className: 'marine-popup'});

            const end = data.optimized_route[data.optimized_route.length - 1];
            L.circleMarker([end.lat, end.lon], {
                radius: 6,
                color: '#111111',
                fillColor: '#F4EFEA',
                fillOpacity: 1,
                weight: 3,
                pane: 'routePane'
            }).addTo(routeGroup).bindPopup('<b>Destination</b>', {className: 'marine-popup'});

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


    // Trace Toggle Logic
    const traceToggle = document.getElementById('trace-toggle');
    const traceContent = document.getElementById('trace-content');
    const traceIcon = document.getElementById('trace-icon');
    const traceList = document.getElementById('trace-list');

    const dagModal = document.getElementById('dag-modal');
    const dagCloseBtn = document.getElementById('dag-close-btn');
    
    traceToggle.addEventListener('click', () => {
        traceToggle.classList.remove('ready-pulse');
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
        const container = document.querySelector('.dag-pipeline-container');
        if (!container) return;
        
        container.innerHTML = '';
        container.style.position = 'relative';
        container.style.display = 'flex';
        container.style.justifyContent = 'space-between';
        container.style.alignItems = 'stretch';
        container.style.padding = '40px 20px';
        container.style.minHeight = '350px';
        
        if (!traceData || traceData.length === 0) {
            container.innerHTML = '<div style="color:var(--text-muted);">No trace data available.</div>';
            return;
        }

        // 1. Group nodes into layers
        const l0 = [], l1 = [], l2 = [], l3 = [];
        traceData.forEach(step => {
            const sl = step.stage.toLowerCase();
            if (sl.includes('intent')) l0.push(step);
            else if (sl.includes('verdict')) l2.push(step);
            else if (sl.includes('narrat')) l3.push(step);
            else l1.push(step);
        });
        
        const layers = [];
        if (l0.length) layers.push(l0);
        if (l1.length) layers.push(l1);
        if (l2.length) layers.push(l2);
        if (l3.length) layers.push(l3);

        // 2. SVG Background for connections
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.style.position = 'absolute';
        svg.style.top = '0';
        svg.style.left = '0';
        svg.style.width = '100%';
        svg.style.height = '100%';
        svg.style.zIndex = '0';
        svg.style.pointerEvents = 'none';
        container.appendChild(svg);

        // 3. Build Columns and Nodes
        const cols = [];
        layers.forEach((layerSteps, colIdx) => {
            const col = document.createElement('div');
            col.className = 'dag-col';
            col.style.display = 'flex';
            col.style.flexDirection = 'column';
            col.style.justifyContent = 'center';
            col.style.gap = '40px';
            col.style.zIndex = '1';
            
            const nodeEls = [];
            layerSteps.forEach(step => {
                const node = document.createElement('div');
                
                let sourceClass = 'live';
                const src = step.source_type || step.source || '';
                const summ = step.summary || '';
                if (src === 'error' || src === 'mock_error' || summ.includes('error') || summ.includes('failed') || summ.includes('No valid route')) {
                    sourceClass = 'error';
                } else if (src === 'fallback' || src === 'mock_fallback') {
                    sourceClass = 'fallback';
                }
                // we drop the time-based amber here because parallel tools take different times
                
                node.className = `dag-node ${sourceClass}`;
                node.style.position = 'relative'; // for connecting lines
                
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
                    <div class="dag-node-summary" style="opacity:0; transition: opacity 0.3s; font-size: 0.6rem; max-width: 120px;">${step.summary}</div>
                `;
                
                col.appendChild(node);
                nodeEls.push({ step, el: node, sourceClass });
            });
            
            container.appendChild(col);
            cols.push(nodeEls);
        });

        // 4. Draw Lines & Animate
        // Wait for next frame so flexbox layouts the nodes
        requestAnimationFrame(() => {
            const containerRect = container.getBoundingClientRect();
            
            // Draw paths
            for (let i = 0; i < cols.length - 1; i++) {
                const fromNodes = cols[i];
                const toNodes = cols[i+1];
                
                fromNodes.forEach(fromObj => {
                    const fromRect = fromObj.el.querySelector('.dag-node-circle').getBoundingClientRect();
                    const startX = fromRect.right - containerRect.left;
                    const startY = fromRect.top + fromRect.height/2 - containerRect.top;
                    
                    toNodes.forEach(toObj => {
                        const toRect = toObj.el.querySelector('.dag-node-circle').getBoundingClientRect();
                        const endX = toRect.left - containerRect.left;
                        const endY = toRect.top + toRect.height/2 - containerRect.top;
                        
                        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                        const cp1x = startX + (endX - startX) / 2;
                        const d = `M ${startX} ${startY} C ${cp1x} ${startY}, ${cp1x} ${endY}, ${endX} ${endY}`;
                        
                        path.setAttribute('d', d);
                        path.setAttribute('fill', 'none');
                        
                        path.style.stroke = 'rgba(58,107,140, 0.4)';
                        path.style.strokeWidth = '3';
                        path.style.strokeDasharray = '10, 10';
                        path.classList.add('flow-path');
                        
                        path.style.opacity = '0';
                        path.style.transition = 'opacity 0.4s ease';
                        
                        svg.appendChild(path);
                        
                        if (!toObj.incomingPaths) toObj.incomingPaths = [];
                        toObj.incomingPaths.push(path);
                    });
                });
            }
            
            // Animation sequence
            let delay = 300;
            cols.forEach((colNodes, colIndex) => {
                setTimeout(() => {
                    colNodes.forEach(nodeObj => {
                        // Reveal incoming paths
                        if (nodeObj.incomingPaths) {
                            nodeObj.incomingPaths.forEach(p => p.style.opacity = '1');
                        }
                        
                        nodeObj.el.classList.add('active');
                        const circle = nodeObj.el.querySelector('.dag-node-circle');
                        circle.style.transform = 'scale(1.1)';
                        
                        circle.style.boxShadow = nodeObj.sourceClass === 'error' ? '0 0 25px rgba(216, 27, 96, 0.8)' : 
                                                 nodeObj.sourceClass === 'fallback' ? '0 0 25px rgba(255, 215, 0, 0.8)' : 
                                                 '0 0 25px rgba(58, 107, 140, 0.8)';
                        
                        nodeObj.el.querySelectorAll('div').forEach(el => el.style.opacity = '1');
                        
                        setTimeout(() => {
                            circle.style.transform = 'scale(1)';
                            circle.style.boxShadow = nodeObj.sourceClass === 'error' ? '0 0 10px rgba(216, 27, 96, 0.4)' : 
                                                     nodeObj.sourceClass === 'fallback' ? '0 0 10px rgba(255, 215, 0, 0.4)' : 
                                                     '0 0 10px rgba(58, 107, 140, 0.4)';
                        }, 400);
                    });
                }, delay);
                
                // Add delay for next column
                delay += 800; // Stagger tree levels
            });
        
        });
    }

    // =========================================================================
    // COASTAL AUTHORITY MODE LOGIC
    // =========================================================================
    const simulatedFleet = [
        {"id": "V-101", "lat": 9.25, "lon": 79.15, "type": "Fishing"},
        {"id": "V-102", "lat": 9.30, "lon": 79.20, "type": "Commercial"},
        {"id": "V-103", "lat": 9.15, "lon": 79.10, "type": "Fishing"},
        {"id": "V-104", "lat": 9.40, "lon": 79.35, "type": "Fishing"},
        {"id": "V-105", "lat": 9.10, "lon": 79.60, "type": "Cargo"},
        {"id": "V-106", "lat": 9.45, "lon": 79.70, "type": "Fishing"},
        {"id": "V-107", "lat": 9.35, "lon": 79.40, "type": "Passenger"},
        {"id": "V-108", "lat": 9.20, "lon": 79.50, "type": "Fishing"},
        {"id": "V-109", "lat": 9.32, "lon": 79.55, "type": "Fishing"},
        {"id": "V-110", "lat": 9.12, "lon": 79.25, "type": "Commercial"},
        {"id": "V-111", "lat": 9.28, "lon": 79.31, "type": "Fishing"},
        {"id": "V-112", "lat": 9.27, "lon": 79.12, "type": "Fishing"},
    ];

    let fleetGroup = null;
    let authDrawnItems = null;
    let authDrawControl = null;
    let currentPolygon = null;

    function initAuthorityMode() {
        try {
            if (!fleetGroup) {
                fleetGroup = L.featureGroup().addTo(map);
                simulatedFleet.forEach(v => {
                    const icon = L.divIcon({ className: 'vessel-icon', html: 'VSL', iconSize: [24, 24] });
                    const marker = L.marker([v.lat, v.lon], {icon}).addTo(fleetGroup);
                    marker.bindPopup(`<b>${v.id}</b><br>Type: ${v.type}`, {className: 'marine-popup'});
                    marker.vesselId = v.id;
                });
            } else if (!map.hasLayer(fleetGroup)) {
                map.addLayer(fleetGroup);
            }

            if (!authDrawnItems) {
                authDrawnItems = L.featureGroup().addTo(map);
                
                authDrawControl = new L.Control.Draw({
                    position: 'topright',
                    draw: {
                        polygon: { 
                            shapeOptions: { 
                                color: '#3A6B8C', 
                                weight: 3,
                                fillOpacity: 0.2,
                                className: 'authority-polygon interactive-map-element'
                            },
                            icon: new L.DivIcon({
                                iconSize: new L.Point(12, 12),
                                className: 'leaflet-div-icon leaflet-editing-icon authority-draw-vertex'
                            }),
                            touchIcon: new L.DivIcon({
                                iconSize: new L.Point(12, 12),
                                className: 'leaflet-div-icon leaflet-editing-icon authority-draw-vertex'
                            })
                        },
                        polyline: false, rectangle: false, circle: false, marker: false, circlemarker: false
                    },
                    edit: false
                });
                
                map.on(L.Draw.Event.CREATED, function (e) {
                    authDrawnItems.clearLayers();
                    const layer = e.layer;
                    authDrawnItems.addLayer(layer);
                    
                    const latlngs = layer.getLatLngs()[0];
                    currentPolygon = latlngs.map(ll => [ll.lat, ll.lng]);
                    
                    document.getElementById('broadcast-form-container').classList.remove('hidden');
                    document.getElementById('broadcast-result-container').classList.add('hidden');
                    resetVesselHighlights();
                });
            }
            if (authDrawControl) {
                map.addControl(authDrawControl);
            }
            
            fetchRankings();
        } catch (err) {
            alert("Error in initAuthorityMode: " + err.message);
            console.error(err);
        }
    }
    
    function exitAuthorityMode() {
        if (fleetGroup && map.hasLayer(fleetGroup)) {
            map.removeLayer(fleetGroup);
        }
        if (authDrawControl) {
            map.removeControl(authDrawControl);
        }
        if (authDrawnItems) {
            authDrawnItems.clearLayers();
        }
        document.getElementById('broadcast-form-container').classList.add('hidden');
        document.getElementById('broadcast-result-container').classList.add('hidden');
        resetVesselHighlights();
    }

    function resetVesselHighlights() {
        if (!fleetGroup) return;
        fleetGroup.eachLayer(layer => {
            if (layer.getElement()) {
                layer.getElement().classList.remove('highlighted');
            }
        });
    }

    async function fetchRankings() {
        try {
            const res = await fetch('http://127.0.0.1:8000/coastal-authority/block-rankings');
            if (!res.ok) {
                alert("Fetch failed with status: " + res.status);
                return;
            }
            const data = await res.json();
            if (data.status === 'success') {
                const tbody = document.querySelector('#ranking-table tbody');
                tbody.innerHTML = '';
                data.rankings.forEach(block => {
                    const tr = document.createElement('tr');
                    
                    let tierClass = 'tier-safe';
                    if (block.action_tier === 'NO-GO') tierClass = 'tier-no-go';
                    else if (block.action_tier === 'CAUTION') tierClass = 'tier-caution';
                    
                    tr.innerHTML = `
                        <td>${block.block_name}</td>
                        <td>${block.hmi_score}</td>
                        <td class="${tierClass}">${block.action_tier}</td>
                    `;
                    tr.addEventListener('click', () => {
                        map.flyTo([block.lat, block.lon], 12);
                    });
                    tbody.appendChild(tr);
                });
            } else {
                alert("API returned error status: " + JSON.stringify(data));
            }
        } catch (e) {
            alert('Error fetching rankings: ' + e.message);
            console.error('Error fetching rankings', e);
        }
    }

    document.getElementById('broadcast-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!currentPolygon) return;
        
        const eventType = document.getElementById('bc-event-type').value;
        const severity = document.getElementById('bc-severity').value;
        
        try {
            const res = await fetch('http://127.0.0.1:8000/coastal-authority/broadcast', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    polygon_coordinates: currentPolygon,
                    event_type: eventType,
                    severity: severity
                })
            });
            const data = await res.json();
            
            if (data.status === 'success') {
                // Highlight vessels
                resetVesselHighlights();
                if (fleetGroup) {
                    fleetGroup.eachLayer(layer => {
                        if (data.affected_vessels.includes(layer.vesselId) && layer.getElement()) {
                            layer.getElement().classList.add('highlighted');
                        }
                    });
                }
                
                // Show result
                document.getElementById('broadcast-result-container').classList.remove('hidden');
                document.getElementById('affected-count').textContent = `Alert dispatched to ${data.affected_vessels.length} vessel(s).`;
                document.getElementById('cap-xml-display').textContent = data.cap_xml;
                document.getElementById('cap-xml-display').classList.add('hidden');
            }
        } catch (e) {
            console.error('Broadcast failed', e);
        }
    });

    document.getElementById('toggle-xml-btn').addEventListener('click', () => {
        const pre = document.getElementById('cap-xml-display');
        if (pre.classList.contains('hidden')) {
            pre.classList.remove('hidden');
        } else {
            pre.classList.add('hidden');
        }
    });

    // =========================================================================
    // SCIENTIST MODE LOGIC
    // =========================================================================
    const scientistForm = document.getElementById('scientist-form');
    const scientistInput = document.getElementById('scientist-input');
    const scientistLoading = document.getElementById('scientist-loading-indicator');
    const scientistSendBtn = document.getElementById('scientist-send-btn');
    const scientistAnalysisContent = document.getElementById('scientist-analysis-content');
    const scientistWelcomeText = document.getElementById('scientist-welcome-text');
    const trendChartContainer = document.getElementById('trend-chart-container');
    const trendChartWrapper = document.getElementById('trend-chart-wrapper');
    const depthChartWrapper = document.getElementById('depth-chart-wrapper');
    const depthChartEmptyState = document.getElementById('depth-chart-empty-state');

    scientistForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        let query = scientistInput.value.trim();
        if (!query) return;

        scientistInput.value = '';
        
        scientistLoading.classList.remove('hidden');
        scientistSendBtn.disabled = true;
        scientistInput.disabled = true;
        
        scientistWelcomeText.classList.add('hidden');
        scientistAnalysisContent.classList.add('hidden');

        try {
            const response = await fetch('http://127.0.0.1:8000/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_query: query, mode: 'scientist' })
            });

            if (!response.ok) {
                throw new Error(`Backend Error: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            
            // Render text analysis
            scientistAnalysisContent.innerHTML = marked.parse(data.final_advisory_text || data.abort_reason || 'No text provided.');
            scientistAnalysisContent.classList.remove('hidden');

            // Render Trends Chart
            if (data.yearly_data && data.yearly_data.length > 0) {
                renderTrendChart(data.yearly_data);
            } else {
                trendChartWrapper.innerHTML = '<div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: var(--text-muted); font-size: 0.8rem; text-align: center; width: 100%;">No trend data available for this query</div>';
            }

        } catch (error) {
            console.error(error);
            scientistAnalysisContent.innerHTML = `<span class="error-msg">${error.message}</span>`;
            scientistAnalysisContent.classList.remove('hidden');
        } finally {
            scientistLoading.classList.add('hidden');
            scientistSendBtn.disabled = false;
            scientistInput.disabled = false;
            scientistInput.focus();
        }
    });

    function renderTrendChart(yearlyData) {
        trendChartWrapper.innerHTML = '';
        const width = 400; // Fixed viewBox width based on sidebar
        const height = 180;
        const padX = 45;
        const padY = 30;

        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', '100%');
        svg.setAttribute('height', '100%');
        svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
        svg.style.overflow = 'visible';

        const years = yearlyData.map(d => d.year);
        const sstVals = yearlyData.map(d => d.mean_sst_celsius);
        const hasChl = yearlyData.some(d => d.mean_chlorophyll_a_mg_per_m3 !== null && d.mean_chlorophyll_a_mg_per_m3 !== undefined);
        
        const minSst = Math.min(...sstVals) - 0.5;
        const maxSst = Math.max(...sstVals) + 0.5;

        // Draw grid and axes
        for(let i=0; i<=4; i++) {
            const y = padY + (i/4)*(height - 2*padY);
            const gridLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            gridLine.setAttribute('x1', padX); gridLine.setAttribute('y1', y);
            gridLine.setAttribute('x2', width - padX); gridLine.setAttribute('y2', y);
            gridLine.setAttribute('stroke', 'rgba(255,255,255,0.05)');
            svg.appendChild(gridLine);
            
            const yLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            yLabel.setAttribute('x', padX - 5); yLabel.setAttribute('y', y + 3);
            yLabel.setAttribute('fill', 'var(--text-muted)'); yLabel.setAttribute('font-size', '9');
            yLabel.setAttribute('text-anchor', 'end');
            yLabel.textContent = (maxSst - (i/4)*(maxSst - minSst)).toFixed(1);
            svg.appendChild(yLabel);
        }

        // Draw Line for SST
        let sstPathD = '';
        yearlyData.forEach((d, i) => {
            const x = padX + (i / (yearlyData.length - 1 || 1)) * (width - 2 * padX);
            const y = height - padY - ((d.mean_sst_celsius - minSst) / (maxSst - minSst)) * (height - 2 * padY);
            
            if (i === 0) sstPathD += `M ${x} ${y} `;
            else sstPathD += `L ${x} ${y} `;
            
            const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            dot.setAttribute('cx', x); dot.setAttribute('cy', y);
            dot.setAttribute('r', 4); dot.setAttribute('fill', '#FF6B6B');
            
            const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
            const sstVal = (d.mean_sst_celsius !== null && d.mean_sst_celsius !== undefined) ? d.mean_sst_celsius.toFixed(2) + ' °C' : 'Data unavailable';
            title.textContent = `Year: ${d.year}\nSST: ${sstVal}`;
            dot.appendChild(title);
            svg.appendChild(dot);
            
            const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            label.setAttribute('x', x); label.setAttribute('y', height - padY + 15);
            label.setAttribute('fill', 'var(--text-muted)'); label.setAttribute('font-size', '10');
            label.setAttribute('text-anchor', 'middle');
            label.textContent = d.year;
            svg.appendChild(label);
        });

        const sstPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        sstPath.setAttribute('d', sstPathD);
        sstPath.setAttribute('stroke', '#FF6B6B'); sstPath.setAttribute('stroke-width', '2');
        sstPath.setAttribute('fill', 'none');
        svg.appendChild(sstPath);
        
        if (hasChl) {
            const chlVals = yearlyData.map(d => d.mean_chlorophyll_a_mg_per_m3).filter(c => c !== null);
            const maxChl = Math.max(...chlVals) || 1;
            yearlyData.forEach((d, i) => {
                const x = padX + (i / (yearlyData.length - 1 || 1)) * (width - 2 * padX);
                if (d.mean_chlorophyll_a_mg_per_m3 !== null) {
                    const barHeight = (d.mean_chlorophyll_a_mg_per_m3 / maxChl) * (height - 2 * padY);
                    const barY = height - padY - barHeight;
                    const bar = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                    bar.setAttribute('x', x - 6); bar.setAttribute('y', barY);
                    bar.setAttribute('width', 12); bar.setAttribute('height', barHeight);
                    bar.setAttribute('fill', 'rgba(0, 191, 165, 0.4)');
                    const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
                    const chlVal = d.mean_chlorophyll_a_mg_per_m3.toFixed(2) + ' mg/m³';
                    title.textContent = `Chlorophyll: ${chlVal}`;
                    bar.appendChild(title);
                    svg.insertBefore(bar, sstPath);
                } else {
                    const unav = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                    unav.setAttribute('x', x); unav.setAttribute('y', height - padY - 5);
                    unav.setAttribute('fill', 'var(--text-muted)'); unav.setAttribute('font-size', '9');
                    unav.setAttribute('text-anchor', 'middle');
                    unav.textContent = 'NO DATA';
                    svg.appendChild(unav);
                }
            });
        }

        const legendSst = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        legendSst.setAttribute('x', padX); legendSst.setAttribute('y', 15);
        legendSst.setAttribute('fill', '#FF6B6B'); legendSst.setAttribute('font-size', '10');
        legendSst.textContent = '● SST (°C)';
        svg.appendChild(legendSst);
        
        if (hasChl) {
            const legendChl = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            legendChl.setAttribute('x', padX + 80); legendChl.setAttribute('y', 15);
            legendChl.setAttribute('fill', '#00BFA5'); legendChl.setAttribute('font-size', '10');
            legendChl.textContent = '■ Chlorophyll';
            svg.appendChild(legendChl);
        }

        trendChartWrapper.appendChild(svg);
    }

    // Export function to global scope to be called on persona switch
    window.renderDepthCrossSection = function() {
        if (!window.lastState || !window.lastState.optimized_route || window.lastState.optimized_route.length === 0) {
            depthChartWrapper.innerHTML = '';
            depthChartWrapper.appendChild(depthChartEmptyState);
            return;
        }
        
        const route = window.lastState.optimized_route;
        const hasDepth = route.some(wp => wp.depth !== undefined && wp.depth !== null);
        
        if (!hasDepth) {
            depthChartWrapper.innerHTML = '<div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: var(--text-muted); font-size: 0.8rem; text-align: center; width: 100%;">No bathymetry data available for this route.</div>';
            return;
        }

        depthChartWrapper.innerHTML = '';
        const width = 400;
        const height = 120;
        const padX = 45;
        const padY = 20;

        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', '100%');
        svg.setAttribute('height', '100%');
        svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
        svg.style.overflow = 'visible';

        const depths = route.map(wp => Math.abs(wp.depth || 0)); 
        const maxDepth = Math.max(...depths, 5); 
        
        // Y Axis Grid
        for(let i=0; i<=2; i++) {
            const y = padY + (i/2)*(height - 2*padY);
            const grid = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            grid.setAttribute('x1', padX); grid.setAttribute('y1', y);
            grid.setAttribute('x2', width - padX); grid.setAttribute('y2', y);
            grid.setAttribute('stroke', 'rgba(255,255,255,0.05)');
            svg.appendChild(grid);
            
            const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            label.setAttribute('x', padX - 5); label.setAttribute('y', y + 4);
            label.setAttribute('fill', 'var(--text-muted)'); label.setAttribute('font-size', '9');
            label.setAttribute('text-anchor', 'end');
            label.textContent = `-${((i/2)*maxDepth).toFixed(0)}m`;
            svg.appendChild(label);
        }

        let pathD = `M ${padX} ${padY} `;
        
        route.forEach((wp, i) => {
            const x = padX + (i / (route.length - 1 || 1)) * (width - 2 * padX);
            const y = padY + (Math.abs(wp.depth || 0) / maxDepth) * (height - 2 * padY);
            pathD += `L ${x} ${y} `;
            
            if (i === 0 || i === route.length - 1) {
                const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                label.setAttribute('x', x); label.setAttribute('y', height - padY + 15);
                label.setAttribute('fill', 'var(--text-muted)'); label.setAttribute('font-size', '9');
                label.setAttribute('text-anchor', i === 0 ? 'start' : 'end');
                label.textContent = i === 0 ? 'START' : 'END';
                svg.appendChild(label);
            }
        });
        
        pathD += `L ${width - padX} ${padY} Z`;

        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', pathD);
        path.setAttribute('fill', 'rgba(0, 191, 165, 0.15)');
        path.setAttribute('stroke', '#00BFA5');
        path.setAttribute('stroke-width', '2');
        svg.appendChild(path);

        const seaLevel = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        seaLevel.setAttribute('x1', padX); seaLevel.setAttribute('y1', padY);
        seaLevel.setAttribute('x2', width - padX); seaLevel.setAttribute('y2', padY);
        seaLevel.setAttribute('stroke', '#5C8CA3');
        seaLevel.setAttribute('stroke-dasharray', '4 4');
        svg.appendChild(seaLevel);

        depthChartWrapper.appendChild(svg);
    };

});

