const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch({ headless: "new" });
    const page = await browser.newPage();
    
    page.on('console', msg => {
        console.log(`[${msg.type()}] ${msg.text()}`);
    });
    
    page.on('pageerror', error => {
        console.log('[PAGE ERROR]', error.message);
    });

    try {
        await page.goto('http://127.0.0.1:8080', { waitUntil: 'networkidle0', timeout: 5000 });
    } catch(e) {
        console.log("Nav timeout or error", e);
    }
    
    await browser.close();
})();
