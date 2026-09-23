import re

with open('style.css', 'r', encoding='utf-8') as f:
    css = f.read()

# Fix .dag-node.active .dag-node-circle text color
pattern = r'(\.dag-node\.active \.dag-node-circle\s*\{[^}]*)color:\s*var\(--text-main\);([^}]*\})'
css = re.sub(pattern, r'\1color: #FFFFFF;\2', css)

# Make sure persona button active text color is good (currently #202124 on --accent-marine)
# Let's change .persona-btn.active color to #FFFFFF
pattern2 = r'(\.persona-btn\.active\s*\{[^}]*)color:\s*#202124;([^}]*\})'
css = re.sub(pattern2, r'\1color: #FFFFFF;\2', css)

# Wait, check #chat-input hover/focus background.
# I set it to #FFFFFF initially, but hover is #28292C.
css = css.replace('background-color: #28292C;', 'background-color: #F8F4F0;')

with open('style.css', 'w', encoding='utf-8') as f:
    f.write(css)
