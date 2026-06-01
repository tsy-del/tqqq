const PORTFOLIO_DATA = {
  "market_prices": {
    "tqqq_usd": 0,
    "soxl_usd": 0,
    "usd_hkd_rate": 7.8
  },
  "portfolio_summary": {
    "total_value_hkd": 0,
    "total_cost_hkd": 1216014,
    "total_profit_hkd": 0
  },
  "accounts": [
    {
      "account_name": "帳戶 A (滾動首期)",
      "total_value_hkd": 0,
      "total_profit_hkd": 0,
      "total_cost_hkd": 255420,
      "holdings": [
        { "asset": "TQQQ", "quantity": 544, "avg_price_usd": 57.825, "current_price_usd": 0 },
        { "asset": "SOXL", "quantity": 11, "avg_price_usd": 116.96, "current_price_usd": 0 }
      ]
    },
    {
      "account_name": "帳戶 B (固定基金)",
      "total_value_hkd": 0,
      "total_profit_hkd": 0,
      "total_cost_hkd": 960594,
      "is_locked": true,
      "holdings": [
        { "asset": "TQQQ", "quantity": 2137, "avg_price_usd": 57.63, "current_price_usd": 0 }
      ]
    }
  ],
  "milestones": [
    {
      "stage": 1,
      "name": "買樓雜費",
      "target_amount_hkd": 450000,
      "tqqq_target_usd": 78.69,
      "status": "COMPLETED",
      "strategy": "觸及即走：沽出約 455 股，套現 $45 萬現金鎖定稅項與佣金。"
    },
    {
      "stage": 2,
      "name": "100萬首期",
      "target_amount_hkd": 1000000,
      "tqqq_target_usd": 126.96,
      "status": "IN_PROGRESS",
      "strategy": "移動止賺：啟動 Trailing Stop。高位任飛，高位回落 10% 即強制套現 $100 萬。"
    },
    {
      "stage": 3,
      "name": "裝修全包",
      "target_amount_hkd": 550000,
      "tqqq_target_usd": 153.25,
      "status": "PENDING",
      "strategy": "回贈＋餘兵：收樓拿走按揭回贈填補，其餘股份放長線重新滾動。"
    }
  ]
};

function formatHKD(num) {
    return new Intl.NumberFormat('zh-HK', { style: 'currency', currency: 'HKD', maximumFractionDigits: 0 }).format(num);
}

// 獲取實時價格 (使用 allorigins /get 以確保繞過所有 CORS 限制)
async function fetchRealTimePrice(ticker) {
    try {
        const url = `https://api.allorigins.win/get?url=${encodeURIComponent('https://query1.finance.yahoo.com/v8/finance/chart/'+ticker)}`;
        const res = await fetch(url, { cache: "no-store" });
        const proxyData = await res.json();
        
        // 解析 allorigins 包裝的 JSON
        const data = JSON.parse(proxyData.contents);
        
        const meta = data.chart.result[0].meta;
        const regPrice = meta.regularMarketPrice;
        
        // Yahoo API 盤後/盤前有時會在 meta 裡面
        // 取最新可用價格
        const postPrice = meta.postMarketPrice;
        const prePrice = meta.preMarketPrice;
        
        let finalPrice = regPrice;
        let isExt = false;
        
        if (postPrice && postPrice !== regPrice) {
            finalPrice = postPrice;
            isExt = true;
        } else if (prePrice && prePrice !== regPrice) {
            finalPrice = prePrice;
            isExt = true;
        }
        
        return { price: Number(finalPrice.toFixed(2)), isExt: isExt };
    } catch (err) {
        console.error("Failed to fetch price for " + ticker, err);
        return null;
    }
}

