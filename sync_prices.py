import yfinance as yf
import os
import json
import time
from datetime import datetime, timezone, timedelta
import subprocess

# Path configurations
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(REPO_DIR, 'data.json')
INDEX_FILE = os.path.join(REPO_DIR, 'index.html')

def format_hkd(num):
    return f"${num:,.0f}"

def get_latest_prices():
    print("Fetching highest frequency prices (v4.1) from yfinance...")
    tqqq = yf.Ticker("TQQQ")
    soxl = yf.Ticker("SOXL")
    
    t_info = tqqq.info
    s_info = soxl.info
    
    def fetch_best_price(info, fast_price):
        pre = info.get('preMarketPrice')
        post = info.get('postMarketPrice')
        reg = info.get('regularMarketPrice')
        current = info.get('currentPrice')
        
        market_state = info.get('marketState', '').upper()
        
        if market_state == 'PRE' and pre is not None and pre > 0:
            return round(pre, 2)
        if (market_state == 'POST' or market_state == 'CLOSED') and post is not None and post > 0:
            return round(post, 2)
            
        if current is not None and current > 0:
            return round(current, 2)
            
        if pre is not None and pre > 0 and pre != reg:
            return round(pre, 2)
        if post is not None and post > 0 and post != reg:
            return round(post, 2)
            
        if reg is not None and reg > 0:
            return round(reg, 2)
            
        prices = [info.get('ask'), info.get('bid'), fast_price]
        valid_prices = [p for p in prices if p is not None and p > 0]
        return round(max(valid_prices), 2) if valid_prices else 0

    t_price = fetch_best_price(t_info, tqqq.fast_info.last_price)
    s_price = fetch_best_price(s_info, soxl.fast_info.last_price)
    
    t_reg = t_info.get('regularMarketPrice') or t_price
    t_label = "EXT" if abs(t_price - t_reg) > 0.01 else "REG"
    
    return t_price, t_label, s_price

