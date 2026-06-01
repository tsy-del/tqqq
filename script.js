async function loadData() {
    try {
        const response = await fetch('data.json?t=' + Date.now());
        const data = await response.json();
        renderDashboard(data);
    } catch (e) {
        console.error("Failed to load data.json", e);
    }
}

function formatHKD(num) {
    return new Intl.NumberFormat('zh-HK', { style: 'currency', currency: 'HKD', maximumFractionDigits: 0 }).format(num);
}

function renderDashboard(data) {
    // Basic Info
    document.getElementById('last-update').innerText = new Date(data.last_updated).toLocaleString();
    document.getElementById('total-value').innerText = formatHKD(data.portfolio_summary.total_value_hkd);
    const profit = data.portfolio_summary.total_profit_hkd;
    document.getElementById('total-profit').innerText = formatHKD(profit);
    document.getElementById('total-profit').style.color = profit >= 0 ? '#34c759' : '#ff3b30';

    // Market Prices
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
            <div style="font-size: 0.9rem;">目標: TQQQ $${m.tqqq_target_usd}</div>
            <div class="strategy-box">${m.strategy}</div>
        </div>
    `).join('');

    // Accounts
    const accContainer = document.getElementById('accounts-container');
    accContainer.innerHTML = data.accounts.map(acc => `
        <div class="account-card">
            <div class="milestone-header">
                <span>${acc.account_name}</span>
                <span>${formatHKD(acc.total_value_hkd)}</span>
            </div>
            <table class="holdings-table">
                ${acc.holdings.map(h => {
                    const gain = ((h.current_price_usd - h.avg_price_usd) / h.avg_price_usd * 100).toFixed(1);
                    return `
                        <tr>
                            <td><b>${h.asset}</b> <span class="qty">x${h.quantity}</span></td>
                            <td align="right">成本: $${h.avg_price_usd}</td>
                            <td align="right" class="${gain >= 0 ? 'up' : 'down'}">${gain >= 0 ? '+' : ''}${gain}%</td>
                        </tr>
                    `;
                }).join('')}
            </table>
        </div>
    `).join('');
}

loadData();
// No auto-price fetch for now since data is static from user input
