# TQQQ Plan - 系統文檔

> 最後更新：2026-09-09（v9.1）

---

## 📁 檔案結構

```
tqqq-plan/
├── sync_prices.py           # 主入口：路徑設定、git 操作、流程整合、寫檔與 commit/push（~200行）
├── price_fetcher.py         # 股價/匯率抓取（yfinance）
├── portfolio_calculator.py  # 持倉市值/利潤/里程碑計算
├── trade_manager.py         # 交易明細（trades.json）讀取與渲染
├── html_renderer.py         # index.html 生成（HTML/CSS/JS 模板）
├── data.json                # 持久化數據（持倉、價格、每日統計）
├── trades.json              # 交易明細帳本
├── profit_history.json      # 利潤歷史記錄（用於圖表）
├── index.html               # 網頁前端（由 sync_prices.py 自動生成，勿手動改）
├── .sync.lock                # 執行期間鎖檔（防止兩個 sync 同時跑），內容為空，勿手動刪
├── admin.html / api_server.py  # 本地 Admin UI（http://localhost:5001，手動輸入交易用）
├── script.js / style.css    # 舊版殘留檔案，目前生成的 index.html 已不再引用，可忽略
├── .gitignore                # 排除 .env、*.log、*.bak 等
├── .github/
│   └── workflows/
│       └── sync.yml          # GitHub Actions 工作流（手動觸發 workflow_dispatch）
└── SYSTEM_DOC.md             # 本文檔
```

**已移除（v9.1 清理，項目 12）：** `trigger_server.py`（本地 proxy server，含硬 code GitHub Token）及對應 launchd job `ai.tqqq.triggerserver`、`.env`、大量一次性 `patch_*.py`/`fix_*.py`/`test*.py`/`debug_*.html` 腳本、`backups/` 內 14 個舊版本檔案。網頁上「手動觸發」按鈕已改為直接連去 GitHub Actions 頁面，唔再依賴本地 server。

---

## 🗂️ 核心版本歷史

| 版本 | 主要改動 |
|------|---------|
| v5.6 | 基礎版本，自動抓取股價、計算利潤、生成 UI |
| v5.7 | 加入 Trading Date Logic（美國東岸時間日期分界）|
| v5.8 | 修復 daily_stats 邏輯：改用美國東岸時間 00:00~23:59 做一日 |
| v8.0 | 新增交易明細（`trades.json`）、交易 tab、未實現/已實現利潤分開顯示 |
| v8.2 | 新增風險指標 tab、圖表時間範圍按鈕、`sync_status` 同步狀態追蹤 |
| v9.0 | **拆分模組**：原 1203 行單一 `sync_prices.py` 拆成 5 個檔案（見上方檔案結構） |
| v9.1 | 加 lock file 防止並行執行衝突；開頭改為只 `checkout` 指定生成檔案，唔再 `reset --hard` 全 repo；清理殘留檔案同 `.gitignore` |

---

## ⚙️ 核心邏輯（sync_prices.py 整合流程）

### 執行流程
1. 取得 `.sync.lock` 檔案鎖（`fcntl.flock` 非阻塞）；攞唔到鎖即代表另一個 sync 正在跑，直接跳過本次執行並正常結束（不算失敗）
2. 若非 GitHub Actions 環境：`git fetch` + `git checkout origin/main -- <指定生成檔案清單>`（**只**還原 `data.json`、`index.html`、`profit_history.json`、`sync_prices.py`、`price_fetcher.py`、`portfolio_calculator.py`、`trade_manager.py`、`html_renderer.py` 呢 8 個由 script 自動生成/管理嘅檔案；`trades.json` 等手動維護嘅資料檔案**不會**被覆蓋，防止手動編輯被清走）
3. 讀取 `data.json`（持倉資料）+ `trades.json`（交易明細，經 `trade_manager.load_trades_ledger`）
4. 用 `price_fetcher.get_latest_prices` 抓取最新股價（TQQQ, SOXL, SPCH 等）+ USD/HKD 匯率
5. 用 `portfolio_calculator` 計算市值/成本/利潤、更新 `daily_stats`/`history_stats`/里程碑進度
6. 更新 `profit_history.json`（含分層降採樣，避免檔案無限增長）
7. 用 `html_renderer.render_page` 生成新 `index.html`
8. 寫入 `data.json`、`index.html`，`git add` + 若有變動則 `commit` + `push` 到 `main` 同強推 `gh-pages`
9. 釋放鎖檔

