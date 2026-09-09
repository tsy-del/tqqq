"""
price_fetcher.py — yfinance 價格抓取邏輯（從 sync_prices.py v8.2 拆出，項目 10）

負責：
- 抓取單一 ticker 的最新價格（含 pre/post market 判斷）
- 抓取 USD/HKD 匯率
- 批量抓取多個 symbol 的價格資料
"""
import time
import yfinance as yf


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


def get_latest_prices(symbols, script_version=""):
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
        prices[sym] = {'price': price, 'label': label, 'change_pct': chg_pct, 'prev_close': prev_close}
    return prices
