import re

with open('app.js', 'r', encoding='utf-8') as f:
    content = f.read()

persona_old = r"if \(currentMode === 'commercial'\) \{\s*personaTitle\.textContent = 'COMMERCIAL NAVIGATOR';\s*chatInput\.placeholder = \"Enter origin and destination ports\.\.\.\";\s*\} else \{\s*personaTitle\.textContent = 'FISHERMAN PORTAL';\s*chatInput\.placeholder = \"Enter coordinates, mission, or ask for a route\.\.\.\";\s*\}"

persona_new = """const headerTitle = document.querySelector('.sidebar-header h1');
        headerTitle.classList.add('persona-switching');
        chatInput.classList.add('persona-switching');
        
        setTimeout(() => {
            if (currentMode === 'commercial') {
                personaTitle.textContent = 'COMMERCIAL NAVIGATOR';
                chatInput.placeholder = "Enter origin and destination ports...";
            } else {
                personaTitle.textContent = 'FISHERMAN PORTAL';
                chatInput.placeholder = "Enter coordinates, mission, or ask for a route...";
            }
            headerTitle.classList.remove('persona-switching');
            chatInput.classList.remove('persona-switching');
        }, 300);"""

content = re.sub(persona_old, persona_new, content)

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(content)