### Daily Stats 邏輯（沿用 v5.8）
- 用**美國東岸時間 (America/New_York) 00:00~23:59** 做一日
- 每次執行比較當前利潤同 `highest_profit_hkd` / `lowest_profit_hkd`
- 日期切換時自動重置

### 價格抓取邏輯（price_fetcher.py）
- 優先順序：PRE > POST > currentPrice > regularMarketPrice
- 市場狀態：PRE/PREPRE → 盤前價；POST/POSTPOST/CLOSED → 盤後價；REG → 正常收市價
- 失敗自動重試

### 重要規則（CRITICAL）
⚠️ **勿直接修改 `index.html`、`script.js`、`style.css`**，所有 UI 改動必須喺 `html_renderer.py` 入面修改，因為每次執行都會重新生成 `index.html`（`script.js`/`style.css` 已不再被引用）。

⚠️ **修改任何 `.py` 檔案（`sync_prices.py`、`price_fetcher.py`、`portfolio_calculator.py`、`trade_manager.py`、`html_renderer.py`）後必須先 `git commit` + `git push` 到 GitHub main，再執行 `python3 sync_prices.py`**。原因：script 開頭嗰個 `git checkout origin/main -- <生成檔案>` 步驟會用 GitHub 上嘅版本覆蓋呢幾個檔案嘅本地改動（唯獨唔會動 `trades.json`）。若先跑 script 未 push，本地改動會被 GitHub 上舊版蓋走。

⚠️ **每次改動邏輯/UI 必須遞增 `SCRIPT_VERSION`**（喺 `sync_prices.py` 頂部，e.g. v9.1 → v9.2）。

⚠️ **拆分後嘅模組改動要做 dry-run 驗證**：修改 `html_renderer.py`/`portfolio_calculator.py` 等後，建議先用一次性 script 呼叫 `render_page()` 產生 HTML，比對關鍵標記（例如 `tab-risk`、`Trade Records`、`sync_status`、`milestone-card`）確認冇漏功能，先正式跑 `sync_prices.py`。

---

## 📊 data.json 結構

```json
{
  "last_updated": "YYYY-MM-DD HH:MM:SS",
  "market_prices": {
    "tqqq_usd": 0.00,
    "soxl_usd": 0.00,
    "spcx_usd": 0.00,
    "spch_usd": 0.00,
    "usd_hkd_rate": 7.8
  },
  "portfolio_summary": {
    "total_value_hkd": 0,
    "total_cost_hkd": 0,
    "total_profit_hkd": 0
  },
  "accounts": [
    {
      "account_name": "帳戶名稱",
      "holdings": [
        {
          "asset": "TQQQ",
          "quantity": 0,
          "avg_price_usd": 0.00,
          "current_price_usd": 0.00
        }
      ]
    }
  ],
  "daily_stats": {
    "date": "YYYY-MM-DD",
    "highest_profit_hkd": 0,
    "lowest_profit_hkd": 0
  },
  "history_stats": {
    "highest_profit_hkd": 0,
    "highest_profit_date": "YYYY-MM-DD HH:MM:SS",
    "lowest_profit_hkd": 0,
    "lowest_profit_date": "YYYY-MM-DD HH:MM:SS"
  },
  "sync_status": {
    "last_attempt": "YYYY-MM-DD HH:MM:SS",
    "last_success": "YYYY-MM-DD HH:MM:SS",
    "api_status": "success",
    "yfinance_status": "ok",
    "github_push_status": "pending"
  }
}
```

`trades.json` 為獨立交易明細帳本，格式見檔案內容；由 `trade_manager.load_trades_ledger` 讀取，**不會**被 sync 腳本開頭嘅 git checkout 覆蓋。

---

## 🌐 外部 API

| API | 用途 | 備註 |
|-----|------|------|
| yfinance (PyPI) | 抓取美股即時/盤前/盤後股價 | 免費，無需 API Key，`price_fetcher.py` |
| Finnhub API | 網頁前端即時價格更新（JS） | API Key 存喺 `html_renderer.py` 生成嘅 JS 內 |
| GitHub Actions API | 手動觸發雲端更新 | 由使用者手動喺 GitHub 網頁按 "Run workflow"，唔再需要本地 Token/server |

---

## 🤖 GitHub Actions（手動觸發）

