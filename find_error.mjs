import puppeteer from 'puppeteer';
import http from 'http';

(async () => {
    // Fetch HTML from localhost:8000
    const fetch_html = () => new Promise(resolve => {
        http.get('http://127.0.0.1:8000', res => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve(data));
        });
    });

    const html = await fetch_html();
    const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/);
    if (!scriptMatch) { console.log('No script found'); process.exit(1); }

    const js = scriptMatch[1];
    const lines = js.split('\n');
    console.log(`Extracted ${lines.length} lines of JS`);

    const browser = await puppeteer.launch();
    const page = await browser.newPage();

    let lo = 0, hi = lines.length;
    while (lo < hi - 1) {
        const mid = Math.floor((lo + hi) / 2);
        const chunk = lines.slice(0, mid).join('\n');
        let hasError = false;
        try {
            await page.evaluate((code) => {
                new Function(code);
            }, chunk);
        } catch (e) {
            if (e.message.includes('SyntaxError')) {
                hasError = true;
            }
        }
        if (hasError) hi = mid; else lo = mid;
    }

    console.log(`Error is between line ${lo} and ${hi}`);
    const errLine = hi - 1;
    console.log(`Line ${errLine}:`, lines[errLine]);
    if (errLine > 0) console.log(`Context:\n ${lines[errLine - 1]}\n ${lines[errLine]}\n ${lines[errLine + 1]}`);

    await browser.close();
})();
