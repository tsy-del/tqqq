"""
kline_fetcher.py — 用 Futu OpenAPI 拉歷史日 K 線，輸出 kline.json 供前端畫圖。

設計重點：
- `request_history_kline()` 唔佔訂閱額度，但有頻率限制，所以加 staleness guard：
  同一個交易日內已經拉過就跳過，避免 realtime_watcher 每分鐘觸發時浪費配額。
- `max_count` 係由 start 數起（唔係由最新倒數），所以用「起始日期」控制範圍，
  再喺本地截取最後 N 條。
- 輸出格式直接對應 lightweight-charts candlestick series：
  {"TQQQ": [{"time": "2026-09-19", "open": .., "high": .., "low": .., "close": ..}, ...]}

用法：
    from kline_fetcher import update_kline_file
    update_kline_file(['TQQQ', 'SOXL', 'SPCH'])
"""
import json
import os
from datetime import datetime, timedelta, timezone

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
KLINE_FILE = os.path.join(REPO_DIR, 'kline.json')

# 拉幾多日歷史（日曆日，非交易日）；1 年約 365 日 -> ~250 根日 K
LOOKBACK_DAYS = 400
# 最多保留幾多根日 K（前端顯示夠用即可，控制 json 體積）
MAX_BARS = 260
FUTU_HOST = '127.0.0.1'
FUTU_PORT = 11111


def _today_ny_str():
    """用美東日期做 staleness key，貼合美股交易日。"""
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d')


def _load_existing():
    if not os.path.exists(KLINE_FILE):
        return {}
    try:
        with open(KLINE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _needs_refresh(existing, symbols):
    """同一個美東交易日內已經拉過所有目標 symbol 就唔再拉。"""
    if not existing:
        return True
    if existing.get('fetched_on_ny') != _today_ny_str():
        return True
    series = existing.get('series') or {}
    return any(s not in series or not series[s] for s in symbols)


def update_kline_file(symbols, force=False, script_version=''):
    """
    成功時寫入 kline.json 並回傳 dict；跳過或失敗時回傳現有內容（可能為 {}）。
    永遠唔會拋 exception 出去打斷主 sync 流程。
    """
    symbols = [s for s in symbols if s]
    existing = _load_existing()

    if not force and not _needs_refresh(existing, symbols):
        return existing

    try:
        import futu as ft
    except Exception as e:
        print(f"[kline] futu SDK 不可用，跳過 K 線更新: {e}")
        return existing

    end = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    start = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).strftime('%Y-%m-%d')

    quote_ctx = None
    series = dict(existing.get('series') or {})
    fetched_any = False
    try:
        quote_ctx = ft.OpenQuoteContext(host=FUTU_HOST, port=FUTU_PORT)
        print(f"[kline] Fetching daily K-line ({script_version}) for {symbols}...")
        for sym in symbols:
            try:
                ret, data, _page = quote_ctx.request_history_kline(
                    f'US.{sym}', start=start, end=end,
                    ktype=ft.KLType.K_DAY, max_count=1000,
                )
                if ret != 0 or data is None or not len(data):
                    print(f"[kline] {sym} 拉取失敗: {str(data)[:120]}")
                    continue
                bars = []
                for _i, row in data.iterrows():
                    try:
                        bars.append({
                            'time': str(row['time_key'])[:10],
                            'open': round(float(row['open']), 4),
                            'high': round(float(row['high']), 4),
                            'low': round(float(row['low']), 4),
                            'close': round(float(row['close']), 4),
                        })
                    except Exception:
                        continue
                if bars:
                    series[sym] = bars[-MAX_BARS:]
                    fetched_any = True
                    print(f"[kline] {sym}: {len(series[sym])} 根日 K（至 {series[sym][-1]['time']}）")
            except Exception as e:
                print(f"[kline] {sym} 出錯: {e}")
                continue
    except Exception as e:
        print(f"[kline] 連線 Futu OpenD 失敗，保留舊 K 線: {e}")
        return existing
    finally:
        if quote_ctx is not None:
            try:
                quote_ctx.close()
            except Exception:
                pass

    if not fetched_any:
        return existing

    payload = {
        'fetched_on_ny': _today_ny_str(),
        'fetched_at': datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S'),
        'series': series,
    }
    try:
        with open(KLINE_FILE, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))
    except Exception as e:
        print(f"[kline] 寫入 kline.json 失敗: {e}")
        return existing
    return payload


if __name__ == '__main__':
    import sys
    syms = sys.argv[1:] or ['TQQQ', 'SOXL', 'SPCH']
    out = update_kline_file(syms, force=True, script_version='manual')
    s = out.get('series', {})
    for k, v in s.items():
        print(k, len(v), 'bars, last:', v[-1] if v else None)
