import re
import os

FILE_PATH = "/Users/tsy/.openclaw/workspace/tqqq-plan/sync_prices.py"

with open(FILE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# 移除錯誤位置的 Patch
content = re.sub(r'\s*# --- PATCH: Trading Date Logic ---.*?# ---------------------------------\n', '\n', content, flags=re.DOTALL)

# 注入正確位置的 Patch (在 total_profit_hkd 計算之後)
injection = "data['portfolio_summary']['total_profit_hkd'] = int(round(total_profit_hkd))"
new_block = """
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
        else:
            if int(round(total_profit_hkd)) > data['daily_stats']['highest_profit_hkd']:
                data['daily_stats']['highest_profit_hkd'] = int(round(total_profit_hkd))
            if int(round(total_profit_hkd)) < data['daily_stats']['lowest_profit_hkd']:
                data['daily_stats']['lowest_profit_hkd'] = int(round(total_profit_hkd))
        # ---------------------------------
"""
if "# --- PATCH: Trading Date Logic ---" not in content:
    content = content.replace(injection, injection + "\n" + new_block)

with open(FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(content)
