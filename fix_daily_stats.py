import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os

repo_dir = "/Users/tsy/.openclaw/workspace/tqqq-plan"
data_file = os.path.join(repo_dir, "data.json")
history_file = os.path.join(repo_dir, "profit_history.json")

with open(data_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

with open(history_file, 'r', encoding='utf-8') as f:
    history = json.load(f)

ny_tz = ZoneInfo("America/New_York")
hk_tz = ZoneInfo("Asia/Hong_Kong")
ny_now = datetime.now(ny_tz)

if ny_now.hour < 9 or (ny_now.hour == 9 and ny_now.minute < 30):
    trading_date = ny_now - timedelta(days=1)
else:
    trading_date = ny_now
    
trading_date_str = trading_date.strftime('%Y-%m-%d')

# The trading session in HKT:
# NY 09:30 is HKT 21:30 (usually, depending on DST). Let's just use exact unix timestamps.
session_start_ny = trading_date.replace(hour=9, minute=30, second=0, microsecond=0)
session_end_ny = trading_date.replace(hour=16, minute=0, second=0, microsecond=0) # roughly, maybe extended hours till next morning

start_ts = int(session_start_ny.timestamp())
# For current daily stats, it includes everything from session start to NOW
end_ts = int(datetime.now().timestamp())

session_data = [item for item in history if start_ts <= item['time'] <= end_ts]

if session_data:
    highest = max(session_data, key=lambda x: x['value'])
    lowest = min(session_data, key=lambda x: x['value'])
    
    data['daily_stats'] = {
        "date": trading_date_str,
        "highest_profit_hkd": highest['value'],
        "lowest_profit_hkd": lowest['value'],
        "highest_time": datetime.fromtimestamp(highest['time'], hk_tz).strftime('%H:%M:%S'),
        "lowest_time": datetime.fromtimestamp(lowest['time'], hk_tz).strftime('%H:%M:%S')
    }
else:
    print("No data for current session")

with open(data_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    
print(f"Updated daily_stats for {trading_date_str}: High {data['daily_stats']['highest_profit_hkd']}, Low {data['daily_stats']['lowest_profit_hkd']}")
