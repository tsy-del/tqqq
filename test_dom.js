const fs = require('fs');
const html = fs.readFileSync('curr.html', 'utf8');

// Mock fetch
global.fetch = async (url) => {
    console.log("Fetch called:", url);
    return {
        json: async () => {
            if (url.includes('TQQQ')) return { c: 100, dp: 2.5 };
            if (url.includes('SOXL')) return { c: 50, dp: 1.5 };
            if (url.includes('SPCH')) return { c: 10, dp: 0.5 };
            return {};
        }
    };
};

const dom = new (require('jsdom').JSDOM)(html, { runScripts: "dangerously" });
setTimeout(() => {
    console.log("Val:", dom.window.document.getElementById('summary-total-value').textContent);
    console.log("Profit:", dom.window.document.getElementById('summary-total-profit').textContent);
    console.log("LIVE:", dom.window.document.getElementById('live-indicator').style.display);
}, 2000);
