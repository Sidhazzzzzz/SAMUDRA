const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch({ headless: "new" });
    const page = await browser.newPage();
    
    // We expect errors because the URL is broken, so we suppress them
    page.on('console', msg => {
        if (msg.type() !== 'error') {
            console.log('PAGE LOG:', msg.text());
        }
    });
    
    await page.goto('http://localhost:8080', { waitUntil: 'networkidle0' });
    
    // Wait for timeouts (we set timeoutMs = 5000)
    await new Promise(r => setTimeout(r, 6000));
    
    const errors = await page.evaluate(() => {
        const errs = Array.from(document.querySelectorAll('.layer-error'));
        return errs.map(e => e.parentElement.textContent.trim());
    });
    
    console.log("Found layer errors for:", errors);
    
    await browser.close();
})();
