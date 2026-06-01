import yfinance as yf
from flask import Flask, jsonify
from flask_cors import CORS
import threading

app = Flask(__name__)
CORS(app)  # 解決網頁跨域問題

@app.route('/api/tqqq')
def get_tqqq():
    try:
        tqqq = yf.Ticker("TQQQ")
        # 獲取最新價格
        data = tqqq.fast_info
        price = data.last_price
        prev_close = data.previous_close
        change = ((price - prev_close) / prev_close) * 100
        
        return jsonify({
            "price": round(price, 2),
            "change": round(change, 2),
            "time": data.last_volume # 或是其他時間戳
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # 預設在 5001 端口運行
    app.run(host='0.0.0.0', port=5001)
