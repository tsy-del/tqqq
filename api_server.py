import yfinance as yf
from flask import Flask, jsonify, request
from flask_cors import CORS
from functools import wraps
import os
import json
import time
import secrets

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# 你的靜態數據路徑
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data.json')

# v11.1: 寫入端點需要 auth token。首次啟動自動生成並存喺本機檔案
# （唔入 git），token 印在啟動 log，Admin UI 要求輸入先可以儲存。
TOKEN_FILE = os.path.join(os.path.dirname(__file__), '.admin_token')


def _load_or_create_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            tok = f.read().strip()
            if tok:
                return tok
    tok = secrets.token_urlsafe(24)
    with open(TOKEN_FILE, 'w') as f:
        f.write(tok)
    os.chmod(TOKEN_FILE, 0o600)
    return tok


ADMIN_TOKEN = _load_or_create_token()


def require_token(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        supplied = request.headers.get('X-Admin-Token', '')
        if not secrets.compare_digest(supplied, ADMIN_TOKEN):
            return jsonify({"status": "error", "message": "unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper


@app.route('/')
def admin_page():
    return app.send_static_file('admin.html')

@app.route('/api/data')
def get_data():
    with open(DATA_FILE, 'r') as f:
        return jsonify(json.load(f))

@app.route('/api/save_data', methods=['POST'])
@require_token
def save_data():
    try:
        new_data = request.json
        with open(DATA_FILE, 'w') as f:
            json.dump(new_data, f, indent=2, ensure_ascii=False)
            
        # 儲存後觸發 update_prices 和 git push
        import subprocess
        # 1. 執行更新腳本
        # data.json 已經由 Admin 寫入；同步時跳過 generated-file checkout，
        # 否則 sync_prices.py 的前置同步會將剛輸入的資料覆蓋回 origin/main。
        env = os.environ.copy()
        env['TQQQ_PRESERVE_LOCAL_DATA'] = '1'
        result = subprocess.run(
            ["python3", "sync_prices.py"],
            cwd=os.path.dirname(__file__), env=env,
            capture_output=True, text=True, timeout=180,
        )
        if result.returncode != 0:
            return jsonify({"status": "error", "message": "同步失敗", "detail": result.stderr[-2000:]}), 500
        
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/update_prices')
@require_token
def update_prices():
    try:
        # 1. 讀取現有的 data.json
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)

        # 2. 調用 yfinance 獲取最新價格（v11.1: 加入 SPCH，不再只更新 TQQQ/SOXL）
        tickers = {
            'TQQQ': yf.Ticker("TQQQ"),
            'SOXL': yf.Ticker("SOXL"),
            'SPCH': yf.Ticker("SPCH"),
        }
        latest_prices = {
            sym: round(t.fast_info.last_price, 2) for sym, t in tickers.items()
        }

        # 3. 更新數據
        data['market_prices']['tqqq_usd'] = latest_prices['TQQQ']
        data['market_prices']['soxl_usd'] = latest_prices['SOXL']
        data['market_prices']['spch_usd'] = latest_prices['SPCH']
        data['last_updated'] = time.strftime('%Y-%m-%dT%H:%M:%S+08:00')

        # 4. 重新計算盈虧 (Portfolio Summary)
        # v11.1: avg_price_usd 先更新 current_price_usd 再累加 cost，
        # 否則之前用的是檔案里舊的 total_cost_hkd 会導致 profit 錯。
        total_value_hkd = 0
        total_cost_hkd = 0
        rate = data['market_prices']['usd_hkd_rate']

        for acc in data['accounts']:
            acc_value_hkd = 0
            acc_cost_hkd = 0
            for h in acc['holdings']:
                if h['asset'] == 'USD 現金':
                    asset_value_hkd = h['quantity'] * rate
                    acc_value_hkd += asset_value_hkd
                    continue
                if h['asset'] in latest_prices:
                    h['current_price_usd'] = latest_prices[h['asset']]

                asset_value_hkd = h['quantity'] * h['current_price_usd'] * rate
                acc_value_hkd += asset_value_hkd
                acc_cost_hkd += h['quantity'] * h['avg_price_usd'] * rate

            acc['total_value_hkd'] = round(acc_value_hkd, 0)
            acc['total_cost_hkd'] = round(acc_cost_hkd, 0)
            acc['total_profit_hkd'] = round(acc_value_hkd - acc_cost_hkd, 0)
            total_value_hkd += acc_value_hkd
            total_cost_hkd += acc_cost_hkd

        data['portfolio_summary']['total_value_hkd'] = round(total_value_hkd, 0)
        data['portfolio_summary']['total_cost_hkd'] = round(total_cost_hkd, 0)
        data['portfolio_summary']['total_profit_hkd'] = round(total_value_hkd - total_cost_hkd, 0)

        # 5. 寫回 data.json
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return jsonify({"status": "success", **latest_prices})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    print(f"Admin token (X-Admin-Token header 需要): {ADMIN_TOKEN}")
    # v11.1: 只綁 localhost。唔再接受全網段任何人的寫入請求。
    app.run(host='127.0.0.1', port=5001)
