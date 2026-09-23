import re

with open('app.js', 'r', encoding='utf-8') as f:
    app_js = f.read()

update_trace_replacement = """function updateTracePanel(traceData) {
        const dagNodesContainer = document.getElementById('dag-nodes');
        const dagLineFill = document.getElementById('dag-line-fill');
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
            if (src === 'error' || src === 'mock_error' || step.summary.includes('error') || step.summary.includes('failed') || step.summary.includes('No valid route')) {
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
    }"""

start_idx = app_js.find('function updateTracePanel(traceData) {')
end_idx = app_js.find('const chatForm =', start_idx)
if end_idx == -1:
    end_idx = app_js.find('const exportBtn', start_idx)
    
if start_idx != -1 and end_idx != -1:
    app_js = app_js[:start_idx] + update_trace_replacement + "\n\n    " + app_js[end_idx:]
else:
    print(f"Failed to find indices. Start: {start_idx}, End: {end_idx}")

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(app_js)
