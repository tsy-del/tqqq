"""
trade_manager.py — 交易明細 (trades.json) 讀取與相關計算（從 sync_prices.py 拆出，項目 10）

負責：
- 讀取 trades.json（交易明細帳本）
- 產生交易紀錄 HTML（Trade Records tab）
- 產生圖表交易事件標記 (v8.2 項目 7)
"""
import json
from datetime import datetime
from zoneinfo import ZoneInfo


def load_trades_ledger(trades_file):
    try:
        with open(trades_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("trades.json not found, ledger unavailable")
        return []


def render_trades_html(trades_ledger):
    trades_html = ""
    if trades_ledger:
        for t in reversed(trades_ledger):  # 最新交易喺上
            action_badge = "BUY" if t['action'] == 'BUY' else "SELL"
            action_color = "var(--accent)" if t['action'] == 'BUY' else "var(--danger)"
            price_str = f"${t['price_usd']:.2f}" if t.get('price_usd') else "N/A"
            fee_str = f"${t['fee_usd']}" if t.get('fee_usd', 0) > 0 else ""
            ref_str = t.get('reference', '') or ''
            notes_str = t.get('notes', '') or ''
            trades_html += f"""<div class="asset-row" style="font-size: 12px;">
                <div>
                    <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                        <span style="font-weight: 700;">{t['date']}</span>
                        <span style="background: {action_color}; color: #fff; font-size: 9px; padding: 2px 6px; border-radius: 4px; font-weight: 700;">{action_badge}</span>
                    </div>
                    <div style="color: var(--text-dim); font-size: 11px;">{t.get('account', 'N/A')} · {t['asset']} × {t['quantity']}</div>
                    {f'<div style="color: var(--text-dim); font-size: 10px; margin-top: 2px;">{notes_str}</div>' if notes_str else ''}
                </div>
                <div style="text-align: right;">
                    <div style="font-weight: 700;">{price_str}</div>
                    {f'<div style="font-size: 10px; color: var(--text-dim);">Fee: {fee_str}</div>' if fee_str else ''}
                    {f'<div style="font-size: 9px; color: var(--text-dim); margin-top: 2px;">{ref_str}</div>' if ref_str else ''}
                </div>
            </div>"""
        trades_html = f'<section style="margin-top: 32px; margin-bottom: 32px;"><h2>Trade Records</h2>{trades_html}</section>'
    else:
        trades_html = '<section style="margin-top: 32px; margin-bottom: 32px;"><h2>Trade Records</h2><div style="text-align: center; color: var(--text-dim); padding: 32px;">No trade records available</div></section>'
    return trades_html


def build_trade_markers(trades_ledger):
    """v8.2 項目 7: 為圖表產生加/減倉事件標記。"""
    trade_markers = []
    ny_tz = ZoneInfo("America/New_York")
    for t in trades_ledger:
        try:
            dt = datetime.strptime(t['date'], '%Y-%m-%d').replace(tzinfo=ny_tz)
            ts = int(dt.timestamp())
            trade_markers.append({
                "time": ts,
                "action": t['action'],
                "label": f"{t['asset']} {t['action']}"
            })
        except Exception:
            continue
    return trade_markers
