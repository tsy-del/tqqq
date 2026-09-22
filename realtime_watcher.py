"""
realtime_watcher.py — 常駐推送監聽器（v10.4，取代 cron 定時 polling）

負責：
- 用 Futu OpenAPI 的 subscribe() 訂閱 TQQQ/SOXL/SPCH 逐筆報價（跳價）
- 收到推送時只記落記憶體，唔即刻觸發更新
- 背景 timer 每 THROTTLE_SECONDS 秒檢查一次：如果自上次更新後價格有變，先觸發
  sync_prices.py 嘅 update_files()（計算 + render + git commit/push）
- 24 小時運行，斷線自動重連（Futu SDK 內建重連，呢邊加埋看門狗重新訂閱）

用法：
    python3 realtime_watcher.py
建議透過 launchd 長駐運行（見 com.tqqqplan.realtimewatcher.plist）。
"""
import os
import sys
import time
import threading
import traceback
from datetime import datetime, timezone, timedelta

import futu as ft

# 借用 sync_prices.py 已有嘅計算/render/git 邏輯，唔重複寫
import sync_prices

FUTU_HOST = '127.0.0.1'
FUTU_PORT = 11111
SYMBOLS = ['TQQQ', 'SOXL', 'SPCH']
FUTU_CODES = [f"US.{s}" for s in SYMBOLS]

# 節流：最少相隔幾秒先允許觸發一次 update_files()（避免開市時狂 push git）
THROTTLE_SECONDS = 60
# 看門狗：幾秒都冇收到任何推送就當作連線可能有問題，嘗試重新訂閱
WATCHDOG_IDLE_SECONDS = 300

_lock = threading.Lock()
_latest_prices = {}   # sym -> 顯示價（根據時段揀選的 pre/after/overnight/last）
_last_pushed_prices = {}  # sym -> 上次觸發 update_files() 時嘅價格，用嚟判斷有冇變
_last_tick_at = 0.0
_last_update_at = 0.0
_current_market_us = ''  # 最新嘅 market_us 狀態，由背景 thread 定期更新
_stop = threading.Event()

# 每幾秒刷新一次 market_us 狀態（唔需要每次推送都查，因為市場狀態唔會喺好短時間內跟著變）
MARKET_STATE_REFRESH_SECONDS = 20


def _valid(p):
    return p is not None and p == p and float(p) > 0


def _pick_display_price(row, market_us):
    """同 price_fetcher._fetch_prices_via_futu 用一致邏輯（v11.2: 夜盤有效數據優先於
    market_us 狀態字串）：盤前/盤後/夜盤好多時冇成交，last_price 唔會變，但
    pre/after/overnight 價會跟報價跳動，所以必須睜返嘅欄位先偵測到変動。
    唔再純粹跟 market_us 字串對一，因為呢個狀態機可能落後於實際時鐘，
    導致 overnight_price 已經有有效新值但 market_us 仍未跳去 NIGHT_OPEN 時，
    若仍死守 market_us 就会一直用已凍結嘅 after_price，永不触發更新。"""
    pre_price = row.get('pre_price')
    after_price = row.get('after_price')
    overnight_price = row.get('overnight_price')
    last_price = row.get('last_price')

    if market_us == 'MORNING':
        if _valid(last_price):
            return round(float(last_price), 4)
    elif _valid(overnight_price) and market_us in (
        'AFTER_HOURS_BEGIN', 'AFTER_HOURS_END', 'NIGHT_OPEN', 'NIGHT_END',
        'PRE_MARKET_BEGIN', 'PRE_MARKET_END',
    ):
        return round(float(overnight_price), 4)
    elif market_us in ('PRE_MARKET_BEGIN', 'PRE_MARKET_END') and _valid(pre_price):
        return round(float(pre_price), 4)
    elif market_us in ('AFTER_HOURS_BEGIN', 'AFTER_HOURS_END') and _valid(after_price):
        return round(float(after_price), 4)
    if _valid(last_price):
        return round(float(last_price), 4)
    return None


