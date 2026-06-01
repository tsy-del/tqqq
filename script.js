async function fetchTQQQPrice() {
    const symbol = 'TQQQ';
    const priceEl = document.getElementById('tqqq-price');
    const changeEl = document.getElementById('price-change');
    const updateEl = document.getElementById('last-update');

    try {
        // 使用一個支持 CORS 的財經 API 代理，或者使用更開放的數據源
        // 這裡嘗試使用一個比較穩定的金融數據 API
        const response = await fetch(`https://api.iextrading.com/1.0/stock/${symbol}/quote`);
        
        if (!response.ok) {
            // 如果 IEX 失敗，嘗試另一個
            throw new Error('IEX Failed');
        }

        const data = await response.json();
        const price = data.latestPrice;
        const changePercent = (data.changePercent * 100).toFixed(2);

        priceEl.innerText = price.toFixed(2);
        changeEl.innerText = `${changePercent > 0 ? '+' : ''}${changePercent}%`;
        changeEl.className = `change ${changePercent >= 0 ? 'up' : 'down'}`;
        updateEl.innerText = new Date().toLocaleTimeString();

    } catch (error) {
        console.warn('API Error, trying fallback...', error);
        // Fallback: 顯示「休市中」或使用固定延遲數據
        priceEl.innerText = "休市或載入中";
        changeEl.innerText = "--%";
        updateEl.innerText = "請檢查網絡或等候開市";
    }
}

fetchTQQQPrice();
setInterval(fetchTQQQPrice, 60000);