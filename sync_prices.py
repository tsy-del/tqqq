import yfinance as yf
import os
import json
import time
import traceback
from datetime import datetime, timezone, timedelta
import subprocess

# Path configurations
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(REPO_DIR, 'data.json')
INDEX_FILE = os.path.join(REPO_DIR, 'index.html')

SCRIPT_VERSION = "v4.14"

def format_hkd(num):
    return f"${num:,.0f}"

def run_git(args, **kwargs):
    return subprocess.run(["git"] + args, check=True, cwd=REPO_DIR, **kwargs)

def fetch_best_price(info, fast_price):
    pre = info.get('preMarketPrice')
    post = info.get('postMarketPrice')
    reg = info.get('regularMarketPrice')
    current = info.get('currentPrice')

    market_state = info.get('marketState', '').upper()

    if market_state in ('PRE', 'PREPRE') and pre is not None and pre > 0:
        return round(pre, 2)
    if market_state in ('POST', 'POSTPOST', 'CLOSED') and post is not None and post > 0:
        return round(post, 2)

    if current is not None and current > 0:
        return round(current, 2)

    if pre is not None and pre > 0 and pre != reg:
        return round(pre, 2)
    if post is not None and post > 0 and post != reg:
        return round(post, 2)

    if reg is not None and reg > 0:
        return round(reg, 2)

    # Last resort: prefer last traded price, then ask/bid
    for p in [fast_price, info.get('ask'), info.get('bid')]:
        if p is not None and p > 0:
            return round(p, 2)
    return 0

def get_ticker_data(symbol, retries=3, delay=5):
    """Fetch ticker info with retry, since yfinance occasionally fails or returns empty data."""
    last_err = None
    for attempt in range(retries):
        try:
            t = yf.Ticker(symbol)
            info = t.info
            try:
                fast_price = t.fast_info.last_price
            except Exception:
                fast_price = None
            if info and (info.get('regularMarketPrice') or info.get('currentPrice') or fast_price):
                return info, fast_price
        except Exception as e:
            last_err = e
        print(f"Retry {attempt + 1}/{retries} for {symbol}...")
        time.sleep(delay)
    raise RuntimeError(f"Failed to fetch valid data for {symbol}: {last_err}")

def get_latest_prices():
    print(f"Fetching highest frequency prices ({SCRIPT_VERSION}) from yfinance...")
    t_info, t_fast = get_ticker_data("TQQQ")
    s_info, s_fast = get_ticker_data("SOXL")

    t_price = fetch_best_price(t_info, t_fast)
    s_price = fetch_best_price(s_info, s_fast)

    # Abort if any price is invalid, so we never write zeros into data.json / HTML
    if t_price <= 0 or s_price <= 0:
        raise RuntimeError(f"Invalid price fetched (TQQQ: {t_price}, SOXL: {s_price}). Aborting update.")

    t_reg = t_info.get('regularMarketPrice') or t_price
    t_label = "EXT" if abs(t_price - t_reg) > 0.01 else "REG"

    s_reg = s_info.get('regularMarketPrice') or s_price
    s_label = "EXT" if abs(s_price - s_reg) > 0.01 else "REG"

    return t_price, t_label, s_price, s_label

