import re

with open('style.css', 'r', encoding='utf-8') as f:
    css = f.read()

# Replace send-btn old block
send_old = r"""#send-btn \{
    background-color: var\(--accent-marine\);
    color: var\(--text-main\);
    border: none;
    padding: 0 20px;
    font-family: var\(--font-heading\);
    cursor: pointer;
    border-radius: 3px;
    transition: background-color 0\.2s;
\}
#send-btn:hover \{
    background-color: var\(--text-muted\);
    color: var\(--bg-navy\);
\}
#send-btn:disabled \{
    opacity: 0\.5;
    cursor: not-allowed;
\}"""
send_new = """/* Primary Buttons */
.primary-btn {
    background: linear-gradient(135deg, var(--accent-marine), #4A90E2);
    color: #ffffff !important;
    border: none;
    padding: 10px 20px;
    font-family: var(--font-heading);
    font-weight: 600;
    letter-spacing: 0.5px;
    cursor: pointer;
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    position: relative;
    overflow: hidden;
    width: 100%;
}
.primary-btn::after {
    content: '';
    position: absolute;
    top: 0; left: -100%; width: 50%; height: 100%;
    background: linear-gradient(to right, transparent, rgba(255,255,255,0.2), transparent);
    transform: skewX(-20deg);
    transition: all 0.5s ease;
}
.primary-btn:hover::after {
    left: 150%;
}
.primary-btn:hover {
    box-shadow: 0 6px 16px rgba(58, 80, 107, 0.6);
}
.primary-btn:disabled {
    background: var(--text-muted);
    opacity: 0.5;
    cursor: not-allowed;
    box-shadow: none;
}
.primary-btn:disabled::after {
    display: none;
}
#send-btn { width: auto; padding: 0 24px; }
#export-btn { margin-top: 5px; }
"""
css = re.sub(send_old, send_new, css, flags=re.MULTILINE)

# Replace persona switcher block
persona_old = r"""/\* Persona Switcher \*/
\.persona-switcher \{
    display: flex;
    gap: 10px;
    padding: 10px 20px;
    background: var\(--bg-navy\);
    border-bottom: 1px solid var\(--accent-marine\);
\}
\.persona-btn \{
    flex: 1;
    padding: 6px;
    background: transparent;
    border: 1px solid var\(--text-muted\);
    color: var\(--text-muted\);
    border-radius: 4px;
    cursor: pointer;
    font-size: 0\.8rem;
    font-family: var\(--font-main\);
    text-transform: uppercase;
    transition: all 0\.2s ease;
\}
\.persona-btn:hover \{
    border-color: var\(--text-main\);
    color: var\(--text-main\);
\}
\.persona-btn\.active \{
    background: var\(--accent-marine\);
    color: var\(--bg-dark\);
    border-color: var\(--accent-marine\);
    font-weight: 700;
\}"""
persona_new = """/* Persona Switcher */
.persona-switcher {
    display: flex;
    gap: 4px;
    padding: 6px;
    margin: 10px 20px;
    background: rgba(0, 0, 0, 0.3);
    border-radius: 8px;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.2);
}
.persona-btn {
    flex: 1;
    padding: 8px;
    background: transparent;
    border: none;
    color: var(--text-muted);
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.8rem;
    font-weight: 600;
    font-family: var(--font-heading);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    transition: all var(--transition-medium) var(--ease-curve);
}
.persona-btn:hover {
    color: var(--text-main);
    background: rgba(255, 255, 255, 0.05);
}
.persona-btn.active {
    background: var(--bg-panel);
    color: #ffffff;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    border: 1px solid rgba(255,255,255,0.1);
}"""
css = re.sub(persona_old, persona_new, css, flags=re.MULTILINE)

with open('style.css', 'w', encoding='utf-8') as f:
    f.write(css)
