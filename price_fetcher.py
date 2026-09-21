"""
price_fetcher.py — 價格抓取邏輯（項目 10 拆分；v9.4 加入 Futu OpenAPI 主來源）

負責：
- 抓取單一 ticker 的最新價格（含 pre/post market 判斷）
- 抓取 USD/HKD 匯率
- 批量抓取多個 symbol 的價格資料

來源優先順序：
- Futu OpenAPI（透過本機 OpenD，需已登入並啟動）為主要來源
- yfinance 為 Futu 連線失敗時的 fallback（例如 OpenD 未啟動）
"""
import time
import yfinance as yf

try:
    import futu as ft
    _FUTU_AVAILABLE = True
except ImportError:
    _FUTU_AVAILABLE = False

FUTU_HOST = '127.0.0.1'
FUTU_PORT = 11111


def fetch_best_price(info, fast_price):
    pre = info.get('preMarketPrice')
    post = info.get('postMarketPrice')
    reg = info.get('regularMarketPrice')
    current = info.get('currentPrice')

    market_state = info.get('marketState', '').upper()

    if market_state in ('PRE', 'PREPRE') and pre is not None and pre > 0:
        return round(pre, 2)
    if market_state in ('POST', 'POSTPOST', 'CLOSED') and post is not None and post > 0:
        return round(post, 2)

    if current is not None and current > 0:
        return round(current, 2)

    if pre is not None and pre > 0 and pre != reg:
        return round(pre, 2)
    if post is not None and post > 0 and post != reg:
        return round(post, 2)

    if reg is not None and reg > 0:
        return round(reg, 2)

    # Last resort: prefer last traded price, then ask/bid
    for p in [fast_price, info.get('ask'), info.get('bid')]:
        if p is not None and p > 0:
            return round(p, 2)
    return 0


def get_ticker_data(symbol, retries=3, delay=5):
    """Fetch ticker info with retry, since yfinance occasionally fails or returns empty data."""
    last_err = None
    for attempt in range(retries):
        try:
            t = yf.Ticker(symbol)
            info = t.info
            try:
                fast_price = t.fast_info.last_price
            except Exception:
                fast_price = None
            if info and (info.get('regularMarketPrice') or info.get('currentPrice') or fast_price):
                return info, fast_price
        except Exception as e:
            last_err = e
        print(f"Retry {attempt + 1}/{retries} for {symbol}...")
        time.sleep(delay)
    raise RuntimeError(f"Failed to fetch valid data for {symbol}: {last_err}")


def fetch_usd_hkd_rate(fallback=7.8):
    """Fetch live USD/HKD rate from yfinance. Falls back to previous value on failure."""
    for attempt in range(3):
        try:
            t = yf.Ticker("HKD=X")
            info = t.info
            candidates = [
                info.get('regularMarketPrice'),
                info.get('bid'),
                info.get('ask'),
                info.get('previousClose'),
            ]
            try:
                candidates.insert(0, t.fast_info.last_price)
            except Exception:
                pass
            for c in candidates:
                if c and 7.0 < float(c) < 8.5:
                    return round(float(c), 4)
        except Exception:
            pass
        time.sleep(2)
    print(f"WARN: USD/HKD fetch failed, using fallback {fallback}")
    return fallback


