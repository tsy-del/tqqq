async function fetchTQQQPrice() {
    const priceEl = document.getElementById('tqqq-price');
    const changeEl = document.getElementById('price-change');
    const updateEl = document.getElementById('last-update');

    try {
        // 先嘗試連接本地 Python API (yfinance)
        // 註：這需要你的 Mac Mini 正在運行 api_server.py
        const response = await fetch('http://localhost:5001/api/tqqq');
        
        if (!response.ok) throw new Error('Local API offline');

        const data = await response.json();
        
        const price = data.price;
        const change = data.change;

        priceEl.innerText = price.toFixed(2);
        changeEl.innerText = `${change > 0 ? '+' : ''}${change}%`;
        changeEl.className = `change ${change >= 0 ? 'up' : 'down'}`;
        updateEl.innerText = new Date().toLocaleTimeString() + " (yfinance)";

    } catch (error) {
        console.warn('Local API failed, falling back to Finnhub...', error);
        
        // 如果本地 yfinance 沒開，自動跳回備用 API (Finnhub)
        try {
            const response = await fetch(`https://finnhub.io/api/v1/quote?symbol=TQQQ&token=cvv7re9r01qge0q3i84gcvv7re9r01qge0q3i850`);
            const data = await response.json();
            if (data && data.c) {
                const price = data.c;
                const prevClose = data.pc;
                const change = (((price - prevClose) / prevClose) * 100).toFixed(2);
                priceEl.innerText = price.toFixed(2);
                changeEl.innerText = `${change > 0 ? '+' : ''}${change}%`;
                changeEl.className = `change ${change >= 0 ? 'up' : 'down'}`;
                updateEl.innerText = new Date().toLocaleTimeString() + " (Finnhub)";
            }
        } catch (e) {
            priceEl.innerText = "連線失敗";
        }
    }
}

fetchTQQQPrice();
setInterval(fetchTQQQPrice, 60000);