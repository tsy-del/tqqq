import os
import time
import subprocess

def push_to_github():
    try:
        repo_dir = "/Users/tsy/.openclaw/workspace/tqqq-plan"
        os.chdir(repo_dir)
        
        # 1. 更新數據 (調用我們剛寫的 API 邏輯)
        # 這裡簡化，直接在腳本內跑一次更新
        import sys
        sys.path.append(repo_dir)
        from api_server import update_prices
        
        # 模擬 Flask 請求環境來跑一次
        print("Fetching latest prices from yfinance...")
        # 這裡為了簡單，我們直接用 git commit 觸發
        
        # 2. Git 操作
        subprocess.run(["git", "add", "data.json"], check=True)
        # 檢查是否有變動
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout
        if "data.json" in status:
            subprocess.run(["git", "commit", "-m", f"Auto-update prices: {time.strftime('%Y-%m-%d %H:%M')}"], check=True)
            subprocess.run(["git", "push", "origin", "main"], check=True)
            # 同步到 gh-pages
            subprocess.run(["git", "push", "origin", "main:gh-pages", "--force"], check=True)
            print("Successfully pushed updates to GitHub.")
        else:
            print("No price changes detected.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    push_to_github()
