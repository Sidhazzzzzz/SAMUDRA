import re

with open('style.css', 'r', encoding='utf-8') as f:
    css = f.read()

# 1. Update CSS Variables back to dark theme
variables_old = r""":root \{
    /\* Admiralty Chart Conventions \*/
    --bg-dark: #EAE3DA;      /\* Replaces old dark background with tan/buff \(Land\) \*/
    --bg-navy: #F4EFEA;      /\* Base sidebar background \(Buff\) \*/
    --bg-panel: #FDFBF7;     /\* Bright card background \(White-ish buff\) \*/
    
    --text-main: #111111;    /\* Chart-black for linework and text \*/
    --text-muted: #555555;   
    
    --accent-marine: #3A6B8C; /\* Depth-banded blue \(medium deep\) \*/
    --accent-marine-glow: rgba\(58, 107, 140, 0\.3\);"""

variables_new = """:root {
    /* Admiralty Chart Conventions (Only for Map / Accents / Modal) */
    --accent-marine: #3A6B8C;
    --accent-marine-glow: rgba(58, 107, 140, 0.3);

    /* Dark Theme Base */
    --bg-dark: #0B101E;
    --bg-navy: #151B2B;
    --bg-panel: #1C2541;
    
    --text-main: #FFFFFF;
    --text-muted: #8D99AE;"""

css = re.sub(variables_old, variables_new, css)

# 2. Fix Modal background and text explicitly to Admiralty Light theme
# Since the global text is white now, and global bg is dark, we need to override the modal specifically
modal_css_old = r"""\.dag-modal-content \{
    background: var\(--bg-panel\);"""
modal_css_new = """.dag-modal-content {
    background: #FDFBF7;
    color: #111111;"""
css = re.sub(modal_css_old, modal_css_new, css)

# Fix modal h2
css = css.replace('.dag-modal-content h2 {\n    font-family: var(--font-heading);\n    color: var(--text-main);', '.dag-modal-content h2 {\n    font-family: var(--font-heading);\n    color: #111111;')

# Fix node text colors
css = css.replace('color: var(--text-main);\n    text-align: center;\n    text-transform: uppercase;\n}', 'color: #111111;\n    text-align: center;\n    text-transform: uppercase;\n}')
css = css.replace('.dag-node-time {\n    font-family: monospace;\n    font-size: 0.7rem;\n    color: var(--text-muted);', '.dag-node-time {\n    font-family: monospace;\n    font-size: 0.7rem;\n    color: #555555;')
css = css.replace('.dag-node-summary {\n    font-size: 0.65rem;\n    color: var(--text-muted);', '.dag-node-summary {\n    font-size: 0.65rem;\n    color: #555555;')
css = css.replace('background: var(--bg-panel);\n    border: 3px solid #DDDDDD;', 'background: #FDFBF7;\n    border: 3px solid #DDDDDD;')

# 3. Fix input background (I changed it to #FFFFFF earlier)
css = css.replace('background-color: #FFFFFF;\n    color: var(--text-main);\n    border: 1px solid #CCCCCC;', 'background-color: #0B101E;\n    color: #FFFFFF;\n    border: 1px solid #1C2541;')
css = css.replace('background-color: #F8F4F0;', 'background-color: #1C2541;')

# Also the .persona-switcher container
css = css.replace('background-color: #FFFFFF;\n    border: 1px solid #CCCCCC;', 'background-color: #0B101E;\n    border: 1px solid #1C2541;')

# And the hover states for persona
css = css.replace('rgba(0, 0, 0, 0.04)', 'rgba(255, 255, 255, 0.04)')
css = css.replace('rgba(0, 0, 0, 0.05)', 'rgba(255, 255, 255, 0.05)')

with open('style.css', 'w', encoding='utf-8') as f:
    f.write(css)
