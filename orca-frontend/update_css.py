import re

with open('style.css', 'r', encoding='utf-8') as f:
    css = f.read()

# 1. Update CSS Variables
variables_old = r""":root \{
    --bg-dark: #0B101E;
    --bg-navy: #151B2B;
    --bg-panel: #1C2541;
    --text-main: #FFFFFF;
    --text-muted: #8D99AE;
    --accent-marine: #00B4D8;
    --accent-marine-glow: rgba\(0, 180, 216, 0\.3\);
    --transition-fast: 0\.2s;
    --transition-medium: 0\.4s;
    --transition-slow: 0\.8s;
    --ease-curve: cubic-bezier\(0\.4, 0, 0\.2, 1\);
\}"""

variables_new = """:root {
    /* Admiralty Chart Conventions */
    --bg-dark: #EAE3DA;      /* Replaces old dark background with tan/buff (Land) */
    --bg-navy: #F4EFEA;      /* Base sidebar background (Buff) */
    --bg-panel: #FDFBF7;     /* Bright card background (White-ish buff) */
    
    --text-main: #111111;    /* Chart-black for linework and text */
    --text-muted: #555555;   
    
    --accent-marine: #3A6B8C; /* Depth-banded blue (medium deep) */
    --accent-marine-glow: rgba(58, 107, 140, 0.3);
    
    --alert-safe: #5C8CA3;
    --alert-caution: #FFD700; /* Hazard yellow */
    --alert-nogo: #D81B60;    /* Chart magenta */
    --alert-unknown: #888888;
    
    --transition-fast: 0.2s;
    --transition-medium: 0.4s;
    --transition-slow: 0.8s;
    --ease-curve: cubic-bezier(0.4, 0, 0.2, 1);
}"""

if re.search(r':root\s*\{[^}]*\}', css):
    css = re.sub(r':root\s*\{[^}]*\}', variables_new, css)
else:
    css = variables_new + "\n" + css

# 2. Add DAG Modal Styles
modal_css = """
/* ========================================================
   SECTION 8: FULL-SCREEN DAG MODAL
   ======================================================== */
.dag-modal {
    position: fixed;
    top: 0; left: 0; width: 100vw; height: 100vh;
    background: rgba(17, 17, 17, 0.85); /* Dark overlay */
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    pointer-events: none;
    transition: opacity var(--transition-medium) var(--ease-curve);
    backdrop-filter: blur(4px);
}
.dag-modal.show {
    opacity: 1;
    pointer-events: auto;
}
.dag-modal-content {
    background: var(--bg-panel);
    width: 90%;
    max-width: 1000px;
    height: 80vh;
    border-radius: 12px;
    padding: 40px;
    position: relative;
    box-shadow: 0 10px 40px rgba(0,0,0,0.5);
    display: flex;
    flex-direction: column;
    transform: translateY(20px);
    transition: transform var(--transition-medium) var(--ease-curve);
}
.dag-modal.show .dag-modal-content {
    transform: translateY(0);
}
.dag-close-btn {
    position: absolute;
    top: 20px; right: 25px;
    background: none;
    border: none;
    font-size: 2rem;
    color: var(--text-muted);
    cursor: pointer;
    transition: color var(--transition-fast);
}
.dag-close-btn:hover {
    color: var(--alert-nogo); /* Magenta on hover to close */
}
.dag-modal-content h2 {
    font-family: var(--font-heading);
    color: var(--text-main);
    text-align: center;
    margin-top: 0;
    margin-bottom: 50px;
    letter-spacing: 2px;
}

/* Linear Pipeline */
.dag-pipeline-container {
    position: relative;
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 40px;
}
.dag-line-bg {
    position: absolute;
    top: 50%; left: 40px; right: 40px;
    height: 4px;
    background: #DDDDDD;
    transform: translateY(-50%);
    z-index: 1;
}
.dag-line-fill {
    position: absolute;
    top: 50%; left: 40px;
    height: 4px;
    background: var(--accent-marine); /* Blue filling line */
    transform: translateY(-50%);
    z-index: 2;
    width: 0%; /* Animates via JS */
    transition: width linear;
}
.dag-nodes {
    display: flex;
    justify-content: space-between;
    width: 100%;
    position: relative;
    z-index: 3;
}
.dag-node {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 100px;
    opacity: 0.3; /* Default unlit */
    transform: translateY(10px);
    transition: all var(--transition-medium) var(--ease-curve);
}
.dag-node.active {
    opacity: 1;
    transform: translateY(0);
}
.dag-node-circle {
    width: 32px; height: 32px;
    background: var(--bg-panel);
    border: 3px solid #DDDDDD;
    border-radius: 50%;
    margin-bottom: 15px;
    box-shadow: 0 0 0 rgba(0,0,0,0);
    transition: all var(--transition-medium) var(--ease-curve);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.7rem;
    font-weight: bold;
    color: transparent;
}
.dag-node.active .dag-node-circle {
    border-color: var(--accent-marine);
    background: var(--accent-marine);
    color: #FFF;
    box-shadow: 0 0 15px var(--accent-marine-glow);
}
/* If source is error, use magenta */
.dag-node.error .dag-node-circle {
    border-color: var(--alert-nogo);
    background: var(--alert-nogo);
    box-shadow: 0 0 15px rgba(216, 27, 96, 0.4);
}
/* If source is fallback, use caution yellow */
.dag-node.fallback .dag-node-circle {
    border-color: var(--alert-caution);
    background: var(--alert-caution);
    box-shadow: 0 0 15px rgba(255, 215, 0, 0.4);
    color: var(--text-main);
}
.dag-node-label {
    font-family: var(--font-heading);
    font-size: 0.8rem;
    font-weight: 700;
    color: var(--text-main);
    text-align: center;
    text-transform: uppercase;
}
.dag-node-time {
    font-family: monospace;
    font-size: 0.7rem;
    color: var(--text-muted);
    margin-top: 5px;
    text-align: center;
}
.dag-node-summary {
    font-size: 0.65rem;
    color: var(--text-muted);
    text-align: center;
    margin-top: 5px;
    max-width: 120px;
}
"""

if '/* ========================================================' not in modal_css:
    pass # Just to ensure no error
css += "\n" + modal_css

# Ensure osm-dark-filter is preserved
if '.osm-dark-filter' not in css:
    css += "\n.osm-dark-filter { filter: invert(100%) hue-rotate(180deg) brightness(95%) contrast(90%); }\n"

# Overhaul colors in the rest of the UI (Material 3 replacements)
# Chat input background #202124 -> #FFFFFF (Admiralty theme)
css = css.replace('background-color: #202124;', 'background-color: #FFFFFF;')
css = css.replace('color: #E8EAED;', 'color: var(--text-main);')
css = css.replace('border: 1px solid #3C4043;', 'border: 1px solid #CCCCCC;')
# Primary buttons #8AB4F8 -> var(--accent-marine)
css = css.replace('background-color: #8AB4F8;', 'background-color: var(--accent-marine);')
css = css.replace('color: #202124 !important;', 'color: #FFFFFF !important;')
# Primary btn hover #A8C7FA -> slightly darker marine
css = css.replace('background-color: #A8C7FA;', 'background-color: #4A86A8;')

with open('style.css', 'w', encoding='utf-8') as f:
    f.write(css)
