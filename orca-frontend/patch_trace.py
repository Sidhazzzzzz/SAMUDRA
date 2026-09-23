import re

with open('app.js', 'r', encoding='utf-8') as f:
    content = f.read()

trace_old = r"traceData\.forEach\(step => \{\n\s*const li = document\.createElement\('li'\);"
trace_new = "traceData.forEach((step, index) => {\n            const li = document.createElement('li');"
content = re.sub(trace_old, trace_new, content)

append_old = r"li\.appendChild\(summaryDiv\);\n\s*traceList\.appendChild\(li\);\n\s*\}\);"
append_new = "li.appendChild(summaryDiv);\n            traceList.appendChild(li);\n            setTimeout(() => { li.classList.add('visible'); }, 100 + (index * 200));\n        });"
content = re.sub(append_old, append_new, content)

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(content)
