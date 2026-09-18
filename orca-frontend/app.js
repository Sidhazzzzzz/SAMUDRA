document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Map
    // Centered on Gulf of Mannar bounding box (lat 9.0–9.5, lon 79.0–79.8)
    const map = L.map('map').setView([9.25, 79.4], 10);

    // Use CartoDB Dark Matter for a deep navy / maritime radar aesthetic
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);

    // FeatureGroup to hold dynamic layers (so we can clear them easily)
    const dynamicLayers = L.featureGroup().addTo(map);

    // 2. DOM Elements
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatHistory = document.getElementById('chat-history');
    const sendBtn = document.getElementById('send-btn');
    const loadingIndicator = document.getElementById('loading-indicator');
    
    const verdictPanel = document.getElementById('verdict-panel');
    const verdictBadge = document.getElementById('verdict-badge');
    const verdictReason = document.getElementById('verdict-reason');

    // 3. Chat Form Submit
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = chatInput.value.trim();
        if (!query) return;

        // Append user message
        appendMessage('COMMANDER', query, 'user-msg');
        chatInput.value = '';
        
        // UI Loading state
        setLoading(true);

        try {
            // POST to backend
            const response = await fetch('http://localhost:8000/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_query: query })
            });

            if (!response.ok) {
                throw new Error(`Backend Error: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            
            // Process the response
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
        if (data.verdict) {
            updateVerdictPanel(data.verdict.verdict, data.verdict.reason);
        } else {
            // If LLM failed or no verdict generated
            updateVerdictPanel('UNKNOWN', data.abort_reason || 'No verdict evaluated.');
        }

        // B. Update Chat History
        if (data.final_advisory_text) {
            // Convert simple markdown-like double asterisks to bold if needed
            const formattedText = data.final_advisory_text.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br>');
            appendMessage('ORCA SYSTEM', formattedText, 'system-msg');
        } else if (data.abort_reason) {
            appendMessage('ORCA SYSTEM', `Mission Aborted: ${data.abort_reason}`, 'system-msg error-msg');
        }

        // C. Update Map (Clear old layers first)
        dynamicLayers.clearLayers();

        // Draw PFZ Targets
        if (data.pfz_targets && data.pfz_targets.length > 0) {
            data.pfz_targets.forEach(pfz => {
                // radius is in nautical miles, Leaflet expects meters (1 nm = 1852 m)
                const radiusMeters = pfz.radius_nm * 1852;
                const circle = L.circle([pfz.centroid_lat, pfz.centroid_lon], {
                    color: '#06D6A0',
                    fillColor: '#06D6A0',
                    fillOpacity: 0.2,
                    weight: 2
                }).addTo(dynamicLayers);
                
                const speciesList = pfz.species_likely ? pfz.species_likely.join(', ') : 'Unknown';
                circle.bindPopup(`<b>Zone:</b> ${pfz.id}<br><b>Species:</b> ${speciesList}<br><b>Confidence:</b> ${(pfz.confidence*100).toFixed(0)}%`);
            });
        }

        // Draw Optimized Route
        if (data.optimized_route && data.optimized_route.length > 0) {
            const latlngs = data.optimized_route.map(wp => [wp.lat, wp.lon]);
            
            // Draw Polyline
            const routeLine = L.polyline(latlngs, {
                color: '#FFD166',
                weight: 4,
                dashArray: '5, 10',
                lineJoin: 'round'
            }).addTo(dynamicLayers);

            // Add Origin Marker
            const start = data.optimized_route[0];
            L.circleMarker([start.lat, start.lon], {
                radius: 6,
                color: '#FFD166',
                fillColor: '#1C2541',
                fillOpacity: 1,
                weight: 3
            }).addTo(dynamicLayers).bindPopup('<b>Departure</b>');

            // Add Destination Marker
            const end = data.optimized_route[data.optimized_route.length - 1];
            L.circleMarker([end.lat, end.lon], {
                radius: 6,
                color: '#EF476F',
                fillColor: '#1C2541',
                fillOpacity: 1,
                weight: 3
            }).addTo(dynamicLayers).bindPopup('<b>Destination</b>');

            // Optionally adjust map bounds to fit route/pfzs
            map.fitBounds(dynamicLayers.getBounds(), { padding: [30, 30] });
        } else if (data.pfz_targets && data.pfz_targets.length > 0) {
            // Just fit to PFZs if no route
            map.fitBounds(dynamicLayers.getBounds(), { padding: [30, 30] });
        } else {
            // Reset to default box
            map.setView([9.25, 79.4], 10);
        }
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
        // Remove existing status classes
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
