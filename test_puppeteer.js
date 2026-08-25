const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    page.on('console', msg => console.log('PAGE LOG:', msg.text()));
    page.on('pageerror', err => console.log('PAGE ERROR:', err.message));
    await page.goto('https://tsy-del.github.io/tqqq/', {waitUntil: 'networkidle0'});
    
    // Check if chart was rendered
    const hasCanvas = await page.evaluate(() => {
        const container = document.getElementById('chart-container');
        return container ? container.querySelectorAll('canvas').length > 0 : false;
    });
    console.log("Has canvas:", hasCanvas);
    
    await browser.close();
})();
