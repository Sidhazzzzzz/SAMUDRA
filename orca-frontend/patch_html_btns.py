import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Clean up Export button
export_old = r"""<button id="export-btn" class="hidden" style="width: 100%; padding: 8px; background-color: var\(--accent-marine\); color: var\(--bg-dark\); border: none; border-radius: 4px; font-weight: bold; cursor: pointer;">Export Advisory \(PDF\)</button>"""
export_new = """<button id="export-btn" class="hidden primary-btn">Export Advisory (PDF)</button>"""
html = re.sub(export_old, export_new, html)

# 2. Add primary-btn to Transmit button
send_old = r"""<button type="submit" id="send-btn">TRANSMIT</button>"""
send_new = """<button type="submit" id="send-btn" class="primary-btn">TRANSMIT</button>"""
html = re.sub(send_old, send_new, html)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
