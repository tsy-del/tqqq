import json
import os
import subprocess

# Path configurations
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(REPO_DIR, 'data.json')

def run_git(args, **kwargs):
    return subprocess.run(["git"] + args, check=True, cwd=REPO_DIR, **kwargs)

def update_spch_avg():
    # Force sync with GitHub before editing
    print("Syncing with GitHub...")
    run_git(["fetch", "origin", "main"])
    run_git(["reset", "--hard", "origin/main"])

    if not os.path.exists(DATA_FILE):
        print("data.json not found")
        return

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 1. Find the SPCH holding in Account D (HSBC)
    target_account_name = "帳戶 D (滙豐 - P683880)"
    account_d = next((acc for acc in data['accounts'] if acc['account_name'] == target_account_name), None)
    
    if not account_d:
        print(f"Account {target_account_name} not found")
        return

    spch_holding = next((h for h in account_d['holdings'] if h['asset'] == 'SPCH'), None)
    
    if not spch_holding:
        print("SPCH holding not found in Account D")
        return

    # 2. Calculate new quantity and average price
    # Old: 150 shares @ 19.52
    # New: Buy 50 shares @ 16.98
    old_qty = 150
    old_avg = 19.52
    buy_qty = 50
    buy_price = 16.98

    new_qty = old_qty + buy_qty
    total_cost = (old_qty * old_avg) + (buy_qty * buy_price)
    new_avg = round(total_cost / new_qty, 4)

    print(f"Updating SPCH: {old_qty} shares -> {new_qty} shares")
    print(f"Updating Avg Price: {old_avg} -> {new_avg}")

    spch_holding['quantity'] = new_qty
    spch_holding['avg_price_usd'] = new_avg

    # 3. Save and Push
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("Data saved. Committing and pushing...")
    run_git(["add", "data.json"])
    run_git(["commit", "-m", f"Update HSBC SPCH: +50 shares @ 16.98 (New Avg: {new_avg})"])
    run_git(["push", "origin", "main"])
    print("Push successful. Now run sync_prices.py to update UI.")

if __name__ == "__main__":
    update_spch_avg()
