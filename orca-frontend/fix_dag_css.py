import re

with open('style.css', 'r', encoding='utf-8') as f:
    css = f.read()

css = css.replace('.dag-node.error .dag-node-circle', '.dag-node.active.error .dag-node-circle')
css = css.replace('.dag-node.fallback .dag-node-circle', '.dag-node.active.fallback .dag-node-circle')

# Make sure icons are centered properly in the circle
css = css.replace('.dag-node-circle {\n    width: 32px; height: 32px;', '.dag-node-circle {\n    width: 40px; height: 40px;\n    font-size: 1.2rem;')

with open('style.css', 'w', encoding='utf-8') as f:
    f.write(css)
