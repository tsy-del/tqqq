# TQQQ Plan - 系統文檔

> 最後更新：2026-08-25

---

## 📁 檔案結構

```
tqqq-plan/
├── sync_prices.py          # 核心腳本（生成 index.html + 更新 data.json）
├── data.json               # 持久化數據（持倉、價格、每日統計）
├── index.html              # 網頁前端（由 sync_prices.py 自動生成，勿手動改）
├── profit_history.json     # 利潤歷史記錄（用於圖表）
├── trigger_server.py       # 本地 Proxy Server（接收按鈕請求 trigger GitHub Actions）
├── sync.log                # Cron Job 執行日誌
├── .env                    # 本地環境變量（含 GITHUB_TOKEN，勿上傳）
├── .github/
│   └── workflows/
│       └── sync.yml        # GitHub Actions 工作流（手動觸發）
└── SYSTEM_DOC.md           # 本文檔
```

---

## 🗂️ 核心版本歷史

| 版本 | 主要改動 |
|------|---------|
| v5.6 | 基礎版本，自動抓取股價、計算利潤、生成 UI |
| v5.7 | 加入 Trading Date Logic（美國東岸時間日期分界）|
| v5.8 | 修復 daily_stats 邏輯：改用美國東岸時間 00:00~23:59 做一日，正確追蹤最高/最低利潤；修復手動觸發按鈕 |

---

## ⚙️ 核心邏輯（sync_prices.py）

### 執行流程
1. `git fetch` + `git reset --hard origin/main`（強制同步 GitHub，防 push conflict）
2. 讀取 `data.json`（持倉資料）
3. 用 yfinance 抓取最新股價（TQQQ, SOXL, SPCH 等）
4. 計算各帳戶市值、成本、利潤
5. 更新 `daily_stats`（今日最高/最低利潤）
6. 更新 `history_stats`（歷史最高/最低利潤）
7. 更新 `profit_history.json`（圖表數據）
8. 生成 `index.html`
9. `git commit` + `git push` 到 main + gh-pages

### Daily Stats 邏輯（v5.8）
- 用**美國東岸時間 (America/New_York) 00:00~23:59** 做一日
- 每次執行比較當前利潤同 `highest_profit_hkd` / `lowest_profit_hkd`
- 日期切換時自動重置

### 價格抓取邏輯
- 優先順序：PRE > POST > currentPrice > regularMarketPrice
- 市場狀態：PRE/PREPRE → 盤前價；POST/POSTPOST/CLOSED → 盤後價；REG → 正常收市價
- 失敗自動重試 3 次（每次間隔 5 秒）

### 重要規則（CRITICAL）
⚠️ **勿直接修改 `index.html` 或 `script.js`**，所有 UI 改動必須喺 `sync_prices.py` 入面修改，因為每次執行都會重新生成 `index.html`。

⚠️ **修改 `sync_prices.py` 後必須先 `git push` 到 GitHub，再執行腳本**，否則腳本開頭嘅 `git reset --hard` 會覆蓋本地修改。

⚠️ **每次改動 UI/邏輯必須遞增 `SCRIPT_VERSION`**（e.g. v5.8 → v5.9）。

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
  }
}
```

---

## 🌐 外部 API

| API | 用途 | 備註 |
|-----|------|------|
| yfinance (PyPI) | 抓取美股即時/盤前/盤後股價 | 免費，無需 API Key |
| Finnhub API | 網頁前端即時價格更新 | API Key 存喺 sync_prices.py 內 |
| GitHub API | 手動觸發 GitHub Actions | Token: `ghp_Fv…tDs7`，存喺 trigger_server.py |

---

## 🤖 GitHub Actions

- **檔案**：`.github/workflows/sync.yml`
- **觸發方式**：手動 (`workflow_dispatch`)
- **功能**：喺 GitHub 雲端執行 `sync_prices.py`，更新價格並 push 到 gh-pages
- **用途**：當本地 Cron Job 唔運作時（例如電腦關機），可以手動從雲端更新

---

## ⏰ 本地 Cron Job 時間表

| 時間 (HKT) | 頻率 | 說明 |
|-----------|------|------|
| 21:00, 21:15 | 各一次 | 開盤前預熱 |
| 21:30–21:55 | 每 5 分鐘 | 開盤初段高頻更新 |
| 22:00–00:00 | 每 5 分鐘 | 正常交易時段 |
| 01:00–20:00 | 每 15 分鐘 | 盤前/盤後/非交易時段 |

---

## 🖥️ 本地服務

### Trigger Proxy Server
- **檔案**：`trigger_server.py`
- **Port**：`19999`
- **功能**：接收網頁按鈕請求，用 GitHub Token trigger GitHub Actions workflow
- **自動啟動**：LaunchAgent `~/Library/LaunchAgents/ai.tqqq.triggerserver.plist`
- **Log**：`trigger_server.log`

---

## 🚀 重建步驟（從零開始）

1. **Clone repo**
   ```bash
   git clone git@github.com:tsy-del/tqqq.git tqqq-plan
   cd tqqq-plan
   ```

2. **安裝依賴**
   ```bash
   pip3 install yfinance
   ```

3. **設定 GitHub Token（手動觸發按鈕用）**
   - 在 `trigger_server.py` 第 10 行填入 GitHub Personal Access Token
   - Token 需要 `workflow` 權限

4. **設定 LaunchAgent（本地 proxy server 自動啟動）**
   ```bash
   cp ai.tqqq.triggerserver.plist ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/ai.tqqq.triggerserver.plist
   ```

5. **設定 Cron Job**
   ```bash
   crontab -e
   # 參考上方時間表
   ```

6. **測試執行**
   ```bash
   python3 sync_prices.py
   ```

---

## 🌍 網頁地址

- **GitHub Pages**：`https://tsy-del.github.io/tqqq/`
- **Repo**：`https://github.com/tsy-del/tqqq`
