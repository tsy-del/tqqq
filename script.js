async function fetchTQQQPrice() {
    const priceEl = document.getElementById('tqqq-price');
    const changeEl = document.getElementById('price-change');
    const updateEl = document.getElementById('last-update');

    // 方案 1: 本地 API (yfinance)
    try {
        console.log("嘗試連接本地 API...");
        const response = await fetch('http://localhost:5001/api/tqqq');
        if (response.ok) {
            const data = await response.json();
            priceEl.innerText = data.price.toFixed(2);
            changeEl.innerText = `${data.change > 0 ? '+' : ''}${data.change}%`;
            changeEl.className = `change ${data.change >= 0 ? 'up' : 'down'}`;
            updateEl.innerText = new Date().toLocaleTimeString() + " (yfinance)";
            return;
        }
    } catch (e) {
        console.log("本地 API 未就緒或連線失敗。");
    }

    // 方案 2: 直接使用 Yahoo Finance Query API (透過跨域 Proxy 或直接嘗試)
    // 註：有些瀏覽器環境下直接訪問此 URL 會被 CORS 阻擋
    try {
        console.log("嘗試連接 Yahoo 公開接口...");
        const symbol = 'TQQQ';
        // 使用一個常見的 CORS Proxy (如果這也不行，我們還有方案 3)
        const response = await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?interval=1m&range=1d`);
        const data = await response.json();
        const result = data.chart.result[0];
        const price = result.meta.regularMarketPrice;
        const prevClose = result.meta.previousClose;
        const change = ((price - prevClose) / prevClose * 100).toFixed(2);

        priceEl.innerText = price.toFixed(2);
        changeEl.innerText = `${change > 0 ? '+' : ''}${change}%`;
        changeEl.className = `change ${change >= 0 ? 'up' : 'down'}`;
        updateEl.innerText = new Date().toLocaleTimeString() + " (Yahoo)";
        return;
    } catch (e) {
        console.log("Yahoo 直接連線失敗。");
    }

    // 方案 3: Finnhub (最穩定的備援，無需 Proxy)
    try {
        console.log("嘗試連接 Finnhub...");
        const response = await fetch(`https://finnhub.io/api/v1/quote?symbol=TQQQ&token=cvv7re9r01qge7i86j80cvv7re9r01qge7i86j8g`);
        const data = await response.json();
        if (data && data.c) {
            const price = data.c;
            const prevClose = data.pc;
            const change = (((price - prevClose) / prevClose) * 100).toFixed(2);
            priceEl.innerText = price.toFixed(2);
            changeEl.innerText = `${change > 0 ? '+' : ''}${change}%`;
            changeEl.className = `change ${change >= 0 ? 'up' : 'down'}`;
            updateEl.innerText = new Date().toLocaleTimeString() + " (Finnhub)";
            return;
        }
    } catch (e) {
        priceEl.innerText = "連線失敗";
        updateEl.innerText = "請檢查網絡";
    }
}

fetchTQQQPrice();
setInterval(fetchTQQQPrice, 60000);