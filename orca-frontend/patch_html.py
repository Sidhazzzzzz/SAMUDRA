with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Add Basemap Toggles
basemap_html = '''        <div id="layer-controls" class="floating-controls">
            <h4 class="controls-title">MAP LAYERS</h4>
            
            <div class="basemap-toggle" style="margin-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px;">
                <div style="font-size: 0.8em; color: var(--text-muted); margin-bottom: 4px;">BASEMAP</div>
                <label class="toggle-label"><input type="radio" name="basemap" value="satellite" checked> Satellite</label>
                <label class="toggle-label"><input type="radio" name="basemap" value="dark"> Dark Matter</label>
            </div>
            
            <div style="font-size: 0.8em; color: var(--text-muted); margin-bottom: 4px;">OVERLAYS</div>'''

content = content.replace('''        <div id="layer-controls" class="floating-controls">
            <h4 class="controls-title">MAP LAYERS</h4>''', basemap_html)

# Add Metrics Strip
metrics_html = '''            <div class="persona-switcher">
                <button type="button" class="persona-btn active" data-mode="fishing">Fisherman</button>
                <button type="button" class="persona-btn" data-mode="commercial">Commercial</button>
            </div>

            <div id="metrics-strip" class="metrics-strip hidden">
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

            <div id="verdict-panel" class="verdict-panel status-unknown">'''

content = content.replace('''            <div class="persona-switcher">
                <button type="button" class="persona-btn active" data-mode="fishing">Fisherman</button>
                <button type="button" class="persona-btn" data-mode="commercial">Commercial</button>
            </div>

            <div id="verdict-panel" class="verdict-panel status-unknown">''', metrics_html)

# Fix trace icon charset
content = content.replace('<span id="trace-icon">-</span>', '<span id="trace-icon">▼</span>')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)
