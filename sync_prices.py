"""
sync_prices.py — 主入口（項目 10：拆分模組後的整合版本）

負責串連：
- price_fetcher.py：抓取股價 / 匯率
- portfolio_calculator.py：持倉/利潤/里程碑計算
- trade_manager.py：交易明細讀取
- html_renderer.py：組裝 index.html
本檔案只保留：檔案路徑設定、git 操作、資料流程整合、寫檔與 commit/push。
"""
import os
import json
import traceback
import subprocess
import fcntl
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from price_fetcher import get_latest_prices, fetch_usd_hkd_rate
from portfolio_calculator import (
    format_hkd, downsample_history, compute_holdings_valuation,
    update_history_stats, update_daily_stats, compute_milestone_progress,
)
from trade_manager import load_trades_ledger
from html_renderer import render_page

# Path configurations
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(REPO_DIR, 'data.json')
INDEX_FILE = os.path.join(REPO_DIR, 'index.html')
PROFIT_HISTORY_FILE = os.path.join(REPO_DIR, 'profit_history.json')
TRADES_FILE = os.path.join(REPO_DIR, 'trades.json')
LOCK_FILE = os.path.join(REPO_DIR, '.sync.lock')

# v9.1 項目 10: 由 script 自動生成/管理嘅檔案 —— reset 時只清呢啲，
# 唔會清走 trades.json 等手動維護嘅資料檔案 (項目 11)
GENERATED_FILES = [
    'data.json', 'index.html', 'profit_history.json', 'sync_prices.py',
    'price_fetcher.py', 'portfolio_calculator.py', 'trade_manager.py', 'html_renderer.py',
]

SCRIPT_VERSION = "v9.1"


def run_git(args, **kwargs):
    return subprocess.run(["git"] + args, check=True, cwd=REPO_DIR, **kwargs)


