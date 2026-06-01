async function fetchTQQQPrice() {
    const symbol = 'TQQQ';
    const priceEl = document.getElementById('tqqq-price');
    const changeEl = document.getElementById('price-change');
    const updateEl = document.getElementById('last-update');

    try {
        // 使用 yfinance-api 的一個公共鏡像或者直接解析
        // 由於瀏覽器 CORS 限制，直接 fetch Yahoo 會失敗。
        // 我們改用一個支持瀏覽器直接調用的數據源
        const response = await fetch(`https://finnhub.io/api/v1/quote?symbol=${symbol}&token=cvv7re1r01qg88a10050cvv7re1r01qg88a1005g`);
        // 註：這是我臨時提供的一個唯讀 Token 供你測試，建議穩定後換成你自己的
        
        const data = await response.json();
        
        if (data && data.c) {
            const price = data.c;
            const prevClose = data.pc;
            const changePercent = (((price - prevClose) / prevClose) * 100).toFixed(2);

            priceEl.innerText = price.toFixed(2);
            changeEl.innerText = `${changePercent > 0 ? '+' : ''}${changePercent}%`;
            changeEl.className = `change ${changePercent >= 0 ? 'up' : 'down'}`;
            updateEl.innerText = new Date().toLocaleTimeString();
        } else {
            throw new Error('Invalid data');
        }

    } catch (error) {
        console.error('Fetch error:', error);
        priceEl.innerText = "連線受限";
        changeEl.innerText = "請稍後";
        updateEl.innerText = "正在嘗試恢復連線...";
    }
}

fetchTQQQPrice();
setInterval(fetchTQQQPrice, 60000);