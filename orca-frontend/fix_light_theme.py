import re

with open('style.css', 'r', encoding='utf-8') as f:
    css = f.read()

# Fix gauge circles
css = css.replace('stroke: rgba(255, 255, 255, 0.1);', 'stroke: rgba(0, 0, 0, 0.1);')

# Fix text colors for gauges
css = css.replace('color: white;', 'color: var(--text-main);')
css = css.replace('color: #E8EAED;', 'color: var(--text-main);')
css = css.replace('color: #FFF;', 'color: var(--text-main);')

# We don't want to replace *every* color: #FFF, for example .primary-btn uses #FFF for text.
# Let's target .primary-btn specifically to ensure it stays readable.
css = css.replace('color: var(--text-main) !important; /* High contrast text */', 'color: #FFFFFF !important;')

with open('style.css', 'w', encoding='utf-8') as f:
    f.write(css)
