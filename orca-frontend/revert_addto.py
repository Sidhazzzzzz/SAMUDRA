with open('app.js', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("pane: 'sstPane'\n    });", "pane: 'sstPane'\n    }).addTo(map);")
content = content.replace("pane: 'chlPane'\n    });", "pane: 'chlPane'\n    }).addTo(map);")

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(content)
