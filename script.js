async function loadData() {
    try {
        console.log("Fetching data.json...");
        // 強制忽略緩存
        const response = await fetch('data.json?v=' + Date.now());
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();
        console.log("Data loaded:", data);
        renderDashboard(data);
    } catch (e) {
        console.error("Failed to load data.json", e);
        document.body.innerHTML += `<div style="color:red; padding:20px;">載入數據失敗，請確認 data.json 是否存在。錯誤: ${e.message}</div>`;
    }
}

function formatHKD(num) {
    return new Intl.NumberFormat('zh-HK', { 
        style: 'currency', 
        currency: 'HKD', 
        maximumFractionDigits: 0 
    }).format(num);
}

function renderDashboard(data) {
    try {
        // 更新時間
        document.getElementById('last-update').innerText = new Date(data.last_updated).toLocaleString();
        
        // 總資產與盈虧
        document.getElementById('total-value').innerText = formatHKD(data.portfolio_summary.total_value_hkd);
        const profit = data.portfolio_summary.total_profit_hkd;
        const profitEl = document.getElementById('total-profit');
        profitEl.innerText = formatHKD(profit);
        profitEl.style.color = profit >= 0 ? '#34c759' : '#ff3b30';

        // 市場價格
        document.getElementById('tqqq-price').innerText = `$${data.market_prices.tqqq_usd}`;
        document.getElementById('soxl-price').innerText = `$${data.market_prices.soxl_usd}`;
        document.getElementById('rate').innerText = data.market_prices.usd_hkd_rate;

        // Milestones
        const milesContainer = document.getElementById('milestones-container');
        milesContainer.innerHTML = data.milestones.map(m => `
            <div class="milestone-item">
                <div class="milestone-header">
                    <span>Stage ${m.stage}: ${m.name}</span>
                    <span class="status-tag status-${m.status}">${m.status}</span>
                </div>
                <div style="font-size: 0.9rem; margin-top:5px;">目標價: <b style="color:#007aff;">TQQQ $${m.tqqq_target_usd}</b></div>
                <div class="strategy-box">${m.strategy}</div>
            </div>
        `).join('');

        // Accounts
        const accContainer = document.getElementById('accounts-container');
        accContainer.innerHTML = data.accounts.map(acc => `
            <div class="account-card">
                <div class="milestone-header" style="border-bottom: 1px solid #333; padding-bottom: 8px; margin-bottom: 10px;">
                    <span>${acc.account_name}</span>
                    <span style="color:#007aff;">${formatHKD(acc.total_value_hkd)}</span>
                </div>
                <table class="holdings-table">
                    ${acc.holdings.map(h => {
                        const gain = ((h.current_price_usd - h.avg_price_usd) / h.avg_price_usd * 100).toFixed(1);
                        return `
                            <tr>
                                <td><b>${h.asset}</b> <span class="qty">x${h.quantity}</span></td>
                                <td align="right">成本: $${h.avg_price_usd}</td>
                                <td align="right" class="${gain >= 0 ? 'up' : 'down'}" style="font-weight:bold; width:80px;">${gain >= 0 ? '+' : ''}${gain}%</td>
                            </tr>
                        `;
                    }).join('')}
                </table>
            </div>
        `).join('');
        console.log("Dashboard rendered successfully.");
    } catch (renderError) {
        console.error("Rendering error:", renderError);
    }
}

// 頁面加載完成後執行
window.onload = loadData;
