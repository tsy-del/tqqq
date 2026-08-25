import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os

repo_dir = "/Users/tsy/.openclaw/workspace/tqqq-plan"
history_file = os.path.join(repo_dir, "profit_history.json")

with open(history_file, 'r', encoding='utf-8') as f:
    history = json.load(f)

ny_tz = ZoneInfo("America/New_York")
hk_tz = ZoneInfo("Asia/Hong_Kong")

trading_date = datetime(2026, 8, 24, tzinfo=ny_tz)
start_time = trading_date.replace(hour=9, minute=30)
end_time = trading_date.replace(hour=20, minute=0) # Include after-hours if we want to track till next morning

start_ts = int(start_time.timestamp())
end_ts = int((trading_date + timedelta(days=1)).replace(hour=9, minute=29).timestamp())

session_data = [item for item in history if start_ts <= item['time'] <= end_ts]

if session_data:
    highest = max(session_data, key=lambda x: x['value'])
    lowest = min(session_data, key=lambda x: x['value'])
    print("Highest:")
    print(highest['value'], datetime.fromtimestamp(highest['time'], hk_tz).strftime('%Y-%m-%d %H:%M:%S'))
    print("Lowest:")
    print(lowest['value'], datetime.fromtimestamp(lowest['time'], hk_tz).strftime('%Y-%m-%d %H:%M:%S'))
else:
    print("No data")
