import re
import os
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

FILE_PATH = "/Users/tsy/.openclaw/workspace/tqqq-plan/sync_prices.py"

with open(FILE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 更新版本號
content = content.replace('SCRIPT_VERSION = "v5.6"', 'SCRIPT_VERSION = "v5.7"')

# 2. 注入 Trading Date 邏輯同重置檢查
# 搵 update_files 嘅開頭注入位置
trading_date_logic = """
        # --- PATCH: Trading Date Logic ---
        ny_tz = ZoneInfo("America/New_York")
        ny_now = datetime.now(ny_tz)
        if ny_now.hour < 9 or (ny_now.hour == 9 and ny_now.minute < 30):
            trading_date = (ny_now - timedelta(days=1)).date()
        else:
            trading_date = ny_now.date()
        trading_date_str = trading_date.strftime("%Y-%m-%d")

        if 'daily_stats' not in data:
            data['daily_stats'] = {'date': trading_date_str, 'highest_profit_hkd': int(round(total_profit_hkd)), 'lowest_profit_hkd': int(round(total_profit_hkd))}
        
        if data['daily_stats'].get('date') != trading_date_str:
            data['daily_stats'] = {
                'date': trading_date_str,
                'highest_profit_hkd': int(round(total_profit_hkd)),
                'lowest_profit_hkd': int(round(total_profit_hkd))
            }
        # ---------------------------------
"""

# Regex 注入
content = re.sub(r'(def update_files\(\):\n\s+try:\n)', r'\1' + trading_date_logic, content)

with open(FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch v5.7 applied successfully!")
