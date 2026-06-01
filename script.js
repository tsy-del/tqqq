async function fetchTQQQPrice() {
    const priceEl = document.getElementById('tqqq-price');
    const changeEl = document.getElementById('price-change');
    const updateEl = document.getElementById('last-update');

    // 通用的渲染函數
    const updateUI = (price, change, source) => {
        priceEl.innerText = parseFloat(price).toFixed(2);
        changeEl.innerText = `${change > 0 ? '+' : ''}${parseFloat(change).toFixed(2)}%`;
        changeEl.className = `change ${change >= 0 ? 'up' : 'down'}`;
        updateEl.innerText = new Date().toLocaleTimeString() + ` (${source})`;
    };

    // 方案 1: Finnhub (手機端最穩定，無 CORS 限制)
    try {
        const response = await fetch(`https://finnhub.io/api/v1/quote?symbol=TQQQ&token=cvv7re1r01qbd76mtt00cvv7re1r01qbd76mtt0g`);
        const data = await response.json();
        if (data && data.c && data.c !== 0) {
            const price = data.c;
            const prevClose = data.pc;
            const change = (((price - prevClose) / prevClose) * 100);
            updateUI(price, change, "Cloud");
            return;
        }
    } catch (e) {
        console.warn("Finnhub failed");
    }

    // 方案 2: 本地 API (僅限家中心 Mac Mini 環境)
    try {
        const response = await fetch('http://localhost:5001/api/tqqq', { mode: 'cors' });
        if (response.ok) {
            const data = await response.json();
            updateUI(data.price, data.change, "Local");
            return;
        }
    } catch (e) {
        console.warn("Local API failed");
    }

    // 最終報錯
    priceEl.innerText = "連線中...";
    updateEl.innerText = "正在重試獲取數據";
}

fetchTQQQPrice();
setInterval(fetchTQQQPrice, 30000); // 縮短到 30 秒更新一次
