import json
import os
import subprocess

REPO_DIR = '/Users/tsy/.openclaw/workspace/tqqq-plan'
DATA_FILE = os.path.join(REPO_DIR, 'data.json')

with open(DATA_FILE, 'r') as f:
    data = json.load(f)

for acc in data['accounts']:
    if acc['account_name'] == '帳戶 C (中銀香港)':
        for holding in acc['holdings']:
            if holding['asset'] == 'SOXL':
                old_qty = holding['quantity']
                old_avg = holding['avg_price_usd']
                
                old_total_cost = old_qty * old_avg
                fee = 32
                new_total_cost = old_total_cost + fee
                new_avg = new_total_cost / old_qty
                
                holding['avg_price_usd'] = round(new_avg, 4)
                print(f"Updated SOXL in {acc['account_name']}: added $32 fee. Avg {old_avg} -> {holding['avg_price_usd']}")

with open(DATA_FILE, 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

subprocess.run(["git", "add", "data.json"], check=True, cwd=REPO_DIR)
subprocess.run(["git", "commit", "-m", "Add $32 fee to recent SOXL trade in Account C"], check=True, cwd=REPO_DIR)
subprocess.run(["git", "push"], check=True, cwd=REPO_DIR)
print("Pushed to github. Now running sync_prices.py...")
subprocess.run(["python3", "sync_prices.py"], check=True, cwd=REPO_DIR)
