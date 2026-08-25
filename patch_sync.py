import os

path = '/Users/tsy/.openclaw/workspace/tqqq-plan/sync_prices.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

rep1 = """<div class="summary-card">
        <div class="summary-label">Total Value (HKD)</div>
        <div class="summary-value">{format_hkd(total_value_hkd)}</div>
        <div style="font-size: 11px; color: var(--text-dim); margin-top: 6px;">總成本: {format_hkd(total_cost_hkd)}</div>
    </div>
    <div class="summary-card">
        <div class="summary-label">Total Profit</div>
        <div class="profit-display" style="color:{total_profit_color}">
            <div class="summary-value">{format_hkd(total_profit_hkd)}</div>
            <div class="profit-pct">{total_profit_sign}{total_profit_pct:.1f}%</div>
        </div>
    </div>"""

target1 = """<div class="summary-card">
        <div class="summary-label">Total Value (HKD)</div>
        <div class="summary-value" id="summary-total-value">{format_hkd(total_value_hkd)}</div>
        <div style="font-size: 11px; color: var(--text-dim); margin-top: 6px;">總成本: <span id="summary-total-cost">{format_hkd(total_cost_hkd)}</span></div>
    </div>
    <div class="summary-card">
        <div class="summary-label">Total Profit</div>
        <div class="profit-display" id="summary-profit-display" style="color:{total_profit_color}">
            <div class="summary-value" id="summary-total-profit">{format_hkd(total_profit_hkd)}</div>
            <div class="profit-pct" id="summary-profit-pct">{total_profit_sign}{total_profit_pct:.1f}%</div>
        </div>
    </div>"""

content = content.replace(rep1, target1)

rep2 = """        ticker_bar_html += f\"\"\"<a href="https://hk.finance.yahoo.com/quote/{sym}" target="_blank" class="ticker-item" style="text-decoration: none;">
                <div style="display: flex; align-items: center; gap: 6px; overflow: hidden;">
                    <span class="ticker-symbol" style="flex-shrink: 0;">{sym}</span>
                    <span class="ticker-price" style="flex-shrink: 0;">${p_data['price']}</span>
                    <span class="session-tag" style="display:{'inline-block' if p_data['label'] == 'EXT' else 'none'}; flex-shrink: 0; font-size: 8px; padding: 0 2px;">{p_data['label']}</span>
                </div>
                <span style="font-size: 11px; font-weight: 700; color: {chg_color}; flex-shrink: 0;">{chg_sign}{chg:.1f}%</span>
            </a>\\n\"\"\""""

target2 = """        ticker_bar_html += f\"\"\"<a href="https://hk.finance.yahoo.com/quote/{sym}" target="_blank" class="ticker-item" style="text-decoration: none;">
                <div style="display: flex; align-items: center; gap: 6px; overflow: hidden;">
                    <span class="ticker-symbol" style="flex-shrink: 0;">{sym}</span>
                    <span class="ticker-price" id="ticker-price-{sym}" style="flex-shrink: 0;">${p_data['price']}</span>
                    <span class="session-tag" id="ticker-session-{sym}" style="display:{'inline-block' if p_data['label'] == 'EXT' else 'none'}; flex-shrink: 0; font-size: 8px; padding: 0 2px;">{p_data['label']}</span>
                </div>
                <span id="ticker-chg-{sym}" style="font-size: 11px; font-weight: 700; color: {chg_color}; flex-shrink: 0;">{chg_sign}{chg:.1f}%</span>
            </a>\\n\"\"\""""

content = content.replace(rep2, target2)

rep3 = """<header><div class="header-top"><h1>📈 TQQQ Plan</h1><span class="v-tag">{SCRIPT_VERSION}</span></div><div class="last-update">Last Update: {current_time_str}</div></header>"""
target3 = """<header><div class="header-top"><h1>📈 TQQQ Plan</h1><div><span class="v-tag" id="live-indicator" style="background: rgba(16,185,129,0.2); color: var(--success); margin-right: 4px; border: 1px solid var(--success); display: none; align-items: center; gap: 4px;">LIVE<span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:var(--success); animation: pulse 1.5s infinite;"></span></span><span class="v-tag">{SCRIPT_VERSION}</span></div></div><div class="last-update">Last Update: {current_time_str}</div></header>"""
content = content.replace(rep3, target3)

rep_css = """<style>
:root {"""
target_css = """<style>
@keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }
:root {"""
content = content.replace(rep_css, target_css)

rep_js_prep = """        history_html = f\"\"\"<section style="margin-top: 32px; margin-bottom: 32px;">"""
target_js_prep = """        app_data_json = json.dumps(data)
        active_tickers_json = json.dumps(active_tickers_sorted)

        history_html = f\"\"\"<section style="margin-top: 32px; margin-bottom: 32px;">"""
