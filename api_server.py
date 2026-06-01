import yfinance as yf
from flask import Flask, jsonify
from flask_cors import CORS
import os
import json
import time

app = Flask(__name__)
CORS(app)

# 你的靜態數據路徑
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data.json')

@app.route('/api/update_prices')
def update_prices():
    try:
        # 1. 讀取現有的 data.json
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        
        # 2. 調用 yfinance 獲取最新價格
        tqqq = yf.Ticker("TQQQ")
        soxl = yf.Ticker("SOXL")
        
        tqqq_price = round(tqqq.fast_info.last_price, 2)
        soxl_price = round(soxl.fast_info.last_price, 2)
        
        # 3. 更新數據
        data['market_prices']['tqqq_usd'] = tqqq_price
        data['market_prices']['soxl_usd'] = soxl_price
        data['last_updated'] = time.strftime('%Y-%m-%dT%H:%M:%S+08:00')
        
        # 4. 重新計算盈虧 (Portfolio Summary)
        total_value_hkd = 0
        total_cost_hkd = 0
        rate = data['market_prices']['usd_hkd_rate']
        
        for acc in data['accounts']:
            acc_value_hkd = 0
            for h in acc['holdings']:
                if h['asset'] == 'TQQQ': h['current_price_usd'] = tqqq_price
                if h['asset'] == 'SOXL': h['current_price_usd'] = soxl_price
                
                asset_value_hkd = h['quantity'] * h['current_price_usd'] * rate
                acc_value_hkd += asset_value_hkd
                total_cost_hkd += h['quantity'] * h['avg_price_usd'] * rate
            
            acc['total_value_hkd'] = round(acc_value_hkd, 0)
            acc['total_profit_hkd'] = round(acc_value_hkd - acc['total_cost_hkd'], 0)
            total_value_hkd += acc_value_hkd
            
        data['portfolio_summary']['total_value_hkd'] = round(total_value_hkd, 0)
        data['portfolio_summary']['total_profit_hkd'] = round(total_value_hkd - total_cost_hkd, 0)
        
        # 5. 寫回 data.json
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        return jsonify({"status": "success", "tqqq": tqqq_price, "soxl": soxl_price})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
