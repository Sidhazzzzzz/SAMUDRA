with open('app.js', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("pane: 'sstPane'\n    }).addTo(map);", "pane: 'sstPane'\n    });")
content = content.replace("pane: 'chlPane'\n    }).addTo(map);", "pane: 'chlPane'\n    });")

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(content)
