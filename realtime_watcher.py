"""
realtime_watcher.py — 常駐推送監聽器（v11.17 簡化版，配合 cron 定期 sync）

負責：
- 用 Futu OpenAPI 的 subscribe() 訂閱 TQQQ/SOXL/SPCH 逐筆報價（跳價）
- 收到推送時記錄最後跳價時間 (_last_tick_at)
- 背景 timer 每 10 秒將 _last_tick_at 寫入 tick.json（供前端顯示「跳價」時間戳）
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

import futu as ft

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
TICK_FILE = os.path.join(REPO_DIR, 'tick.json')

FUTU_HOST = '127.0.0.1'
FUTU_PORT = 11111
SYMBOLS = ['TQQQ', 'SOXL', 'SPCH']
FUTU_CODES = [f"US.{s}" for s in SYMBOLS]

# 看門狗：幾秒都冇收到任何推送就當作連線可能有問題，嘗試重新訂閱
WATCHDOG_IDLE_SECONDS = 300
# 每幾秒將 _last_tick_at 寫入 tick.json
TICK_WRITE_INTERVAL = 10

_lock = threading.Lock()
_last_tick_at = 0.0
_stop = threading.Event()


def _hk_now_str():
    hk_tz = timezone(timedelta(hours=8))
    return datetime.now(hk_tz).strftime('%Y-%m-%d %H:%M:%S')


class TickHandler(ft.StockQuoteHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, data = super(TickHandler, self).on_recv_rsp(rsp_pb)
        global _last_tick_at
        if ret_code != ft.RET_OK:
            print(f"[跳價回調錯誤] {data}")
            return ft.RET_ERROR, data
        # v11.17: 簡化版，純粹記錄最後推送時間，唔再判斷價格變動
        got = _lock.acquire(timeout=5)
        if got:
            try:
                _last_tick_at = time.time()
            finally:
                _lock.release()
        return ft.RET_OK, data


def _tick_writer_loop():
    """背景 thread：每 10 秒將 _last_tick_at 寫入 tick.json。"""
    while not _stop.is_set():
        time.sleep(TICK_WRITE_INTERVAL)
        got = _lock.acquire(timeout=5)
        if not got:
            continue
        try:
            last_tick = _last_tick_at
        finally:
            _lock.release()
        
        if last_tick > 0:
            try:
                hk_tz = timezone(timedelta(hours=8))
                dt = datetime.fromtimestamp(last_tick, tz=hk_tz)
                tick_data = {
                    'last_tick_at': last_tick,
                    'last_tick_hk': dt.strftime('%Y-%m-%d %H:%M:%S')
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
                        print(f"[{_hk_now_str()}] 超過 {WATCHDOG_IDLE_SECONDS}s 無推送，重新連線...")
                        try:
                            quote_ctx.close()
                        except Exception:
                            pass
                        quote_ctx = None

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


if __name__ == '__main__':
    main()
