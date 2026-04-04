import puppeteer from 'puppeteer';

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();

  // Capture console errors with full details
  page.on('pageerror', err => {
    console.log('PAGE ERROR:', err.toString());
    if (err.stack) console.log('STACK:', err.stack.substring(0, 500));
  });
  page.on('console', msg => {
    if (msg.type() === 'error') console.log('CONSOLE ERROR:', msg.text());
  });

  // Listen for request failures
  page.on('requestfailed', req => console.log('REQUEST FAILED:', req.url()));

  try {
    const response = await page.goto('http://127.0.0.1:8000', { waitUntil: 'domcontentloaded', timeout: 10000 });
    console.log('Status:', response.status());

    // Try to get JS error line by evaluating a snippet
    await page.waitForTimeout(1000);

    // Check what actually loaded in window
    const result = await page.evaluate(() => {
      return {
        hasAPI: typeof API !== 'undefined',
        hasSendChat: typeof sendChat !== 'undefined',
        hasLoadSessions: typeof loadSessions !== 'undefined',
        error: typeof lastError !== 'undefined' ? lastError : 'none'
      };
    }).catch(e => ({ evalError: e.message }));

    console.log('Window state:', JSON.stringify(result));

    await page.screenshot({ path: '/Users/azan/.gemini/antigravity/brain/ef912fcf-0197-4a0a-90c8-3a9c5a968fc0/debug_screenshot.png' });
    console.log('Screenshot saved');

  } catch (e) {
    console.error('Navigation error:', e.message);
  }

  await browser.close();
})();
