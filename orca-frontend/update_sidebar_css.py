import re

with open('style.css', 'r', encoding='utf-8') as f:
    css = f.read()

# Add spacing variables
if '--space-sm' not in css:
    css = css.replace(':root {', ':root {\n    --space-sm: 8px;\n    --space-md: 16px;\n    --space-lg: 24px;')

# Remove old verdict-panel and trace-container CSS (we will replace it)
css = re.sub(r'\#verdict-panel\s*\{[^}]*\}', '', css, flags=re.DOTALL)
css = re.sub(r'\.verdict-header\s*\{[^}]*\}', '', css, flags=re.DOTALL)
css = re.sub(r'\.verdict-title\s*\{[^}]*\}', '', css, flags=re.DOTALL)
css = re.sub(r'\.verdict-reason\s*\{[^}]*\}', '', css, flags=re.DOTALL)

# Let's just append the new layout CSS
layout_css = """
/* ========================================================
   SECTION 9: SIDEBAR LAYOUT & GROUPING
   ======================================================== */
.sidebar {
    display: flex;
    flex-direction: column;
    height: 100vh;
    padding: var(--space-md);
    gap: var(--space-md);
    box-sizing: border-box;
}
.sidebar-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: transparent;
    padding: 0;
    border-bottom: none;
}
.sidebar-header {
    padding: 0;
    background: transparent;
    border-bottom: none;
}
.sidebar-header h1 {
    margin: 0;
}
.persona-switcher {
    margin: 0;
    width: 200px; /* compact */
}
.sidebar-status-card {
    background-color: var(--bg-panel);
    border-radius: 12px;
    padding: var(--space-md);
    border: 1px solid rgba(255, 255, 255, 0.05);
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}
.status-row {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
}
.status-label {
    font-family: var(--font-heading);
    font-size: 0.8rem;
    font-weight: 700;
    color: var(--text-muted);
    letter-spacing: 0.5px;
}
.status-divider {
    height: 1px;
    background: rgba(255, 255, 255, 0.1);
    margin: var(--space-sm) 0;
}
.verdict-reason {
    font-size: 0.9rem;
    color: var(--text-main);
    line-height: 1.4;
}
.secondary-btn-style {
    background: transparent;
    border: 1px solid var(--accent-marine);
    color: var(--accent-marine) !important;
}
.secondary-btn-style:hover {
    background: rgba(58, 107, 140, 0.1);
}

.chat-history {
    flex: 1;
    overflow-y: auto;
    padding: 0;
    padding-right: 5px; /* for scrollbar */
    margin-bottom: 0;
}
.chat-history::-webkit-scrollbar {
    width: 6px;
}
.chat-history::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.2);
    border-radius: 3px;
}
.chat-input-area {
    margin-top: auto;
    background: var(--bg-navy);
    border-radius: 12px;
    padding: var(--space-sm);
    border: 1px solid rgba(255,255,255,0.05);
}
.export-advisory-btn {
    margin-top: var(--space-sm);
    width: 100%;
    font-size: 0.8rem;
    padding: 8px 16px;
}
"""
css += layout_css

with open('style.css', 'w', encoding='utf-8') as f:
    f.write(css)
