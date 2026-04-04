import puppeteer from 'puppeteer';

(async () => {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();

    page.on('pageerror', err => {
        console.log('PAGE ERROR:', err.toString());
    });

    page.on('console', msg => {
        if (msg.type() === 'error') {
            const loc = msg.location();
            console.log(`CONSOLE ERROR at line ${loc.lineNumber}, col ${loc.columnNumber}:`, msg.text());
        }
    });

    try {
        await page.goto('http://127.0.0.1:8000', { waitUntil: 'networkidle0', timeout: 5000 });
    } catch (e) { }

    // Wait to see if error triggers
    await new Promise(r => setTimeout(r, 1000));
    await browser.close();
})();
