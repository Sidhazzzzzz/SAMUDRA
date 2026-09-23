import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Remove the old trace-container from the sidebar
trace_old = r'<div class="trace-container">.*?</div>\s*</div>'
# Wait, regex for nested divs is tricky. Let's just use string replace.
trace_str = """            <div class="trace-container">
                <div class="trace-header" id="trace-toggle">
                    <span>SYSTEM TRACE (DAG)</span>
                    <span id="trace-icon">▼</span>
                </div>
                <div class="trace-content hidden" id="trace-content">
                    <ul id="trace-list"></ul>
                </div>
            </div>"""

html = html.replace(trace_str, """            <div class="trace-container">
                <button type="button" class="primary-btn" id="trace-toggle" style="width: 100%; margin-top: 10px;">VIEW SYSTEM TRACE (DAG)</button>
            </div>""")

# 2. Inject the modal at the end of the body
modal_str = """
    <!-- Full-screen DAG Modal -->
    <div id="dag-modal" class="dag-modal hidden">
        <div class="dag-modal-content">
            <button id="dag-close-btn" class="dag-close-btn">&times;</button>
            <h2>SYSTEM TRACE (DAG)</h2>
            <div class="dag-pipeline-container">
                <div class="dag-line-bg"></div>
                <div class="dag-line-fill" id="dag-line-fill"></div>
                <div class="dag-nodes" id="dag-nodes">
                    <!-- Nodes injected here -->
                </div>
            </div>
        </div>
    </div>
"""

html = html.replace('<!-- Custom JS -->', modal_str + '\n    <!-- Custom JS -->')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
