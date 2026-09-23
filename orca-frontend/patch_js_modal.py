import re

with open('app.js', 'r', encoding='utf-8') as f:
    app_js = f.read()

# 1. Replace traceToggle listener
trace_toggle_old = r"""    traceToggle\.addEventListener\('click', \(\) => \{
        traceContent\.classList\.toggle\('hidden'\);
        traceIcon\.textContent = traceContent\.classList\.contains\('hidden'\) \? '▼' : '▲';
    \}\);"""
trace_toggle_new = """    const dagModal = document.getElementById('dag-modal');
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
    });"""

if 'const dagModal' not in app_js:
    app_js = re.sub(trace_toggle_old, trace_toggle_new, app_js)

# 2. Rewrite updateTracePanel
update_trace_old = r"""    function updateTracePanel\(traceData\) \{.*?(?=\n    // PDF Export Logic)"""
update_trace_new = """    function updateTracePanel(traceData) {
        const dagNodesContainer = document.getElementById('dag-nodes');
        const dagLineFill = document.getElementById('dag-line-fill');
        dagNodesContainer.innerHTML = '';
        dagLineFill.style.width = '0%';
        
        if (!traceData || traceData.length === 0) {
            dagNodesContainer.innerHTML = '<div style="color:var(--text-muted);">No trace data available.</div>';
            return;
        }

        let currentDelay = 0;
        const totalNodes = traceData.length;
        
        traceData.forEach((step, index) => {
            const node = document.createElement('div');
            // If source is error/fallback, add that class for color styling
            let sourceClass = '';
            if (step.source === 'error' || step.source === 'mock_error') sourceClass = 'error';
            else if (step.source === 'fallback') sourceClass = 'fallback';
            else sourceClass = 'live';
            
            node.className = `dag-node ${sourceClass}`;
            
            node.innerHTML = `
                <div class="dag-node-circle">${index + 1}</div>
                <div class="dag-node-label">${step.stage.replace('_agent', '').replace('_parser', '')}</div>
                <div class="dag-node-time">${step.duration_ms} ms</div>
                <div class="dag-node-summary">${step.summary || step.source}</div>
            `;
            
            dagNodesContainer.appendChild(node);
            
            // Animate sequentially
            setTimeout(() => {
                node.classList.add('active');
                // Calculate percentage for the line fill (from first node to current node)
                // If there's 1 node, it's 0. If 5 nodes, node 0=0%, node 4=100%
                const pct = totalNodes > 1 ? (index / (totalNodes - 1)) * 100 : 100;
                dagLineFill.style.width = `${pct}%`;
            }, 300 + (index * 400)); // 400ms interval between nodes
        });
    }
"""
app_js = re.sub(update_trace_old, update_trace_new, app_js, flags=re.DOTALL)

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(app_js)
