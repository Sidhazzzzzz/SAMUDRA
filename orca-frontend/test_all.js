const puppeteer = require('puppeteer');
const http = require('http');
const fs = require('fs');
const path = require('path');

const server = http.createServer((req, res) => {
    let filePath = '.' + req.url;
    if (filePath == './') filePath = './index.html';
    const extname = path.extname(filePath);
    let contentType = 'text/html';
    switch (extname) {
        case '.js': contentType = 'text/javascript'; break;
        case '.css': contentType = 'text/css'; break;
    }
    fs.readFile(filePath, (error, content) => {
        if (error) {
            res.writeHead(500); res.end('Error');
        } else {
            res.writeHead(200, { 'Content-Type': contentType });
            res.end(content, 'utf-8');
        }
    });
});

server.listen(8081, async () => {
    try {
        const browser = await puppeteer.launch({ headless: "new" });
        const page = await browser.newPage();
        let errorCount = 0;
        page.on('pageerror', e => { console.error('PAGE ERROR:', e); errorCount++; });
        page.on('console', msg => { if(msg.type() === 'error') { console.error('CONSOLE ERROR:', msg.text()); errorCount++; } });
        
        await page.goto('http://127.0.0.1:8081', { waitUntil: 'networkidle0' });
        
        // Check persona text
        const title = await page.$eval('#persona-title', el => el.textContent);
        console.log("Initial Persona Title:", title);
        
        // Click commercial mode
        await page.click('button[data-mode="commercial"]');
        await new Promise(r => setTimeout(r, 500));
        const newTitle = await page.$eval('#persona-title', el => el.textContent);
        console.log("New Persona Title:", newTitle);
        
        console.log("Total errors:", errorCount);
        
        await browser.close();
        server.close();
    } catch(e) {
        console.error("Test failed", e);
        server.close();
    }
});
