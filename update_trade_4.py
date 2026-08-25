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
                
                add_qty = 20
                add_price = 108
                fee = 16
                
                new_qty = old_qty + add_qty
                new_total_cost = (old_qty * old_avg) + (add_qty * add_price) + fee
                new_avg = new_total_cost / new_qty
                
                holding['quantity'] = new_qty
                holding['avg_price_usd'] = round(new_avg, 4)
                print(f"Updated SOXL in {acc['account_name']}: {old_qty} -> {new_qty} shares, Avg {old_avg} -> {holding['avg_price_usd']}")

with open(DATA_FILE, 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

subprocess.run(["git", "add", "data.json"], check=True, cwd=REPO_DIR)
subprocess.run(["git", "commit", "-m", "Add 20 SOXL @ 108 plus $16 fee to Account C"], check=True, cwd=REPO_DIR)
subprocess.run(["git", "push"], check=True, cwd=REPO_DIR)
print("Pushed to github. Now running sync_prices.py...")
subprocess.run(["python3", "sync_prices.py"], check=True, cwd=REPO_DIR)
