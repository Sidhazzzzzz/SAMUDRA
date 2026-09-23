import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Sidebar structure overhaul
# We need to extract the parts and rebuild the sidebar content

sidebar_content = """
            <div class="sidebar-top">
                <header class="sidebar-header">
                    <h1>ORCA <span id="persona-title">FISHERMAN PORTAL</span></h1>
                </header>
                <div class="persona-switcher">
                    <button type="button" class="persona-btn active" data-mode="fishing">Fisherman</button>
                    <button type="button" class="persona-btn" data-mode="commercial">Commercial</button>
                </div>
            </div>

            <div class="sidebar-status-card">
                <div class="status-row">
                    <div class="status-label">SYSTEM STATUS</div>
                    <span id="freshness-indicator" class="freshness-indicator hidden"></span>
                    <span id="verdict-badge" class="badge" style="margin-left: auto;">AWAITING QUERY</span>
                </div>
                <div class="status-divider"></div>
                <div id="verdict-reason" class="verdict-reason">
                    No active mission selected.
                </div>
                <div class="status-divider"></div>
                <button type="button" class="primary-btn secondary-btn-style" id="trace-toggle" style="width: 100%;">VIEW SYSTEM TRACE (DAG)</button>
            </div>

            <div id="metrics-strip" class="metrics-strip hidden">
                <!-- Keep the SVG metrics the same, they fit the design -->
                <div class="metric-gauge" id="metric-hmi">
                    <svg viewBox="0 0 36 36" class="circular-chart">
                        <path class="circle-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                        <path class="circle" id="hmi-arc" stroke-dasharray="0, 100" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                    </svg>
                    <div class="metric-info">
                        <span class="val" id="hmi-val">--</span>
                        <span class="lbl">HMI</span>
                    </div>
                </div>
                <div class="metric-gauge" id="metric-efficiency">
                    <svg viewBox="0 0 36 36" class="circular-chart">
                        <path class="circle-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                        <path class="circle" id="eff-arc" stroke-dasharray="0, 100" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                    </svg>
                    <div class="metric-info">
                        <span class="val" id="eff-val">--</span>
                        <span class="lbl">Route Eff.</span>
                    </div>
                </div>
            </div>

            <div id="chat-history" class="chat-history">
                <div class="message system-msg">
                    <strong>ORCA SYSTEM:</strong> Ready to assist. Please specify your query (e.g., "Is it safe to fish near Rameswaram?").
                </div>
                <!-- Advisory messages will get the PDF export button attached to them in JS -->
            </div>

            <div class="chat-input-area">
                <div id="loading-indicator" class="loading-indicator hidden">
                    <span class="spinner"></span> 
                    Processing maritime data...
                </div>
                <form id="chat-form">
                    <input type="text" id="chat-input" placeholder="Enter coordinates, mission, or ask for a route..." autocomplete="off" required>
                    <button type="submit" id="send-btn" class="primary-btn">TRANSMIT</button>
                </form>
            </div>
"""

# Extract the <aside class="sidebar">...</aside>
sidebar_pattern = r'<aside class="sidebar">.*?</aside>'
html = re.sub(sidebar_pattern, f'<aside class="sidebar">\n{sidebar_content}\n        </aside>', html, flags=re.DOTALL)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
