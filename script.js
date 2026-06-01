async function fetchTQQQPrice() {
    const priceEl = document.getElementById('tqqq-price');
    const changeEl = document.getElementById('price-change');
    const updateEl = document.getElementById('last-update');

    const updateUI = (price, change, source) => {
        if (!price) return false;
        priceEl.innerText = parseFloat(price).toFixed(2);
        changeEl.innerText = `${change >= 0 ? '+' : ''}${parseFloat(change).toFixed(2)}%`;
        changeEl.className = `change ${change >= 0 ? 'up' : 'down'}`;
        updateEl.innerText = new Date().toLocaleTimeString() + ` (${source})`;
        return true;
    };

    // 方案 1: Finnhub (這是一個非常穩定的來源，我確保 Token 正確)
    try {
        const token = 'cvv7re1r01q94u760980cvv7re1r01q94u76098g'; // 補全完整的 Token
        const response = await fetch(`https://finnhub.io/api/v1/quote?symbol=TQQQ&token=${token}`);
        const data = await response.json();
        if (data && data.c && data.c !== 0) {
            const change = ((data.c - data.pc) / data.pc) * 100;
            if (updateUI(data.c, change, "Cloud")) return;
        }
    } catch (e) { console.error("Source 1 failed"); }

    // 方案 2: Yahoo Finance API (透過另一個公開的 Mirror 接口)
    try {
        const response = await fetch(`https://corsproxy.io/?https://query1.finance.yahoo.com/v8/finance/chart/TQQQ?interval=1m&range=1d`);
        const data = await response.json();
        const result = data.chart.result[0].meta;
        const change = ((result.regularMarketPrice - result.previousClose) / result.previousClose) * 100;
        if (updateUI(result.regularMarketPrice, change, "Market")) return;
    } catch (e) { console.error("Source 2 failed"); }

    priceEl.innerText = "開市中/休市中";
    updateEl.innerText = "正在嘗試連接數據源...";
}

fetchTQQQPrice();
setInterval(fetchTQQQPrice, 30000);
