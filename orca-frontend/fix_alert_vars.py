import re

with open('style.css', 'r', encoding='utf-8') as f:
    css = f.read()

# Replace hardcoded --status- variables with --alert-
css = css.replace('--status-safe', '--alert-safe')
css = css.replace('--status-caution', '--alert-caution')
css = css.replace('--status-nogo', '--alert-nogo')
css = css.replace('--status-unknown', '--alert-unknown')

# Fix hardcoded rgba backgrounds for statuses
css = re.sub(r'background-color: rgba\(6, 214, 160, 0\.1\);', 'background-color: rgba(92, 140, 163, 0.1);', css) # safe
css = re.sub(r'background-color: rgba\(255, 209, 102, 0\.1\);', 'background-color: rgba(255, 215, 0, 0.1);', css) # caution
css = re.sub(r'background-color: rgba\(239, 71, 111, 0\.1\);', 'background-color: rgba(216, 27, 96, 0.1);', css) # nogo

with open('style.css', 'w', encoding='utf-8') as f:
    f.write(css)
