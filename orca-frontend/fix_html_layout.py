import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Remove inline padding for export button div
export_div_old = r'<div style="padding: 10px 20px;">\s*<button id="export-btn" class="hidden primary-btn">Export Advisory \(PDF\)</button>\s*</div>'
export_div_new = """<div class="export-container">
                <button id="export-btn" class="hidden primary-btn">Export Advisory (PDF)</button>
            </div>"""

html = re.sub(export_div_old, export_div_new, html)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