content = content.replace(rep_js_prep, target_js_prep)

rep4 = """</body></html>\"\"\""""
target4 = """<script>
const APP_DATA = {app_data_json};
const ACTIVE_TICKERS = {active_tickers_json};
const USD_HKD_RATE = {rate};
const TOTAL_COST_HKD = {total_cost_hkd};

async function fetchLivePrices() {{
    try {{
        const symbols = ACTIVE_TICKERS.join(',');
        const yfUrl = `https://query1.finance.yahoo.com/v7/finance/quote?symbols=${{symbols}}`;
        const proxyUrl = `https://api.allorigins.win/raw?url=${{encodeURIComponent(yfUrl)}}`;
        const res = await fetch(proxyUrl);
        const json = await res.json();
        const results = json.quoteResponse.result;
        
        let newTotalValueHkd = 0;
        const prices = {{}};

        results.forEach(q => {{
            let price = q.postMarketPrice || q.preMarketPrice || q.regularMarketPrice;
            if (!price) return;
            prices[q.symbol] = price;
            
            const priceEl = document.getElementById(`ticker-price-${{q.symbol}}`);
            if(priceEl) priceEl.innerText = `$${{price.toFixed(2)}}`;
            
            const chgEl = document.getElementById(`ticker-chg-${{q.symbol}}`);
            if(chgEl) {{
                let chgPct = q.regularMarketChangePercent;
                let marketState = (q.marketState || '').toUpperCase();
                if ((marketState === 'PRE' || marketState === 'PREPRE' || marketState === 'POST' || marketState === 'POSTPOST' || marketState === 'CLOSED') && q.postMarketChangePercent) {{
                    chgPct = q.postMarketChangePercent;
                }} else if ((marketState === 'PRE' || marketState === 'PREPRE') && q.preMarketChangePercent) {{
                    chgPct = q.preMarketChangePercent;
                }}
                if (chgPct !== undefined && chgPct !== null) {{
                    chgEl.innerText = (chgPct >= 0 ? '+' : '') + chgPct.toFixed(1) + '%';
                    chgEl.style.color = chgPct >= 0 ? 'var(--success)' : 'var(--danger)';
                }}
            }}
            
            const sessionEl = document.getElementById(`ticker-session-${{q.symbol}}`);
            if(sessionEl) {{
                let label = "REG";
                let diff = Math.abs(price - q.regularMarketPrice);
                if (diff > 0.01 && q.marketState !== 'REGULAR') label = "EXT";
                sessionEl.innerText = label;
                sessionEl.style.display = (label === 'EXT') ? 'inline-block' : 'none';
            }}
        }});

        APP_DATA.accounts.forEach(acc => {{
            acc.holdings.forEach(h => {{
                if (h.asset !== 'USD 現金' && prices[h.asset]) {{
                    newTotalValueHkd += (h.quantity * prices[h.asset] * USD_HKD_RATE);
                }} else if (h.asset === 'USD 現金') {{
                    newTotalValueHkd += (h.quantity * USD_HKD_RATE);
                }}
            }});
        }});
        
        if (newTotalValueHkd > 0) {{
            newTotalValueHkd = Math.round(newTotalValueHkd);
            const newTotalProfit = newTotalValueHkd - TOTAL_COST_HKD;
            const newTotalProfitPct = (newTotalProfit / TOTAL_COST_HKD) * 100;
            
            const valEl = document.getElementById('summary-total-value');
            if(valEl) valEl.innerText = '$' + newTotalValueHkd.toLocaleString('en-US');
            
            const profitEl = document.getElementById('summary-total-profit');
            if(profitEl) profitEl.innerText = (newTotalProfit >= 0 ? '$' : '-$') + Math.abs(newTotalProfit).toLocaleString('en-US');
            
            const profitPctEl = document.getElementById('summary-profit-pct');
            const displayEl = document.getElementById('summary-profit-display');
            if(profitPctEl && displayEl) {{
                profitPctEl.innerText = (newTotalProfit >= 0 ? '+' : '') + newTotalProfitPct.toFixed(1) + '%';
                displayEl.style.color = newTotalProfit >= 0 ? '#10b981' : '#ef4444';
            }}
        }}

        const ind = document.getElementById('live-indicator');
        if(ind) ind.style.display = 'inline-flex';
        
    }} catch(e) {{
        console.error("Live update failed:", e);
    }}
}}

setInterval(fetchLivePrices, 10000);
setTimeout(fetchLivePrices, 1500);
</script>
</body></html>\"\"\""""
content = content.replace(rep4, target4)

content = content.replace('SCRIPT_VERSION = "v5.4"', 'SCRIPT_VERSION = "v5.5"')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patch applied")