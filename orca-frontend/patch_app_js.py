import re

with open('app.js', 'r', encoding='utf-8') as f:
    app_js = f.read()

# 1. Update export button logic
# Currently: const exportBtn = document.getElementById('export-btn'); if (exportBtn) exportBtn.classList.remove('hidden');
export_old = r"const exportBtn = document\.getElementById\('export-btn'\);\s*if \(exportBtn\) exportBtn\.classList\.remove\('hidden'\);"
export_new = """// Create/move export button to the latest system message
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
"""
# Wait, the original `exportBtn` logic in `app.js` is both in `handleSystemResponse` and globally.
# I need to clean up the global listener and replace it entirely.
# Let's just remove the global PDF Export Logic.
global_export = r"// PDF Export Logic.*?\}\);\s*\}"
app_js = re.sub(global_export, "", app_js, flags=re.DOTALL)
app_js = re.sub(export_old, export_new, app_js)


# 2. Update DAG Modal animation and styling
# On modal open, we animate line progressively and pop-in nodes.
# Color nodes based on source: 
#   blue/teal for live
#   amber/gold for fallback or slow
#   red for error
update_trace_old = r"const dagNodesContainer = document\.getElementById\('dag-nodes'\);.*?\}\n"
# Wait, updateTracePanel was rewritten in my previous run.
# Let's replace the whole function using regex matching everything inside it.
update_trace_pattern = r"function updateTracePanel\(traceData\) \{.*?(?=\n    // PDF Export Logic|\n    // Wait, let's find the end of updateTracePanel|\n    const chatForm)"
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
        const baseDelay = 400; // base time between nodes
        let cumulativeDelay = 300;
        
        traceData.forEach((step, index) => {
            const node = document.createElement('div');
            
            let sourceClass = 'live';
            if (step.source === 'error' || step.source === 'mock_error' || step.summary.includes('error') || step.summary.includes('failed') || step.summary.includes('No valid route')) {
                sourceClass = 'error';
            } else if (step.source === 'fallback' || step.source === 'mock_fallback') {
                sourceClass = 'fallback';
            } else if (step.duration_ms > (maxDuration * 0.8) && maxDuration > 1000) {
                // Unusually long relative to others (amber)
                sourceClass = 'fallback'; 
            }
            
            node.className = `dag-node ${sourceClass}`;
            
            // Icons based on stage
            let icon = '⚙️';
            if (step.stage.includes('intent')) icon = '🧠';
            else if (step.stage.includes('pfz') || step.stage.includes('weather') || step.stage.includes('route')) icon = '📡';
            else if (step.stage.includes('verdict')) icon = '⚖️';
            else if (step.stage.includes('narration')) icon = '📝';
            
            node.innerHTML = `
                <div class="dag-node-circle" style="transform: scale(0); transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);">${icon}</div>
                <div class="dag-node-label" style="opacity:0; transition: opacity 0.3s;">${step.stage.replace('_agent', '').replace('_parser', '')}</div>
                <div class="dag-node-time" style="opacity:0; transition: opacity 0.3s;">${step.duration_ms} ms</div>
                <div class="dag-node-summary" style="opacity:0; transition: opacity 0.3s;">${step.summary || step.source}</div>
            `;
            
            dagNodesContainer.appendChild(node);
            
            // Calculate proportional delay based on this step's real duration (scaled)
            // Capped at 1500ms max per step so we don't wait forever
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
    
# We will use simple string replacement since regex can be brittle here
start_idx = app_js.find('function updateTracePanel(traceData) {')
if start_idx != -1:
    end_idx = app_js.find('const chatForm =', start_idx)
    if end_idx == -1:
        end_idx = app_js.find('let exportBtn', start_idx)
    if end_idx != -1:
        app_js = app_js[:start_idx] + update_trace_replacement + "\n\n    " + app_js[end_idx:]

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(app_js)