class TickHandler(ft.StockQuoteHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, data = super(TickHandler, self).on_recv_rsp(rsp_pb)
        global _last_tick_at
        if ret_code != ft.RET_OK:
            print(f"[跳價回調錯誤] {data}")
            return ft.RET_ERROR, data
        with _lock:
            for _, row in data.iterrows():
                code = row['code']
                if not code.startswith('US.'):
                    continue
                sym = code.split('.', 1)[1]
                if sym not in SYMBOLS:
                    continue
                price = _pick_display_price(row, _current_market_us)
                if price is not None and price > 0:
                    _latest_prices[sym] = price
            _last_tick_at = time.time()
        return ft.RET_OK, data


def _prices_changed():
    with _lock:
        if not _latest_prices:
            return False
        for sym, price in _latest_prices.items():
            if _last_pushed_prices.get(sym) != price:
                return True
        return False


def _mark_pushed():
    with _lock:
        _last_pushed_prices.update(_latest_prices)


def _hk_now_str():
    hk_tz = timezone(timedelta(hours=8))
    return datetime.now(hk_tz).strftime('%Y-%m-%d %H:%M:%S')


def _throttled_update_loop():
    """背景 thread：每秒檢查一次，價格有變 + 已過節流時間 先觸發實際更新。"""
    global _last_update_at
    while not _stop.is_set():
        time.sleep(1)
        now = time.time()
        if now - _last_update_at < THROTTLE_SECONDS:
            continue
        if not _prices_changed():
            continue
        try:
            print(f"[{_hk_now_str()}] 偵測到價格變動，觸發更新...")
            ok = sync_prices.update_files()
            _last_update_at = time.time()
            if ok:
                _mark_pushed()
                print(f"[{_hk_now_str()}] 更新完成。")
            else:
                print(f"[{_hk_now_str()}] 更新失敗，下次價格變動會重試。")
        except Exception as e:
            print(f"[{_hk_now_str()}] 更新時發生例外: {e}")
            traceback.print_exc()
            _last_update_at = time.time()


def _market_state_refresh_loop(quote_ctx_holder):
    """背景 thread：定期查詢一次 market_us 狀態，供 TickHandler 判斷用嗰個時段欄位。
    quote_ctx_holder 係一個 list，[0] 位放住目前活躍嘅 quote_ctx（可能會被主 loop 換走）。"""
    global _current_market_us
    while not _stop.is_set():
        ctx = quote_ctx_holder[0]
        if ctx is not None:
            try:
                ret, state = ctx.get_global_state()
                if ret == ft.RET_OK:
                    with _lock:
                        _current_market_us = state.get('market_us', '').upper()
            except Exception as e:
                print(f"[{_hk_now_str()}] 查詢市場狀態失敗: {e}")
        time.sleep(MARKET_STATE_REFRESH_SECONDS)


def _connect_and_subscribe():
    quote_ctx = ft.OpenQuoteContext(host=FUTU_HOST, port=FUTU_PORT)
    quote_ctx.set_handler(TickHandler())
    ret, data = quote_ctx.subscribe(FUTU_CODES, [ft.SubType.QUOTE], subscribe_push=True)
    if ret != ft.RET_OK:
        quote_ctx.close()
        raise RuntimeError(f"訂閱失敗: {data}")
    print(f"[{_hk_now_str()}] 已訂閱跳價推送: {FUTU_CODES}")

    # 連線後立即查一次市場狀態，唔使等第一個 refresh 週期
    global _current_market_us
    try:
        ret_state, state = quote_ctx.get_global_state()
        if ret_state == ft.RET_OK:
            with _lock:
                _current_market_us = state.get('market_us', '').upper()
            print(f"[{_hk_now_str()}] 目前市場狀態: {_current_market_us}")
    except Exception as e:
        print(f"[{_hk_now_str()}] 初始查詢市場狀態失敗: {e}")

    return quote_ctx


def main():
    global _last_tick_at
    updater_thread = threading.Thread(target=_throttled_update_loop, daemon=True)
    updater_thread.start()

    quote_ctx = None
    quote_ctx_holder = [None]
    state_thread = threading.Thread(target=_market_state_refresh_loop, args=(quote_ctx_holder,), daemon=True)
    state_thread.start()

    try:
        while not _stop.is_set():
            try:
                if quote_ctx is None:
                    quote_ctx = _connect_and_subscribe()
                    quote_ctx_holder[0] = quote_ctx
                    _last_tick_at = time.time()

                time.sleep(10)

                # 看門狗：太耐冇收到任何推送，當連線可能已經失效，重連
                if time.time() - _last_tick_at > WATCHDOG_IDLE_SECONDS:
                    print(f"[{_hk_now_str()}] 超過 {WATCHDOG_IDLE_SECONDS}s 無推送，重新連線...")
                    try:
                        quote_ctx.close()
                    except Exception:
                        pass
                    quote_ctx = None
                    quote_ctx_holder[0] = None

            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"[{_hk_now_str()}] 連線/訂閱例外: {e}，10 秒後重試...")
                traceback.print_exc()
                if quote_ctx is not None:
                    try:
                        quote_ctx.close()
                    except Exception:
                        pass
                    quote_ctx = None
                    quote_ctx_holder[0] = None
                time.sleep(10)
    except KeyboardInterrupt:
        print("收到中斷信號，停止監聽...")
    finally:
        _stop.set()
        if quote_ctx is not None:
            try:
                quote_ctx.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