def update_files():
    try:
        if not os.path.exists(DATA_FILE): 
            print("data.json not found")
            return False
            
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        
        tqqq_price, t_label, soxl_price = get_latest_prices()
        
        old_tqqq = data['market_prices'].get('tqqq_usd', 0)
        old_soxl = data['market_prices'].get('soxl_usd', 0)
        
        # 價格防洗版機制 (如果價格無變，則不 Push)
        if tqqq_price == old_tqqq and soxl_price == old_soxl:
            print(f"Prices unchanged (TQQQ: {tqqq_price}, SOXL: {soxl_price}). Checking if HTML needs update anyway...")
            # We don't return here if we want to force the v4.1 UI update,
            # but in normal runs we would. Let's let it pass this ONE TIME 
            # to push the new GitHub Actions button.
            
        rate = data['market_prices']['usd_hkd_rate']
        
        data['market_prices']['tqqq_usd'] = tqqq_price
        data['market_prices']['soxl_usd'] = soxl_price
        # 確保使用香港時間 (GitHub Server 預設是 UTC)
        hk_tz = timezone(timedelta(hours=8))
        current_time_str = datetime.now(hk_tz).strftime('%Y-%m-%d %H:%M:%S')
        data['last_updated'] = current_time_str
        
        total_value_hkd = 0
        total_cost_hkd = 0
        for acc in data['accounts']:
            acc_val = 0
            for h in acc['holdings']:
                if h['asset'] == 'TQQQ': h['current_price_usd'] = tqqq_price
                if h['asset'] == 'SOXL': h['current_price_usd'] = soxl_price
                asset_val = h['quantity'] * h['current_price_usd'] * rate
                acc_val += asset_val
                total_cost_hkd += h['quantity'] * h['avg_price_usd'] * rate
            acc['total_value_hkd'] = round(acc_val, 0)
            acc['total_profit_hkd'] = round(acc_val - acc['total_cost_hkd'], 0)
            total_value_hkd += acc_val
            
        total_profit_hkd = total_value_hkd - total_cost_hkd
        data['portfolio_summary']['total_value_hkd'] = round(total_value_hkd, 0)
        data['portfolio_summary']['total_profit_hkd'] = round(total_profit_hkd, 0)

        total_profit_pct = (total_profit_hkd / total_cost_hkd) * 100 if total_cost_hkd > 0 else 0
        total_profit_color = '#10b981' if total_profit_hkd >= 0 else '#ef4444'
        total_profit_sign = '+' if total_profit_hkd >= 0 else ''

        stage1_reserve = 450000
        available_profit_for_stage2 = total_profit_hkd - stage1_reserve
        prog2 = min(100, max(0, (available_profit_for_stage2 / 1000000) * 100))
        
        stage2_reserve = 1000000
        available_profit_for_stage3 = available_profit_for_stage2 - stage2_reserve
        prog3 = min(100, max(0, (available_profit_for_stage3 / 550000) * 100))

        milestones_html = ""
        for m in data['milestones']:
            status_class = f"status-{m['status']}"
            
            target_price = m['tqqq_target_usd']
            price_diff = target_price - tqqq_price
            price_diff_pct = (price_diff / tqqq_price) * 100 if target_price > tqqq_price else 0
            
            gap_label = "尚差價格" if target_price > tqqq_price else "超額"
            gap_sign = "+" if target_price > tqqq_price else ""
            gap_val = f"{gap_sign}{price_diff:.2f} ({price_diff_pct:.1f}%)" if target_price > tqqq_price else "已達標"
            gap_color = "var(--accent)" if target_price > tqqq_price else "var(--success)"
            
            if m['stage'] == 1:
                stage_prog = 100.0
                avail_profit_str = f"已鎖定 {format_hkd(m['target_amount_hkd'])}"
                prog_label = "雜費利潤進度"
                shortfall_str = "$0"
            elif m['stage'] == 2:
                stage_prog = prog2
                avail_profit_str = format_hkd(available_profit_for_stage2)
                prog_label = "首期利潤進度"
                shortfall = max(0, 1000000 - available_profit_for_stage2)
                shortfall_str = format_hkd(shortfall)
            elif m['stage'] == 3:
                stage_prog = prog3 if available_profit_for_stage2 > stage2_reserve else 0.0
                avail_profit_str = format_hkd(available_profit_for_stage3) if available_profit_for_stage3 > 0 else "$0"
                prog_label = "裝修利潤進度"
                shortfall = max(0, 550000 - available_profit_for_stage3)
                shortfall_str = format_hkd(shortfall)
                
            details = f"""
            <div class="progress-details">
                <div class="price-gap-box">
                    <div class="pg-row"><span>目標價</span><span class="pg-val">${target_price}</span></div>
                    <div class="pg-row"><span>目前現價 ({t_label})</span><span class="pg-val" style="color:var(--accent);">${tqqq_price}</span></div>
                    <div class="pg-row main-gap"><span>{gap_label}</span><span class="pg-val" style="color:{gap_color};">{gap_val}</span></div>
                </div>
                <div class="detail-row" style="margin-top: 15px;"><span>{prog_label}</span><span class="detail-val">{stage_prog:.1f}%</span></div>
                <div class="progress-bg"><div class="progress-fill" style="width: {stage_prog}%"></div></div>
                <div class="detail-row" style="margin-top: 8px;"><span>可用利潤</span><span class="detail-val">{avail_profit_str}</span></div>
                <div class="detail-row" style="margin-top: 4px;"><span>尚欠金額</span><span class="detail-val" style="color:var(--accent);">{shortfall_str}</span></div>
            </div>"""
            
            if m['stage'] == 1:
                details = '<div style="font-size: 11px; color: var(--success); margin-bottom: 10px;">✅ 盈利已覆蓋 $45 萬雜費</div>' + details
                
            milestones_html += f"""<div class="milestone-card">
                <div class="m-header"><span class="m-title">Stage {m['stage']}: {m['name']}</span><span class="m-status {status_class}">{m['status']}</span></div>
                {details}<div class="m-strategy">{m['strategy']}</div></div>"""

        accounts_html = ""
        for acc in data['accounts']:
            rows = ""
            for h in acc['holdings']:
                gain = ((h['current_price_usd'] - h['avg_price_usd']) / h['avg_price_usd'] * 100)
                pl = (h['current_price_usd'] - h['avg_price_usd']) * h['quantity'] * rate
                rows += f"""<div class="asset-row"><div class="asset-info">
                    <div class="asset-name">{h['asset']} <span class="qty">× {h['quantity']}</span></div>
                    <div class="asset-cost">成本 ${h['avg_price_usd']} | 現價 ${h['current_price_usd']}</div></div>
                    <div style="text-align: right;"><div class="asset-status {'up' if gain >= 0 else 'down'}">{'+' if gain >= 0 else ''}{gain:.1f}%</div>
                    <div style="font-size: 10px; color: var(--text-dim);">{format_hkd(pl)}</div></div></div>"""
            accounts_html += f"""<div class="account-block">
                <div class="account-header"><span>{acc['account_name']}</span><span class="acc-val">{format_hkd(acc['total_value_hkd'])}</span></div>
                <div class="holdings-list">{rows}</div></div>"""

        new_html = f"""<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"><title>TQQQ Plan | v4.2 (Auto Cloud Sync)</title>
<style>
:root {{ --bg: #09090b; --card: #18181b; --glass: rgba(255, 255, 255, 0.03); --border: rgba(255, 255, 255, 0.08); --accent: #3b82f6; --success: #10b981; --danger: #ef4444; --text-main: #fafafa; --text-dim: #71717a; }}
* {{ box-sizing: border-box; }}
body {{ font-family: -apple-system, system-ui, sans-serif; background: var(--bg); color: var(--text-main); margin: 0; padding: 24px 16px; display: flex; justify-content: center; }}
.container {{ max-width: 480px; width: 100%; }}
header {{ margin-bottom: 28px; }}
.header-top {{ display: flex; justify-content: space-between; align-items: center; }}
h1 {{ font-size: 26px; font-weight: 800; margin: 0; }}
.v-tag {{ font-size: 10px; color: var(--text-dim); background: var(--glass); padding: 2px 6px; border-radius: 4px; border: 1px solid var(--border); }}
.last-update {{ font-size: 11px; color: var(--text-dim); margin-top: 6px; }}
.main-summary {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 24px; }}
.summary-card {{ background: var(--card); border: 1px solid var(--border); padding: 18px; border-radius: 20px; position: relative; }}
.summary-card::before {{ content: ''; position: absolute; top:0; left:0; width:4px; height:100%; background: var(--accent); }}
.summary-label {{ font-size: 11px; font-weight: 600; color: var(--text-dim); text-transform: uppercase; margin-bottom: 6px; }}
.summary-value {{ font-size: 20px; font-weight: 700; }}
.profit-display {{ display: flex; align-items: baseline; gap: 8px; }}
.profit-pct {{ font-size: 14px; font-weight: 700; padding-bottom: 1px; }}

.ticker-bar {{ display: flex; gap: 10px; margin-bottom: 24px; overflow-x: auto; padding-bottom: 8px; scrollbar-width: none; }}
.ticker-item {{ background: var(--glass); border: 1px solid var(--border); padding: 10px 14px; border-radius: 14px; display: flex; align-items: center; gap: 10px; }}
.ticker-symbol {{ font-weight: 700; font-size: 13px; color: var(--text-dim); }}
.ticker-price {{ font-family: monospace; font-size: 13px; color: #fff; }}
.session-tag {{ font-size: 9px; padding: 1px 4px; border-radius: 3px; background: rgba(59,130,246,0.2); color: var(--accent); margin-left: 4px; border: 0.5px solid var(--accent); }}

.sync-btn {{ display: block; width: 100%; padding: 14px; background: rgba(255,255,255,0.05); color: #fff; text-align: center; text-decoration: none; border-radius: 14px; font-size: 14px; font-weight: 600; border: 1px solid var(--border); margin-bottom: 32px; transition: background 0.2s; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
.sync-btn:active {{ background: rgba(255,255,255,0.1); transform: translateY(1px); }}

h2 {{ font-size: 13px; font-weight: 700; margin: 0 0 16px; color: var(--text-dim); letter-spacing: 0.1em; display: flex; align-items: center; gap: 10px; text-transform: uppercase; }}
h2::after {{ content: ''; flex: 1; height: 1px; background: var(--border); }}
.milestone-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 24px; padding: 20px; margin-bottom: 16px; }}
.m-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
.m-title {{ font-weight: 700; font-size: 17px; }}
.m-status {{ font-size: 9px; font-weight: 800; padding: 3px 8px; border-radius: 8px; }}
.status-COMPLETED {{ background: rgba(16,185,129,0.1); color: var(--success); border: 1px solid var(--success); }}
.status-IN_PROGRESS {{ background: rgba(59,130,246,0.1); color: var(--accent); border: 1px solid var(--accent); }}
.status-PENDING {{ background: rgba(161,161,170,0.1); color: var(--text-dim); border: 1px solid var(--border); }}
.price-gap-box {{ background: rgba(255,255,255,0.03); padding: 12px; border-radius: 16px; border: 1px solid var(--border); }}
.pg-row {{ display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px; color: var(--text-dim); }}
.pg-val {{ color: #fff; font-weight: 600; }}
.main-gap {{ margin-top: 8px; padding-top: 8px; border-top: 1px dashed var(--border); color: #fff; }}
.main-gap .pg-val {{ font-size: 15px; }}
.progress-details {{ margin-bottom: 14px; }}
.detail-row {{ display: flex; justify-content: space-between; font-size: 12px; color: var(--text-dim); margin-bottom: 4px; }}
.detail-val {{ font-weight: 700; color: #fff; }}
.m-strategy {{ font-size: 12px; color: var(--text-dim); line-height: 1.6; padding-top: 14px; border-top: 1px solid var(--border); margin-top: 15px; }}
.progress-bg {{ background: rgba(255,255,255,0.03); height: 8px; border-radius: 10px; overflow: hidden; }}
.progress-fill {{ background: linear-gradient(90deg, var(--accent), #60a5fa); height: 100%; border-radius: 10px; transition: width 0.5s ease; }}
.account-block {{ margin-bottom: 28px; }}
.account-header {{ display: flex; justify-content: space-between; font-size: 14px; font-weight: 700; margin-bottom: 12px; padding: 0 4px; }}
.asset-row {{ background: var(--card); border: 1px solid var(--border); padding: 14px 18px; border-radius: 18px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
.asset-name {{ font-weight: 700; font-size: 15px; }}
.qty {{ font-size: 11px; color: var(--text-dim); margin-left: 6px; }}
.asset-cost {{ font-size: 11px; color: var(--text-dim); margin-top: 2px; }}
.asset-status {{ font-weight: 800; font-size: 15px; }}
.up {{ color: var(--success); }}
.down {{ color: var(--danger); }}
</style></head>
<body><div class="container">
<header><div class="header-top"><h1>📈 TQQQ Plan</h1><span class="v-tag">v4.2</span></div><div class="last-update">Last Update: {current_time_str}</div></header>
<section class="main-summary">
    <div class="summary-card"><div class="summary-label">Total Value (HKD)</div><div class="summary-value">{format_hkd(total_value_hkd)}</div></div>
    <div class="summary-card">
        <div class="summary-label">Total Profit</div>
        <div class="profit-display" style="color:{total_profit_color}">
            <div class="summary-value">{format_hkd(total_profit_hkd)}</div>
            <div class="profit-pct">{total_profit_sign}{total_profit_pct:.1f}%</div>
        </div>
    </div>
</section>
<section class="ticker-bar">
    <div class="ticker-item"><span class="ticker-symbol">TQQQ</span><span class="ticker-price">${tqqq_price}</span><span class="session-tag" style="display:{'inline-block' if t_label == 'EXT' else 'none'}">{t_label}</span></div>
    <div class="ticker-item"><span class="ticker-symbol">SOXL</span><span class="ticker-price">${soxl_price}</span><span class="session-tag" style="display:none">EXT</span></div>
</section>

<section><h2>Strategic Targets</h2>{milestones_html}</section>
<section style="margin-top: 32px; margin-bottom: 32px;"><h2>Holdings</h2>{accounts_html}</section>

<a href="https://github.com/tsy-del/tqqq/actions/workflows/sync.yml" target="_blank" class="sync-btn">
    🔄 手動觸發雲端更新 (GitHub Actions)
</a>
</div></body></html>"""
        
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        with open(INDEX_FILE, 'w') as f: f.write(new_html)
        
        os.chdir(REPO_DIR)
        subprocess.run(["git", "add", "data.json", "index.html", "sync_prices.py", ".github/workflows/sync.yml"], check=True)
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-m", f"v4.2: Auto Cloud Sync config at {current_time_str}"], check=True)
            subprocess.run(["git", "push", "origin", "main"], check=True)
            subprocess.run(["git", "push", "origin", "main:gh-pages", "--force"], check=True)
            print("Update and push completed successfully.")
        else:
            print("No changes to commit. Stopping script early.")
            
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    update_files()
