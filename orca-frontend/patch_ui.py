import re

# --- 1. Patch app.js for CartoDB URL ---
with open('app.js', 'r', encoding='utf-8') as f:
    app_js = f.read()

# Replace the CartoDB definition
carto_old = r"""    const darkLayer = L\.tileLayer\('https://\{s\}\.basemaps\.cartocdn\.com/dark_all/\{z\}/\{x\}/\{y\}\{r\}\.png', \{\s*attribution: '&copy; OpenStreetMap &copy; CARTO'\s*\}\)\.addTo\(map\);"""
carto_new = """    const darkLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);"""

app_js = re.sub(carto_old, carto_new, app_js)

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(app_js)

# --- 2. Patch style.css for Motion System ---
with open('style.css', 'r', encoding='utf-8') as f:
    css = f.read()

# Remove the old transition from inputs and buttons if present to avoid conflicts, or just let the unified block override it.
# Actually, I'll just append the unified block at the end of style.css

unified_motion_css = """
/* ========================================================
   SECTION 7: Unified Interactive Motion System
   ======================================================== */
button,
.persona-btn,
#send-btn,
#export-btn,
.toggle-label,
.trace-header,
#chat-input {
    transition: transform var(--transition-fast) var(--ease-curve), 
                filter var(--transition-fast) var(--ease-curve), 
                box-shadow var(--transition-fast) var(--ease-curve), 
                background-color var(--transition-fast) var(--ease-curve), 
                border-color var(--transition-fast) var(--ease-curve), 
                color var(--transition-fast) var(--ease-curve) !important;
    will-change: transform, filter;
}

button:hover,
.persona-btn:hover,
#send-btn:hover,
#export-btn:hover,
.toggle-label:hover,
.trace-header:hover,
#chat-input:hover,
#chat-input:focus {
    transform: translateY(-2px);
    filter: brightness(1.15);
}

button:active,
.persona-btn:active,
#send-btn:active,
#export-btn:active,
.toggle-label:active,
.trace-header:active {
    transform: translateY(1px);
    filter: brightness(0.9);
}
"""

css += unified_motion_css

with open('style.css', 'w', encoding='utf-8') as f:
    f.write(css)

print("Patch applied successfully.")
