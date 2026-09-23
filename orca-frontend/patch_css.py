with open('style.css', 'r', encoding='utf-8') as f:
    content = f.read()

root_vars = '''    /* Status Colors */
    --status-safe: #06D6A0;
    --status-caution: #FFD166;
    --status-nogo: #EF476F;

    /* Unified Motion System */
    --transition-fast: 150ms;
    --transition-medium: 300ms;
    --transition-slow: 500ms;
    --ease-curve: cubic-bezier(0.4, 0.0, 0.2, 1);'''

content = content.replace('''    /* Status Colors */
    --status-safe: #06D6A0;
    --status-caution: #FFD166;
    --status-nogo: #EF476F;''', root_vars)

# Disable default map shadows, replace with clean UI rendering
content += '''

/* ========================================================
   SECTION 1: Fallback Errors
   ======================================================== */
.layer-error {
    color: var(--status-caution);
    font-size: 0.85em;
    margin-left: 6px;
    animation: fadeIn var(--transition-medium) var(--ease-curve);
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

/* ========================================================
   SECTION 3: Metrics Strip (Arc Gauges)
   ======================================================== */
.metrics-strip {
    display: flex;
    justify-content: space-around;
    padding: 10px 0;
    background-color: var(--bg-panel);
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    animation: fadeIn var(--transition-medium) var(--ease-curve);
}
.metric-gauge {
    display: flex;
    align-items: center;
    gap: 10px;
}
.circular-chart {
    display: block;
    margin: 0;
    max-width: 40px;
    max-height: 40px;
}
.circle-bg {
    fill: none;
    stroke: rgba(255, 255, 255, 0.1);
    stroke-width: 3.8;
}
.circle {
    fill: none;
    stroke-width: 3.8;
    stroke-linecap: round;
    transition: stroke-dasharray var(--transition-slow) var(--ease-curve), stroke var(--transition-medium) var(--ease-curve);
}
.metric-info {
    display: flex;
    flex-direction: column;
}
.metric-info .val {
    font-weight: 700;
    font-size: 1.1em;
    font-family: 'Oswald', sans-serif;
}
.metric-info .lbl {
    font-size: 0.7em;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ========================================================
   SECTION 4: Persona Transition
   ======================================================== */
.persona-switching {
    opacity: 0;
    transform: translateY(5px);
}
.sidebar-header h1, #chat-input::placeholder {
    transition: opacity var(--transition-medium) var(--ease-curve), transform var(--transition-medium) var(--ease-curve);
}

/* ========================================================
   SECTION 6: Trace Animation
   ======================================================== */
.trace-item {
    opacity: 0;
    transform: translateX(-10px);
    transition: opacity var(--transition-medium) var(--ease-curve), transform var(--transition-medium) var(--ease-curve);
}
.trace-item.visible {
    opacity: 1;
    transform: translateX(0);
}
'''

with open('style.css', 'w', encoding='utf-8') as f:
    f.write(content)
