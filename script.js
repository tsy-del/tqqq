const PORTFOLIO_DATA = {
  "last_updated": "2026-06-01T12:10:00+08:00",
  "market_prices": {
    "tqqq_usd": 85.74,
    "soxl_usd": 224.34,
    "usd_hkd_rate": 7.8
  },
  "portfolio_summary": {
    "total_value_hkd": 1812950,
    "total_cost_hkd": 1216014,
    "total_profit_hkd": 596936
  },
  "accounts": [
    {
      "account_name": "帳戶 A (滾動首期)",
      "total_value_hkd": 383622,
      "total_profit_hkd": 128202,
      "total_cost_hkd": 255420,
      "holdings": [
        { "asset": "TQQQ", "quantity": 544, "avg_price_usd": 57.825, "current_price_usd": 85.74 },
        { "asset": "SOXL", "quantity": 11, "avg_price_usd": 116.96, "current_price_usd": 224.34 }
      ]
    },
    {
      "account_name": "帳戶 B (固定基金)",
      "total_value_hkd": 1429328,
      "total_profit_hkd": 468734,
      "total_cost_hkd": 960594,
      "is_locked": true,
      "holdings": [
        { "asset": "TQQQ", "quantity": 2137, "avg_price_usd": 57.63, "current_price_usd": 85.74 }
      ]
    }
  ],
  "milestones": [
    {
      "stage": 1,
      "name": "買樓雜費",
      "target_amount_hkd": 450000,
      "cumulative_target_hkd": 450000,
      "tqqq_target_usd": 78.69,
      "status": "COMPLETED",
      "strategy": "觸及即走：沽出約 455 股，套現 $45 萬現金鎖定稅項與佣金。",
      "notes": "收樓後預期可獲約 $11.9 萬按揭總回贈"
    },
    {
      "stage": 2,
      "name": "100萬首期",
      "target_amount_hkd": 1000000,
      "cumulative_target_hkd": 1450000,
      "tqqq_target_usd": 126.96,
      "status": "IN_PROGRESS",
      "current_allocated_hkd": 122253,
      "progress_percentage": 14.69,
      "strategy": "移動止賺：啟動 Trailing Stop。高位任飛，高位回落 10% 即強制套現 $100 萬。"
    },
    {
      "stage": 3,
      "name": "裝修全包",
      "target_amount_hkd": 550000,
      "cumulative_target_hkd": 2000000,
      "tqqq_target_usd": 153.25,
      "status": "PENDING",
      "strategy": "回贈＋餘兵：收樓拿走按揭回贈填補，其餘股份放長線重新滾動。"
    }
  ]
};

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
                                <td align="right" style="font-size:0.75rem; color:#8e8e93;">成本 $${h.avg_price_usd}</td>
                                <td align="right" class="${gain >= 0 ? 'up' : 'down'}" style="font-weight:bold; width:70px;">${gain >= 0 ? '+' : ''}${gain}%</td>
                            </tr>
                        `;
                    }).join('')}
                </table>
            </div>
        `).join('');
        
        const statusEl = document.getElementById('dashboard-status');
        if (statusEl) statusEl.style.display = 'none';

    } catch (renderError) {
        console.error("Rendering error:", renderError);
    }
}

// 直接從變量渲染，不依賴外部 fetch
window.addEventListener('load', () => {
    renderDashboard(PORTFOLIO_DATA);
});
