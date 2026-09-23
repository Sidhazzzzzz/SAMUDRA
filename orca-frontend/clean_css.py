import re

with open('style.css', 'r', encoding='utf-8') as f:
    css = f.read()

# Remove the old .primary-btn block and everything after it
# First, let's find where .primary-btn starts
if '/* Primary Buttons (Transmit, Export) */' in css:
    css = css[:css.index('/* Primary Buttons (Transmit, Export) */')]
elif '/* Primary Buttons */' in css:
    css = css[:css.index('/* Primary Buttons */')]

# Also remove the persona switcher from wherever it is.
persona_pattern = r'/\* Persona Switcher \*/.*?\.persona-btn\.active\s*\{[^}]*\}'
css = re.sub(persona_pattern, '', css, flags=re.DOTALL)

# Remove old #chat-input styles
chat_input_pattern = r'#chat-input\s*\{[^}]*\}\s*#chat-input:focus\s*\{[^}]*\}'
css = re.sub(chat_input_pattern, '', css, flags=re.DOTALL)

# Remove old #send-btn styles if they exist
send_btn_pattern = r'#send-btn\s*\{[^}]*\}\s*#send-btn:hover\s*\{[^}]*\}\s*#send-btn:disabled\s*\{[^}]*\}'
css = re.sub(send_btn_pattern, '', css, flags=re.DOTALL)

# Remove any trace of SECTION 7 Unified motion system
motion_pattern = r'/\*\s*={40,}\s*SECTION 7:.*?(?=\/\*|$)'
css = re.sub(motion_pattern, '', css, flags=re.DOTALL)

with open('style.css', 'w', encoding='utf-8') as f:
    f.write(css)

print("Cleaned up CSS.")
