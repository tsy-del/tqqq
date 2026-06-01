async function fetchTQQQPrice() {
    const symbol = 'TQQQ';
    // 使用 Yahoo Finance 的公開 API (或是替代來源)
    // 註：這是一個常見的公開查詢方式，如果失效我們會換另一個
    try {
        const response = await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?interval=1m&range=1d`);
        const data = await response.json();
        const result = data.chart.result[0];
        const price = result.meta.regularMarketPrice;
        const prevClose = result.meta.previousClose;
        const change = ((price - prevClose) / prevClose * 100).toFixed(2);

        document.getElementById('tqqq-price').innerText = price.toFixed(2);
        
        const changeEl = document.getElementById('price-change');
        changeEl.innerText = `${change > 0 ? '+' : ''}${change}%`;
        changeEl.className = `change ${change >= 0 ? 'up' : 'down'}`;
        
        document.getElementById('last-update').innerText = new Date().toLocaleTimeString();
    } catch (error) {
        console.error('Fetch error:', error);
        document.getElementById('tqqq-price').innerText = '載入失敗';
    }
}

fetchTQQQPrice();
// 每 60 秒更新一次
setInterval(fetchTQQQPrice, 60000);