async function renderDashboard() {
    // 1. Fetch live data
    const tqqqData = await fetchRealTimePrice('TQQQ');
    const soxlData = await fetchRealTimePrice('SOXL');
    
    const lastUpdateEl = document.getElementById('last-update');
    
    if (!tqqqData || !soxlData) {
        lastUpdateEl.innerText = "數據載入失敗，將於 5 秒後重試...";
        lastUpdateEl.style.color = "var(--danger)";
        return; // 不要覆蓋現有的介面，保留上次的數據
    }

    const tqqq_price = tqqqData.price;
    const soxl_price = soxlData.price;
    const rate = PORTFOLIO_DATA.market_prices.usd_hkd_rate;
    
    // 2. Calculate Totals
    let total_value_hkd = 0;
    let total_cost_hkd = PORTFOLIO_DATA.portfolio_summary.total_cost_hkd;
    
    PORTFOLIO_DATA.accounts.forEach(acc => {
        let acc_val = 0;
        acc.holdings.forEach(h => {
            if (h.asset === 'TQQQ') h.current_price_usd = tqqq_price;
            if (h.asset === 'SOXL') h.current_price_usd = soxl_price;
            acc_val += h.quantity * h.current_price_usd * rate;
        });
        acc.total_value_hkd = acc_val;
        total_value_hkd += acc_val;
    });

    let total_profit_hkd = total_value_hkd - total_cost_hkd;
    let total_profit_pct = (total_profit_hkd / total_cost_hkd) * 100;

    // 3. Update DOM Elements
    const now = new Date();
    lastUpdateEl.innerText = "Live Sync: " + now.toLocaleTimeString('zh-HK');
    lastUpdateEl.style.color = "var(--text-dim)";
    
    document.getElementById('total-value').innerText = formatHKD(total_value_hkd);
    
    const profitEl = document.getElementById('total-profit');
    profitEl.innerText = formatHKD(total_profit_hkd);
    profitEl.style.color = total_profit_hkd >= 0 ? '#10b981' : '#ef4444';
    
    document.getElementById('total-profit-pct').innerText = (total_profit_hkd >= 0 ? '+' : '') + total_profit_pct.toFixed(1) + '%';

    // Ticker Bar
    document.getElementById('tqqq-price').innerText = `$${tqqq_price}`;
    document.getElementById('soxl-price').innerText = `$${soxl_price}`;
    
    if (tqqqData.isExt) {
        document.getElementById('tqqq-label').style.display = 'inline-block';
    } else {
        document.getElementById('tqqq-label').style.display = 'none';
    }
    
    if (soxlData.isExt) {
        document.getElementById('soxl-label').style.display = 'inline-block';
    } else {
        document.getElementById('soxl-label').style.display = 'none';
    }

    // 4. Milestones
    const stage1_reserve = 450000;
    const avail2 = total_profit_hkd - stage1_reserve;
    const prog2 = Math.min(100, Math.max(0, (avail2 / 1000000) * 100));
    
    const stage2_reserve = 1000000;
    const avail3 = avail2 - stage2_reserve;
    const prog3 = Math.min(100, Math.max(0, (avail3 / 550000) * 100));

    let milestones_html = "";
    PORTFOLIO_DATA.milestones.forEach(m => {
        let target = m.tqqq_target_usd;
        let diff = target - tqqq_price;
        let diff_pct = target > tqqq_price ? (diff / tqqq_price) * 100 : 0;
        
        let gap_label = target > tqqq_price ? "尚差價格" : "超額";
        let gap_val = target > tqqq_price ? `+${diff.toFixed(2)} (${diff_pct.toFixed(1)}%)` : "已達標";
        let gap_color = target > tqqq_price ? "var(--accent)" : "var(--success)";
        
        let prog_pct = 0, avail_str = "", label = "";
        
        if (m.stage === 1) {
            prog_pct = 100;
            avail_str = `已鎖定 $450,000`;
            label = "雜費利潤進度";
        } else if (m.stage === 2) {
            prog_pct = prog2;
            avail_str = formatHKD(avail2);
            label = "首期利潤進度";
        } else if (m.stage === 3) {
            prog_pct = avail2 > stage2_reserve ? prog3 : 0;
            avail_str = avail3 > 0 ? formatHKD(avail3) : "$0";
            label = "裝修利潤進度";
        }

        let html = `
        <div class="milestone-card">
            <div class="m-header">
                <span class="m-title">Stage ${m.stage}: ${m.name}</span>
                <span class="m-status status-${m.status}">${m.status}</span>
            </div>`;
            
        if (m.stage === 1) {
            html += `<div style="font-size: 11px; color: var(--success); margin-bottom: 10px;">✅ 盈利已覆蓋 $45 萬雜費</div>`;
        }
            
        html += `
            <div class="progress-details">
                <div class="price-gap-box">
                    <div class="pg-row"><span>目標價</span><span class="pg-val">$${target}</span></div>
                    <div class="pg-row"><span>目前現價</span><span class="pg-val" style="color:var(--accent);">$${tqqq_price}</span></div>
                    <div class="pg-row main-gap"><span>${gap_label}</span><span class="pg-val" style="color:${gap_color};">${gap_val}</span></div>
                </div>
                <div class="detail-row" style="margin-top: 15px;"><span>${label}</span><span class="detail-val">${prog_pct.toFixed(1)}%</span></div>
                <div class="progress-bg"><div class="progress-fill" style="width: ${prog_pct}%"></div></div>
                <div class="detail-row" style="margin-top: 8px;"><span>可用利潤</span><span class="detail-val">${avail_str}</span></div>
            </div>
            <div class="m-strategy">${m.strategy}</div>
        </div>`;
        milestones_html += html;
    });
    document.getElementById('milestones-container').innerHTML = milestones_html;

    // 5. Accounts
    let accounts_html = "";
    PORTFOLIO_DATA.accounts.forEach(acc => {
        let rows = "";
        acc.holdings.forEach(h => {
            let gain = ((h.current_price_usd - h.avg_price_usd) / h.avg_price_usd) * 100;
            let pl = (h.current_price_usd - h.avg_price_usd) * h.quantity * rate;
            let gc = gain >= 0 ? 'up' : 'down';
            let gs = gain >= 0 ? '+' : '';
            rows += `
            <div class="asset-row">
                <div class="asset-info">
                    <div class="asset-name">${h.asset} <span class="qty">× ${h.quantity}</span></div>
                    <div class="asset-cost">成本 $${h.avg_price_usd} | 現價 $${h.current_price_usd}</div>
                </div>
                <div style="text-align: right;">
                    <div class="asset-status ${gc}">${gs}${gain.toFixed(1)}%</div>
                    <div style="font-size: 10px; color: var(--text-dim);">${formatHKD(pl)}</div>
                </div>
            </div>`;
        });
        accounts_html += `
        <div class="account-block">
            <div class="account-header"><span>${acc.account_name}</span><span class="acc-val">${formatHKD(acc.total_value_hkd)}</span></div>
            <div class="holdings-list">${rows}</div>
        </div>`;
    });
    document.getElementById('accounts-container').innerHTML = accounts_html;
}

// 網頁載入時立刻獲取，之後每 5 秒刷新一次
window.onload = () => {
    renderDashboard();
    setInterval(renderDashboard, 5000);
};