def update_files():
    try:
        # 在開始任何動作前，先強制與 GitHub 同步 (防止手動更新造成的 Git Push Rejected)
        run_git(["fetch", "origin", "main"])
        run_git(["reset", "--hard", "origin/main"])

        if not os.path.exists(DATA_FILE):
            print("data.json not found")
            return False

        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        tqqq_price, t_label, soxl_price, s_label = get_latest_prices()

        old_tqqq = data['market_prices'].get('tqqq_usd', 0)
        old_soxl = data['market_prices'].get('soxl_usd', 0)

        # 價格防洗版機制 (如果價格無變，則不 Push)
        # if tqqq_price == old_tqqq and soxl_price == old_soxl:
        #     print(f"Prices unchanged (TQQQ: {tqqq_price}, SOXL: {soxl_price}). Skipping Git push to save history.")
        #     return True

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
            acc_cost = acc.get('total_cost_hkd', 0)
            acc['total_value_hkd'] = int(round(acc_val))
            acc['total_profit_hkd'] = int(round(acc_val - acc_cost))
            total_value_hkd += acc_val
            total_cost_hkd += acc_cost

        total_profit_hkd = total_value_hkd - total_cost_hkd
        data['portfolio_summary']['total_value_hkd'] = int(round(total_value_hkd))
        data['portfolio_summary']['total_profit_hkd'] = int(round(total_profit_hkd))

        total_profit_pct = (total_profit_hkd / total_cost_hkd) * 100 if total_cost_hkd > 0 else 0
        total_profit_color = '#10b981' if total_profit_hkd >= 0 else '#ef4444'
        total_profit_sign = '+' if total_profit_hkd >= 0 else ''

        stage1_target = 450000
        stage2_target = 1000000
        stage3_target = 550000

        profit_for_stage1 = max(0, min(total_profit_hkd, stage1_target))
        prog1 = (profit_for_stage1 / stage1_target) * 100

        available_for_stage2 = total_profit_hkd - stage1_target
        profit_for_stage2 = max(0, min(available_for_stage2, stage2_target)) if available_for_stage2 > 0 else 0
        prog2 = (profit_for_stage2 / stage2_target) * 100

        available_for_stage3 = available_for_stage2 - stage2_target
        profit_for_stage3 = max(0, min(available_for_stage3, stage3_target)) if available_for_stage3 > 0 else 0
        prog3 = (profit_for_stage3 / stage3_target) * 100

        milestones_html = ""
        for m in data['milestones']:
            target_price = m['tqqq_target_usd']
            price_diff = target_price - tqqq_price
            price_diff_pct = (price_diff / tqqq_price) * 100 if target_price > tqqq_price else 0

            gap_label = "剩餘距離" if target_price > tqqq_price else "超額"
            gap_val = f"{price_diff:.2f} ({price_diff_pct:.1f}%)" if target_price > tqqq_price else "已達標"
            gap_color = "var(--accent)" if target_price > tqqq_price else "var(--success)"

            if m['stage'] == 1:
                stage_prog = prog1
                avail_profit_str = format_hkd(profit_for_stage1)
                prog_label = "雜費利潤進度"
                shortfall = max(0, stage1_target - profit_for_stage1)
                shortfall_str = format_hkd(shortfall)
                m['status'] = "COMPLETED" if prog1 >= 100 else "IN_PROGRESS"
            elif m['stage'] == 2:
                stage_prog = prog2
                avail_profit_str = format_hkd(profit_for_stage2) if available_for_stage2 > 0 else "$0"
                prog_label = "首期利潤進度"
                shortfall = max(0, stage2_target - profit_for_stage2)
                shortfall_str = format_hkd(shortfall)
                if prog2 >= 100: m['status'] = "COMPLETED"
                elif available_for_stage2 > 0: m['status'] = "IN_PROGRESS"
                else: m['status'] = "PENDING"
            elif m['stage'] == 3:
                stage_prog = prog3
                avail_profit_str = format_hkd(profit_for_stage3) if available_for_stage3 > 0 else "$0"
                prog_label = "裝修利潤進度"
                shortfall = max(0, stage3_target - profit_for_stage3)
                shortfall_str = format_hkd(shortfall)
                if prog3 >= 100: m['status'] = "COMPLETED"
                elif available_for_stage3 > 0: m['status'] = "IN_PROGRESS"
                else: m['status'] = "PENDING"

            status_class = f"status-{m['status']}"

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

            if m['stage'] == 1 and prog1 >= 100:
                details = '<div style="font-size: 11px; color: var(--success); margin-bottom: 10px;">✅ 盈利已覆蓋 $45 萬雜費</div>' + details

            is_collapsed = "collapsed" if m['status'] == 'COMPLETED' else ""

            milestones_html += f"""<div class="milestone-card {is_collapsed}">
                <div class="m-header" onclick="this.parentElement.classList.toggle('collapsed')">
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <span class="m-title">Stage {m['stage']}: {m['name']}</span>
                        <span class="toggle-icon">▼</span>
                    </div>
                    <span class="m-status {status_class}">{m['status']}</span>
                </div>
                <div class="m-body">
                    {details}<div class="m-strategy">{m['strategy']}</div>
                </div>
            </div>"""

        # 終極總目標
        total_target = 2000000
        overall_prog = min(100, max(0, (total_profit_hkd / total_target) * 100))
        overall_shortfall = max(0, total_target - total_profit_hkd)

        if total_profit_hkd >= total_target:
            overall_status = "COMPLETED"
            overall_status_class = "status-COMPLETED"
            overall_shortfall_str = "$0"
            is_overall_collapsed = "collapsed"
        else:
            overall_status = "IN_PROGRESS"
            overall_status_class = "status-IN_PROGRESS"
            overall_shortfall_str = format_hkd(overall_shortfall)
            is_overall_collapsed = ""

        milestones_html += f"""<div class="milestone-card {is_overall_collapsed}" style="border: 1px solid var(--accent); box-shadow: 0 0 15px rgba(59,130,246,0.1);">
            <div class="m-header" onclick="this.parentElement.classList.toggle('collapsed')">
                <div style="display: flex; align-items: center; gap: 6px;">
                    <span class="m-title">🏆 終極總目標：純賺 200 萬</span>
                    <span class="toggle-icon">▼</span>
                </div>
                <span class="m-status {overall_status_class}">{overall_status}</span>
            </div>
            <div class="m-body">
                <div class="progress-details" style="margin-top: 10px;">
                    <div class="detail-row"><span>整體利潤進度</span><span class="detail-val">{overall_prog:.1f}%</span></div>
                    <div class="progress-bg"><div class="progress-fill" style="width: {overall_prog}%; background: linear-gradient(90deg, #3b82f6, #10b981);"></div></div>
                    <div class="detail-row" style="margin-top: 8px;"><span>目前總純利</span><span class="detail-val" style="color:var(--success);">{format_hkd(total_profit_hkd)}</span></div>
                    <div class="detail-row" style="margin-top: 4px;"><span>距離 200 萬尚欠</span><span class="detail-val" style="color:var(--accent);">{overall_shortfall_str}</span></div>
                </div>
                <div class="m-strategy">不計成本，目標純利達到 $2,000,000 以完成所有規劃 (雜費、首期、裝修)。</div>
            </div>
        </div>"""

        accounts_html = ""
        for acc in data['accounts']:
            rows = ""
            for h in acc['holdings']:
                avg = h['avg_price_usd']
                gain = ((h['current_price_usd'] - avg) / avg * 100) if avg else 0
                pl = (h['current_price_usd'] - avg) * h['quantity'] * rate
                rows += f"""<div class="asset-row"><div class="asset-info">
                    <div class="asset-name">{h['asset']} <span class="qty">× {h['quantity']}</span></div>
                    <div class="asset-cost">成本 ${avg} | 現價 ${h['current_price_usd']}</div></div>
                    <div style="text-align: right;"><div class="asset-status {'up' if gain >= 0 else 'down'}">{'+' if gain >= 0 else ''}{gain:.1f}%</div>
                    <div style="font-size: 10px; color: var(--text-dim);">{format_hkd(pl)}</div></div></div>"""
            accounts_html += f"""<div class="account-block">
                <div class="account-header"><span>{acc['account_name']}</span><span class="acc-val">{format_hkd(acc['total_value_hkd'])}</span></div>
                <div class="holdings-list">{rows}</div></div>"""

        new_html = f"""<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"><title>TQQQ Plan | {SCRIPT_VERSION} (Auto Cloud Sync)</title>
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
.milestone-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 24px; padding: 20px; margin-bottom: 16px; transition: all 0.3s ease; }}
.m-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; cursor: pointer; user-select: none; }}
.m-header:active {{ opacity: 0.7; }}
.m-title {{ font-weight: 700; font-size: 17px; }}
.toggle-icon {{ font-size: 10px; color: var(--text-dim); transition: transform 0.3s ease; }}
.milestone-card.collapsed .m-body {{ display: none; }}
.milestone-card.collapsed .m-header {{ margin-bottom: 0; }}
.milestone-card.collapsed .toggle-icon {{ transform: rotate(-90deg); }}
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
<header><div class="header-top"><h1>📈 TQQQ Plan</h1><span class="v-tag">{SCRIPT_VERSION}</span></div><div class="last-update">Last Update: {current_time_str}</div></header>
<section class="main-summary">
    <div class="summary-card">
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
    </div>
</section>
<section class="ticker-bar">
    <div class="ticker-item"><span class="ticker-symbol">TQQQ</span><span class="ticker-price">${tqqq_price}</span><span class="session-tag" style="display:{'inline-block' if t_label == 'EXT' else 'none'}">{t_label}</span></div>
    <div class="ticker-item"><span class="ticker-symbol">SOXL</span><span class="ticker-price">${soxl_price}</span><span class="session-tag" style="display:{'inline-block' if s_label == 'EXT' else 'none'}">{s_label}</span></div>
</section>

<section><h2>Strategic Targets</h2>{milestones_html}</section>
<section style="margin-top: 32px; margin-bottom: 32px;"><h2>Holdings</h2>{accounts_html}</section>

<a href="https://github.com/tsy-del/tqqq/actions/workflows/sync.yml" target="_blank" class="sync-btn">
    🔄 手動觸發雲端更新 (GitHub Actions)
</a>
</div></body></html>"""

        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            f.write(new_html)

        run_git(["add", "data.json", "index.html", "sync_prices.py"])
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=REPO_DIR)
        if status.stdout.strip():
            run_git(["commit", "-m", f"{SCRIPT_VERSION}: Auto price sync at {current_time_str}"])
            run_git(["push", "origin", "main"])
            run_git(["push", "origin", "main:gh-pages", "--force"])
            print("Update and push completed successfully.")
        else:
            print("No changes to commit. Stopping script early.")

        return True
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    update_files()