def _fetch_prices_via_futu(symbols):
    """透過 Futu OpenD 抓取市場快照，回傳格式與 get_latest_prices 一致的 dict。
    連線或任何 symbol 出錯時拋出例外，由呼叫方 fallback 去 yfinance。"""
    if not _FUTU_AVAILABLE:
        raise RuntimeError("futu-api SDK 未安裝")

    futu_codes = [f"US.{s}" for s in symbols]
    quote_ctx = ft.OpenQuoteContext(host=FUTU_HOST, port=FUTU_PORT)
    try:
        ret, data = quote_ctx.get_market_snapshot(futu_codes)
        if ret != ft.RET_OK:
            raise RuntimeError(f"Futu get_market_snapshot 失敗: {data}")

        ret_state, state = quote_ctx.get_global_state()
        market_us = state.get('market_us', '').upper() if ret_state == ft.RET_OK else ''
    finally:
        quote_ctx.close()

    prices = {}
    for sym in symbols:
        code = f"US.{sym}"
        row = data[data['code'] == code]
        if row.empty:
            raise RuntimeError(f"Futu 快照無 {code} 資料")
        row = row.iloc[0]

        last_price = float(row['last_price'])
        prev_close = float(row['prev_close_price'])
        pre_price = row.get('pre_price')
        after_price = row.get('after_price')
        overnight_price = row.get('overnight_price')

        def _valid(p):
            return p is not None and p == p and float(p) > 0

        # v10.10: 盤前/盤後成交極稀薄，個別細單掛盤可令 pre_price/after_price
        # 大幅脫離現實（曾出現對比昨日收市 +15% 嘅離譜報價）。偏離 prev_close
        # 超過此百分比時，視為不可靠報價，唔用嚟顯示。
        EXT_HOURS_SANITY_PCT = 8.0

        def _sane_ext(p):
            if not _valid(p) or prev_close <= 0:
                return False
            return abs(float(p) - prev_close) / prev_close * 100 <= EXT_HOURS_SANITY_PCT

        # 根據 Futu 回傳嘅實際市場狀態（market_us）決定顯示邊個時段嘅價，
        # 而唔係靠「欄位有冇值」猜——因為 pre_price/after_price/overnight_price
        # 一旦喺某個時段出現過數值，過咗時段之後都唔會自動清空，
        # 純粹靠有效值判斷會導致夜盤結束、盤前已開始時仍錯誤顯示夜盤價。
        if market_us in ('PRE_MARKET_BEGIN', 'PRE_MARKET_END') and _valid(pre_price) and not _sane_ext(pre_price):
            # 盤前報價偏離收市價過大，唔可靠，改用最後正式成交價，標籤保留 PRE
            price = round(last_price, 2) if last_price > 0 else 0
            label = "PRE"
        elif market_us in ('PRE_MARKET_BEGIN', 'PRE_MARKET_END') and _valid(pre_price):
            price = round(float(pre_price), 2)
            label = "PRE"
        elif market_us in ('AFTER_HOURS_BEGIN', 'AFTER_HOURS_END') and _valid(after_price) and not _sane_ext(after_price):
            price = round(last_price, 2) if last_price > 0 else 0
            label = "AFTER"
        elif market_us in ('AFTER_HOURS_BEGIN', 'AFTER_HOURS_END') and _valid(after_price):
            price = round(float(after_price), 2)
            label = "AFTER"
        elif market_us in ('NIGHT_OPEN', 'NIGHT_END') and _valid(overnight_price):
            price = round(float(overnight_price), 2)
            label = "NIGHT"
        elif market_us == 'MORNING' and _valid(overnight_price):
            # 夜盤延續到開市前一刻，Futu 未必即時切換狀態，仍容許 overnight 價
            price = round(float(overnight_price), 2)
            label = "NIGHT"
        else:
            price = round(last_price, 2) if last_price > 0 else 0
            label = "REG"

        if price <= 0:
            raise RuntimeError(f"Futu 回傳無效價格 {code}: {last_price}")

        chg_pct = ((price - prev_close) / prev_close * 100) if prev_close > 0 else 0

        prices[sym] = {'price': price, 'label': label, 'change_pct': chg_pct, 'prev_close': prev_close, 'source': '牛牛'}
    return prices


def get_latest_prices(symbols, script_version=""):
    try:
        print(f"Fetching prices ({script_version}) from Futu OpenAPI for {symbols}...")
        return _fetch_prices_via_futu(symbols)
    except Exception as e:
        print(f"WARN: Futu OpenAPI 抓取失敗（{e}），改用 yfinance fallback...")
        return _get_latest_prices_yfinance(symbols, script_version=script_version)


def _get_latest_prices_yfinance(symbols, script_version=""):
    print(f"Fetching highest frequency prices ({script_version}) from yfinance for {symbols}...")
    prices = {}
    for sym in symbols:
        info, fast = get_ticker_data(sym)
        price = fetch_best_price(info, fast)
        if price <= 0:
            raise RuntimeError(f"Invalid price fetched for {sym}. Aborting update.")

        reg = info.get('regularMarketPrice') or price

        # Calculate change percentage based on market state
        market_state = info.get('marketState', '').upper()
        # Reference price logic:
        # In PRE/POST, we want to see the change relative to the last regular close (regularMarketPrice)
        # In REG/CLOSED, we want to see the change relative to the previous day's close (previousClose)
        if market_state in ('PRE', 'PREPRE', 'POST', 'POSTPOST'):
            ref_price = info.get('regularMarketPrice')
        else:
            ref_price = info.get('previousClose')

        if not ref_price or ref_price <= 0:
            ref_price = info.get('previousClose') or info.get('regularMarketPrice') or price

        chg_pct = ((price - ref_price) / ref_price * 100) if ref_price > 0 else 0

        label = "EXT" if abs(price - reg) > 0.01 else "REG"
        # v6.9: 存下 yfinance 嘅 previousClose，用嚟前端計 % 变動，
        # 唔再信 Finnhub 自己嘅 pc（發現嘅 SOXL previousClose 持續性錯誤）。
        prev_close = info.get('previousClose') or ref_price
        prices[sym] = {'price': price, 'label': label, 'change_pct': chg_pct, 'prev_close': prev_close, 'source': 'Yahoo'}
    return prices