- **檔案**：`.github/workflows/sync.yml`
- **觸發方式**：手動 (`workflow_dispatch`)，喺 GitHub repo 頁面 → Actions → "Sync Prices (Manual Only)" → "Run workflow"
- **執行環境**：Ubuntu + Python 3.10，`pip install yfinance`，跑 `python sync_prices.py`
- **用途**：當本地 Cron Job 唔運作時（例如電腦關機），可以手動從雲端更新
- **v9.1 拆分後驗證**：Actions checkout main 時會攞齊全部 5 個 `.py` 模組（已用 `git ls-files` 確認全部 tracked），`sync_prices.py` 用相對 import，喺 repo 根目錄執行下正常運作；Actions 環境有 `GITHUB_ACTIONS` env var，會自動跳過本地專用嘅 checkout-reset 步驟

---

## ⏰ 本地 Cron Job 時間表（2026-09-09 更新）

```
PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin

# 一般時段：每 15 分鐘（04:00-20:59 HKT）
*/15 4-20 * * * cd /Users/tsy/.openclaw/workspace/tqqq-plan && /usr/bin/python3 sync_prices.py >> /Users/tsy/.openclaw/workspace/tqqq-plan/cron.log 2>&1
# 美股開市密集時段：每 5 分鐘（21:00-03:59 HKT，大約覆蓋 9:30am-4pm ET）
*/5 21-23,0-3 * * * cd /Users/tsy/.openclaw/workspace/tqqq-plan && /usr/bin/python3 sync_prices.py >> /Users/tsy/.openclaw/workspace/tqqq-plan/cron.log 2>&1
```

檢查方式：`crontab -l`。編輯方式：`crontab -e`（唔好直接覆蓋整個 crontab，會影響其他 job）。

**已移除**：舊版 `trigger_server.py`（port 19999 本地 proxy）同對應 launchd job `ai.tqqq.triggerserver`，已於 2026-09-09 unload + 刪除，唔再需要。

---

## 🚀 重建步驟（從零開始 / 壞咗跟住裝返）

### 方法一：從 Git 重建（優先，最新版）
1. **Clone repo**
   ```bash
   cd /Users/tsy/.openclaw/workspace
   git clone git@github.com:tsy-del/tqqq.git tqqq-plan
   cd tqqq-plan
   ```
2. **安裝依賴**
   ```bash
   pip3 install yfinance
   ```
3. **確認檔案齊全**（應有以下 5 個 `.py` 模組 + 3 個 `.json` 資料檔）
   ```bash
   ls sync_prices.py price_fetcher.py portfolio_calculator.py trade_manager.py html_renderer.py data.json trades.json profit_history.json
   ```
4. **設定 Cron Job**（見上方時間表）
   ```bash
   crontab -e
   ```
5. **測試執行**
   ```bash
   python3 sync_prices.py
   ```
   應輸出 `Update and push completed successfully.` 或 `No changes to commit.`（如剛巧價格未變）

### 方法二：從本地 tar.gz 備份還原（Git repo 損壞時；備份不含 .git，還原後需重新設定 remote）
1. 備份存放於 `/Users/tsy/.openclaw/workspace/tqqq-plan-backups/tqqq-plan_v9.1_<timestamp>.tar.gz`
2. 還原：
   ```bash
   cd /Users/tsy/.openclaw/workspace
   mv tqqq-plan tqqq-plan.broken   # 保留壞咗嗰份，唔好直接刪
   tar -xzf tqqq-plan-backups/tqqq-plan_v9.1_<timestamp>.tar.gz
   cd tqqq-plan
   git init
   git remote add origin git@github.com:tsy-del/tqqq.git
   git fetch origin
   git checkout -b main --track origin/main   # 若本地檔案與 GitHub 一致
   ```
3. 之後同方法一步驟 4-5

### ⚠️ 唔要做嘅事
- 唔要跳過先 commit+push source 就直接執行 `sync_prices.py` 改 `.py` 檔案（會被覆蓋，見上方 CRITICAL 規則）
- 唔要手動刪 `.sync.lock`（除非確認冇任何 sync process 正在跑，否則可能同執行中嘅 process 打架；正常情況 script 執行完會自動釋放）
- 唔要直接改 `index.html`（下次 sync 會覆蓋）

---

## 🌍 網頁地址

- **GitHub Pages**：`https://tsy-del.github.io/tqqq/`
- **Repo**：`https://github.com/tsy-del/tqqq`
