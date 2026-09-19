document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Map
    // Centered on Gulf of Mannar bounding box (lat 9.0–9.5, lon 79.0–79.8)
    const map = L.map('map', {
        zoomControl: false,
        attributionControl: false
    }).setView([10.0, 79.5], 7);
    L.control.zoom({ position: 'bottomright' }).addTo(map);

    // Use Esri World Imagery for a genuine satellite/dark-ocean maritime aesthetic
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19
    }).addTo(map);

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
    fetch('https://incois.gov.in/geoserver/PFZ_EEZ/wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&TYPENAME=PFZ_EEZ:indiaeez&outputFormat=application/json')
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
        }).catch(err => console.error(err));

    // Fetch Sectors
    fetch('https://incois.gov.in/geoserver/PFZ_Sectors/wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&TYPENAME=PFZ_Sectors:sector_new&outputFormat=application/json')
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
        }).catch(err => console.error(err));

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

    // 3. Chat Form Submit
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = chatInput.value.trim();
        if (!query) return;

        appendMessage('COMMANDER', query, 'user-msg');
        chatInput.value = '';
        
        setLoading(true);

        try {
            const response = await fetch('http://localhost:8000/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_query: query })
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
                
                let blobColor = '#06D6A0';
                if (weather.active || overallStatus === 'NO-GO') {
                    blobColor = '#EF476F';
                } else if (overallStatus === 'CAUTION') {
                    blobColor = '#FFD166';
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
                        color: '#06D6A0',
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
                color: '#FFD166',
                weight: 5, // Increased from 4
                dashArray: '5, 10',
                lineJoin: 'round',
                pane: 'routePane'
            }).addTo(routeGroup);

            const start = data.optimized_route[0];
            L.circleMarker([start.lat, start.lon], {
                radius: 6,
                color: '#FFD166',
                fillColor: '#1C2541',
                fillOpacity: 1,
                weight: 3,
                pane: 'routePane'
            }).addTo(routeGroup).bindPopup('<b>Departure</b>');

            const end = data.optimized_route[data.optimized_route.length - 1];
            L.circleMarker([end.lat, end.lon], {
                radius: 6,
                color: '#EF476F',
                fillColor: '#1C2541',
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