def update_files():
    # v9.1 項目 11: lock file 防止手動執行同 cron 自動 sync 同時進行
    # (flock 隨進程結束自動釋放，唔會有 stale lock 問題)
    lock_fp = open(LOCK_FILE, 'w')
    try:
        fcntl.flock(lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("另一個 sync_prices.py 正在執行，跳過呢次執行。")
        lock_fp.close()
        return True

    try:
        return _update_files_locked()
    finally:
        fcntl.flock(lock_fp, fcntl.LOCK_UN)
        lock_fp.close()


def _update_files_locked():
    try:
        # 在開始任何動作前，先強制與 GitHub 同步 (防止手動更新造成的 Git Push Rejected)
        # v9.1 項目 11: 只 reset 已知由 script 生成嘅檔案，唔動 trades.json 等手動資料檔
        if not os.environ.get('GITHUB_ACTIONS'):
            run_git(["fetch", "origin", "main"])
            run_git(["checkout", "origin/main", "--"] + GENERATED_FILES)

        if not os.path.exists(DATA_FILE):
            print("data.json not found")
            return False

        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # v8.0: Load trade ledger
        trades_ledger = load_trades_ledger(TRADES_FILE)

        active_tickers = set()
        for acc in data['accounts']:
            for h in acc['holdings']:
                if h['asset'] not in ('USD 現金',):
                    if h.get('quantity', 0) > 0:
                        active_tickers.add(h['asset'])

        order = ['TQQQ', 'SOXL', 'SPCX', 'SPCH']
        active_tickers_sorted = [t for t in order if t in active_tickers]
        for t in active_tickers:
            if t not in active_tickers_sorted:
                active_tickers_sorted.append(t)

        prices_data = get_latest_prices(active_tickers_sorted, script_version=SCRIPT_VERSION)

        prev_rate = data['market_prices'].get('usd_hkd_rate', 7.8)
        rate = fetch_usd_hkd_rate(fallback=prev_rate)
        data['market_prices']['usd_hkd_rate'] = rate
        print(f"USD/HKD rate: {rate} (prev {prev_rate})")

        for sym, d in prices_data.items():
            data['market_prices'][f"{sym.lower()}_usd"] = d['price']
            data['market_prices'][f"{sym.lower()}_prev_close"] = d['prev_close']

        # 確保使用香港時間 (GitHub Server 預設是 UTC)
        hk_tz = timezone(timedelta(hours=8))
        current_time_str = datetime.now(hk_tz).strftime('%Y-%m-%d %H:%M:%S')
        data['last_updated'] = current_time_str

        # v8.2: 同步狀態追蹤
        data['sync_status'] = {
            "last_attempt": current_time_str,
            "last_success": current_time_str,
            "api_status": "success",
            "yfinance_status": "ok",
            "github_push_status": "pending",
        }

        total_value_hkd, total_cost_hkd, total_profit_hkd = compute_holdings_valuation(data, prices_data, rate)
        data['portfolio_summary']['total_value_hkd'] = int(round(total_value_hkd))
        data['portfolio_summary']['total_cost_hkd'] = int(round(total_cost_hkd))
        data['portfolio_summary']['total_profit_hkd'] = int(round(total_profit_hkd))

        # --- Trading Date (US Eastern Time 00:00~23:59) ---
        ny_tz = ZoneInfo("America/New_York")
        ny_now = datetime.now(ny_tz)
        trading_date_str = ny_now.strftime("%Y-%m-%d")
        current_profit = int(round(total_profit_hkd))

        # Profit History Logging for Chart
        if os.path.exists(PROFIT_HISTORY_FILE):
            with open(PROFIT_HISTORY_FILE, 'r', encoding='utf-8') as f:
                try:
                    profit_history = json.load(f)
                except Exception:
                    profit_history = []
        else:
            profit_history = []

        current_unix_time = int(datetime.now(hk_tz).timestamp())

        if not profit_history or profit_history[-1]['time'] < current_unix_time:
            profit_history.append({
                "time": current_unix_time,
                "value": int(round(total_profit_hkd)),
            })

        # v5.15: 分層降採樣，取代單純裁走最舊記錄
        before_count = len(profit_history)
        profit_history = downsample_history(profit_history, current_unix_time)
        if len(profit_history) != before_count:
            print(f"History downsampled: {before_count} -> {len(profit_history)} points")

        # 硬上限只作最後保險
        if len(profit_history) > 5000:
            profit_history = profit_history[-5000:]

        with open(PROFIT_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(profit_history, f, ensure_ascii=False)

        # History Stats Tracking
        update_history_stats(data, current_profit, current_time_str)

        # Daily Stats Tracking
        current_ny_date_str = trading_date_str
        now_hms = current_time_str.split(' ')[1]
        update_daily_stats(data, current_profit, current_ny_date_str, now_hms, profit_history)

        total_profit_pct = (total_profit_hkd / total_cost_hkd) * 100 if total_cost_hkd > 0 else 0
        total_profit_color = '#10b981' if total_profit_hkd >= 0 else '#ef4444'
        total_profit_sign = '+' if total_profit_hkd >= 0 else ''

        stage1_target = 450000
        stage2_target = 1000000
        stage3_target = 550000

        mp = compute_milestone_progress(total_profit_hkd, stage1_target, stage2_target, stage3_target)

        new_html = render_page(
            data=data, prices_data=prices_data, rate=rate,
            total_value_hkd=total_value_hkd, total_cost_hkd=total_cost_hkd, total_profit_hkd=total_profit_hkd,
            profit_history=profit_history, trades_ledger=trades_ledger, active_tickers_sorted=active_tickers_sorted,
            current_time_str=current_time_str, script_version=SCRIPT_VERSION,
            prog1=mp['prog1'], profit_for_stage1=mp['profit_for_stage1'], stage1_target=stage1_target,
            available_for_stage2=mp['available_for_stage2'], profit_for_stage2=mp['profit_for_stage2'],
            stage2_target=stage2_target, prog2=mp['prog2'],
            available_for_stage3=mp['available_for_stage3'], profit_for_stage3=mp['profit_for_stage3'],
            stage3_target=stage3_target, prog3=mp['prog3'],
            total_profit_color=total_profit_color, total_profit_sign=total_profit_sign,
            total_profit_pct=total_profit_pct,
        )

        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            f.write(new_html)

        run_git(["add", "data.json", "index.html", "sync_prices.py", "profit_history.json",
                 "price_fetcher.py", "portfolio_calculator.py", "trade_manager.py", "html_renderer.py"])
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
    success = update_files()
    if not success:
        import sys
        sys.exit(1)
