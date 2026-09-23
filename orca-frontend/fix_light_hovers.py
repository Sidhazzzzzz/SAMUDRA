import re

with open('style.css', 'r', encoding='utf-8') as f:
    css = f.read()

# Replace white semi-transparent with black semi-transparent for light theme hovers
css = css.replace('rgba(255, 255, 255, 0.04)', 'rgba(0, 0, 0, 0.04)')
css = css.replace('rgba(255, 255, 255, 0.05)', 'rgba(0, 0, 0, 0.05)')

# Update the persona switcher container background
# It was background-color: #FFFFFF; border: 1px solid #CCCCCC;
# That's fine for light theme.

with open('style.css', 'w', encoding='utf-8') as f:
    f.write(css)
