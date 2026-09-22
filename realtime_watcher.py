"""
realtime_watcher.py — 常駐推送監聽器（v11.18 修正版，配合 cron 定期 sync）

負責：
- 用 Futu OpenAPI 的 subscribe() 訂閱 TQQQ/SOXL/SPCH 逐筆報價（跳價）
- 收到推送時提取價格+prev_close+session標籤，寫入 tick.json（供前端即時顯示）
- 背景 timer 每 5 秒將最後推送數據寫入 tick.json
- 唔再觸發 sync_prices.py update_files()——改由 cron 每分鐘定期執行
- 24 小時運行，斷線自動重連（Futu SDK 內建重連，呢邊加埋看門狗重新訂閱）

用法：
    python3 realtime_watcher.py
建議透過 launchd 長駐運行（見 com.tqqqplan.realtimewatcher.plist）。
"""
import os
import sys
import time
import json
import threading
import traceback
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

import futu as ft

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
TICK_FILE = os.path.join(REPO_DIR, 'tick.json')

FUTU_HOST = '127.0.0.1'
FUTU_PORT = 11111
SYMBOLS = ['TQQQ', 'SOXL', 'SPCH']
FUTU_CODES = [f"US.{s}" for s in SYMBOLS]

# 看門狗：幾秒都冇收到任何推送就當作連線可能有問題，嘗試重新訂閱
WATCHDOG_IDLE_SECONDS = 300
# 每幾秒將最後推送數據寫入 tick.json
TICK_WRITE_INTERVAL = 5

_lock = threading.Lock()
_last_tick_at = 0.0
_last_prices = {}  # {symbol: {'price': float, 'prev_close': float, 'label': str}}
_stop = threading.Event()


def _hk_now_str():
    hk_tz = timezone(timedelta(hours=8))
    return datetime.now(hk_tz).strftime('%Y-%m-%d %H:%M:%S')


def _get_session_label():
    """根據美東本地時間窗口判斷時段（v11.13邏輯）"""
    ny_tz = ZoneInfo("America/New_York")
    ny_now = datetime.now(ny_tz)
    h = ny_now.hour
    m = ny_now.minute
    hm = h * 100 + m
    
    if 930 <= hm < 1600:
        return "REG"
    elif 400 <= hm < 930:
        return "PRE"
    elif 1600 <= hm < 2000:
        return "AFTER"
    else:
        return "NIGHT"


class TickHandler(ft.StockQuoteHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, data = super(TickHandler, self).on_recv_rsp(rsp_pb)
        global _last_tick_at, _last_prices
        if ret_code != ft.RET_OK:
            print(f"[跳價回調錯誤] {data}")
            return ft.RET_ERROR, data
        
        # v11.18: 提取價格+prev_close並判斷session標籤
        session_label = _get_session_label()
        got = _lock.acquire(timeout=5)
        if got:
            try:
                _last_tick_at = time.time()
                for i, row in data.iterrows():
                    code = row.get('code', '')
                    if not code.startswith('US.'):
                        continue
                    symbol = code.split('.', 1)[1]
                    price = row.get('last_price', 0)
                    prev_close = row.get('prev_close_price', 0)
                    if price > 0:
                        _last_prices[symbol] = {
                            'price': price,
                            'prev_close': prev_close,
                            'label': session_label
                        }
            finally:
                _lock.release()
        return ft.RET_OK, data


def _tick_writer_loop():
    """背景 thread：每 5 秒將 _last_prices 寫入 tick.json。"""
    while not _stop.is_set():
        time.sleep(TICK_WRITE_INTERVAL)
        got = _lock.acquire(timeout=5)
        if not got:
            continue
        try:
            last_tick = _last_tick_at
            prices_snapshot = dict(_last_prices)
        finally:
            _lock.release()
        
        if last_tick > 0:
            try:
                hk_tz = timezone(timedelta(hours=8))
                dt = datetime.fromtimestamp(last_tick, tz=hk_tz)
                tick_data = {
                    'last_tick_at': last_tick,
                    'last_tick_hk': dt.strftime('%Y-%m-%d %H:%M:%S'),
                    'prices': prices_snapshot
                }
                with open(TICK_FILE, 'w', encoding='utf-8') as f:
                    json.dump(tick_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[{_hk_now_str()}] 寫入 tick.json 失敗: {e}")


def _connect_and_subscribe():
    quote_ctx = ft.OpenQuoteContext(host=FUTU_HOST, port=FUTU_PORT)
    quote_ctx.set_handler(TickHandler())
    ret, data = quote_ctx.subscribe(FUTU_CODES, [ft.SubType.QUOTE], subscribe_push=True)
    if ret != ft.RET_OK:
        quote_ctx.close()
        raise RuntimeError(f"訂閱失敗: {data}")
    print(f"[{_hk_now_str()}] 已訂閱跳價推送: {FUTU_CODES}")
    return quote_ctx


def main():
    global _last_tick_at
    writer_thread = threading.Thread(target=_tick_writer_loop, daemon=True)
    writer_thread.start()

    quote_ctx = None
    try:
        while not _stop.is_set():
            try:
                if quote_ctx is None:
                    quote_ctx = _connect_and_subscribe()
                    got = _lock.acquire(timeout=5)
                    if got:
                        try:
                            _last_tick_at = time.time()
                        finally:
                            _lock.release()

                time.sleep(10)

                # 看門狗：太耐冇收到任何推送，當連線可能已經失效，重連
                now = time.time()
                got = _lock.acquire(timeout=5)
                if got:
                    try:
                        last_tick = _last_tick_at
                    finally:
                        _lock.release()

                    if now - last_tick > WATCHDOG_IDLE_SECONDS:
                        print(f"[{_hk_now_str()}] 看門狗：{WATCHDOG_IDLE_SECONDS}秒冇收到推送，重新訂閱")
                        if quote_ctx:
                            try:
                                quote_ctx.close()
                            except:
                                pass
                            quote_ctx = None

            except Exception as e:
                print(f"[{_hk_now_str()}] 連線/訂閱異常: {e}")
                traceback.print_exc()
                if quote_ctx:
                    try:
                        quote_ctx.close()
                    except:
                        pass
                    quote_ctx = None
                time.sleep(30)

    except KeyboardInterrupt:
        print(f"[{_hk_now_str()}] 收到中斷信號，正常退出")
    finally:
        _stop.set()
        if quote_ctx:
            try:
                quote_ctx.close()
            except:
                pass


if __name__ == '__main__':
    main()
