import json
import os

data_file = "/Users/tsy/.openclaw/workspace/tqqq-plan/data.json"

with open(data_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

data['daily_stats'] = {
    "date": "2026-08-24",
    "highest_profit_hkd": 72963,
    "lowest_profit_hkd": 14333,
    "highest_time": "21:30:09",
    "lowest_time": "22:20:08"
}

with open(data_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
