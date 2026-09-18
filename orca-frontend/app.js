document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Map
    // Centered on Gulf of Mannar bounding box (lat 9.0–9.5, lon 79.0–79.8)
    const map = L.map('map', {
        zoomControl: false // Move it if needed, or leave default
    }).setView([9.25, 79.4], 10);
    L.control.zoom({ position: 'bottomright' }).addTo(map);

    // Use Esri World Imagery for a genuine satellite/dark-ocean maritime aesthetic
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
        maxZoom: 19
    }).addTo(map);

    // Create custom panes for smooth CSS transitions
    const panes = ['weatherPane', 'pfzPane', 'routePane'];
    panes.forEach((p, idx) => {
        map.createPane(p);
        map.getPane(p).style.zIndex = 400 + idx; // Stack them properly
        map.getPane(p).classList.add('fade-pane');
    });

    // FeatureGroups for each data type
    const pfzGroup = L.featureGroup().addTo(map);
    const weatherGroup = L.featureGroup().addTo(map);
    const routeGroup = L.featureGroup().addTo(map);

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

    // Toggle controls
    const togglePfz = document.getElementById('toggle-pfz');
    const toggleWeather = document.getElementById('toggle-weather');
    const toggleRoute = document.getElementById('toggle-route');

    function syncLayerVisibility(e) {
        if (e) console.log('Layer toggle clicked:', e.target.id, 'New state:', e.target.checked);
        
        const pfzPane = map.getPane('pfzPane');
        const weatherPane = map.getPane('weatherPane');
        const routePane = map.getPane('routePane');
        
        if (!pfzPane || !weatherPane || !routePane) {
            console.error('Leaflet panes are missing!');
            return;
        }

        if (togglePfz.checked) pfzPane.classList.remove('hidden-pane');
        else pfzPane.classList.add('hidden-pane');

        if (toggleWeather.checked) weatherPane.classList.remove('hidden-pane');
        else weatherPane.classList.add('hidden-pane');

        if (toggleRoute.checked) routePane.classList.remove('hidden-pane');
        else routePane.classList.add('hidden-pane');
    }

    togglePfz.addEventListener('change', syncLayerVisibility);
    toggleWeather.addEventListener('change', syncLayerVisibility);
    toggleRoute.addEventListener('change', syncLayerVisibility);

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
        const overallStatus = data.verdict ? data.verdict.verdict : 'UNKNOWN';
        if (data.verdict) {
            updateVerdictPanel(overallStatus, data.verdict.reason);
        } else {
            updateVerdictPanel('UNKNOWN', data.abort_reason || 'No verdict evaluated.');
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
                
                let rectColor = '#06D6A0'; // Default safe green
                let fillColor = '#06D6A0';
                
                if (weather.active || overallStatus === 'NO-GO') {
                    rectColor = '#EF476F';
                    fillColor = '#EF476F';
                } else if (overallStatus === 'CAUTION') {
                    rectColor = '#FFD166';
                    fillColor = '#FFD166';
                }

                L.rectangle(rectBounds, {
                    color: rectColor,
                    fillColor: fillColor,
                    fillOpacity: 0.25, // Increased for better contrast
                    weight: 3, // Increased from 2
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
            const latlngs = data.optimized_route.map(wp => [wp.lat, wp.lon]);
            
            const routeLine = L.polyline(latlngs, {
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
        verdictPanel.classList.remove('status-safe', 'status-caution', 'status-nogo', 'status-unknown');
        
        const status = statusStr ? statusStr.toUpperCase() : 'UNKNOWN';
        
        if (status === 'SAFE') {
            verdictPanel.classList.add('status-safe');
        } else if (status === 'CAUTION') {
            verdictPanel.classList.add('status-caution');
        } else if (status === 'NO-GO' || status === 'NOGO') {
            verdictPanel.classList.add('status-nogo');
        } else {
            verdictPanel.classList.add('status-unknown');
        }

        verdictBadge.textContent = status;
        verdictReason.textContent = reasonText || 'No details provided.';
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
