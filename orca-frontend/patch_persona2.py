import re

with open('app.js', 'r', encoding='utf-8') as f:
    content = f.read()

persona_old = r"""            const title = document\.getElementById\('persona-title'\);
            if \(currentMode === "commercial"\) \{
                title\.textContent = "COMMERCIAL NAVIGATOR";
                chatInput\.placeholder = "e\.g\., plan a commercial route from Rameswaram to Mandapam\.\.\.";
            \} else \{
                title\.textContent = "FISHERMAN PORTAL";
                chatInput\.placeholder = "Enter coordinates, mission, or ask for a route\.\.\.";
            \}"""

persona_new = """            const title = document.getElementById('persona-title');
            const headerTitle = document.querySelector('.sidebar-header h1');
            headerTitle.classList.add('persona-switching');
            chatInput.classList.add('persona-switching');
            
            setTimeout(() => {
                if (currentMode === "commercial") {
                    title.textContent = "COMMERCIAL NAVIGATOR";
                    chatInput.placeholder = "e.g., plan a commercial route from Rameswaram to Mandapam...";
                } else {
                    title.textContent = "FISHERMAN PORTAL";
                    chatInput.placeholder = "Enter coordinates, mission, or ask for a route...";
                }
                headerTitle.classList.remove('persona-switching');
                chatInput.classList.remove('persona-switching');
            }, 300);"""

content = re.sub(persona_old, persona_new, content)

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(content)
