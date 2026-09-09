"""
html_renderer.py — index.html 頁面生成邏輯（從 sync_prices.py v8.2 拆出，項目 10）

負責：把已計算好嘅持倉/利潤/風險/交易/圖表資料組裝成最終 index.html。
"""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from portfolio_calculator import format_hkd


def render_page(data, prices_data, rate, total_value_hkd, total_cost_hkd, total_profit_hkd,
                 profit_history, trades_ledger, active_tickers_sorted, current_time_str,
                 script_version, prog1, profit_for_stage1, stage1_target,
                 available_for_stage2, profit_for_stage2, stage2_target, prog2,
                 available_for_stage3, profit_for_stage3, stage3_target, prog3,
                 total_profit_color, total_profit_sign, total_profit_pct):
    """組裝並回傳完整 index.html 字串。就地修改 data['milestones'] 嘅 status 欄位。"""
    SCRIPT_VERSION = script_version

    milestones_html = ""
    # 取得現價以計算里程碑
    tqqq_price = prices_data.get('TQQQ', {}).get('price', data['market_prices'].get('tqqq_usd', 0))
    t_label = prices_data.get('TQQQ', {}).get('label', 'REG')
    soxl_price = prices_data.get('SOXL', {}).get('price', data['market_prices'].get('soxl_usd', 0))
    s_label = prices_data.get('SOXL', {}).get('label', 'REG')
    
    # 初始化累積目標利潤
    cumulative_target_profit = 0

    for m in data['milestones']:
        if m['stage'] == 1:
            stage_prog = prog1
            avail_profit_str = format_hkd(profit_for_stage1)
            prog_label = "雜費利潤進度"
            shortfall = max(0, stage1_target - profit_for_stage1)
            shortfall_str = format_hkd(shortfall)
            m['status'] = "COMPLETED" if prog1 >= 100 else "IN_PROGRESS"
            target_amount = stage1_target
        elif m['stage'] == 2:
            stage_prog = prog2
            avail_profit_str = format_hkd(profit_for_stage2) if available_for_stage2 > 0 else "$0"
            prog_label = "首期利潤進度"
            shortfall = max(0, stage2_target - profit_for_stage2)
            shortfall_str = format_hkd(shortfall)
            if prog2 >= 100: m['status'] = "COMPLETED"
            elif available_for_stage2 > 0: m['status'] = "IN_PROGRESS"
            else: m['status'] = "PENDING"
            target_amount = stage2_target
        elif m['stage'] == 3:
            stage_prog = prog3
            avail_profit_str = format_hkd(profit_for_stage3) if available_for_stage3 > 0 else "$0"
            prog_label = "裝修利潤進度"
            shortfall = max(0, stage3_target - profit_for_stage3)
            shortfall_str = format_hkd(shortfall)
            if prog3 >= 100: m['status'] = "COMPLETED"
            elif available_for_stage3 > 0: m['status'] = "IN_PROGRESS"
            else: m['status'] = "PENDING"
            target_amount = stage3_target

        # 累積目標利潤計算 (直接與目前總資產對比，不再模擬套現扣減)
        cumulative_target_profit += target_amount
        required_portfolio_value = total_cost_hkd + cumulative_target_profit

        if total_value_hkd < required_portfolio_value and total_value_hkd > 0:
            required_growth_pct = (required_portfolio_value / total_value_hkd) - 1
            stage_target_tqqq = tqqq_price * (1 + required_growth_pct)
            stage_target_soxl = soxl_price * (1 + required_growth_pct)
            
            price_diff_pct = required_growth_pct * 100
            gap_label = "剩餘距離"
            gap_val = f"+{price_diff_pct:.1f}%"
            gap_color = "var(--accent)"
            t_target_str = f"${stage_target_tqqq:.2f}"
            s_target_str = f"${stage_target_soxl:.2f}"
        else:
            gap_label = "目標狀態"
            gap_val = "已達標"
            gap_color = "var(--success)"
            t_target_str = "達標"
            s_target_str = "達標"

        status_class = f"status-{m['status']}"

        details = f"""
        <div class="progress-details">
            <div style="font-size: 10px; color: var(--text-dim); margin-bottom: 10px; padding: 6px 10px; background: rgba(255,255,255,0.03); border-radius: 8px;">
                💰 <b>利潤目標</b>: {format_hkd(target_amount)} · 📊 <b>需達資產值</b>: {format_hkd(required_portfolio_value)}
            </div>
            <div class="price-gap-box">
                <div style="display: grid; grid-template-columns: 45px 1fr 1fr 1fr; gap: 4px; font-size: 12px; color: var(--text-dim); margin-bottom: 8px; text-align: right;">
                    <div style="text-align: left;"></div>
                    <div>目標價</div>
                    <div>現價</div>
                    <div>{gap_label}</div>
                </div>
                <div style="display: grid; grid-template-columns: 45px 1fr 1fr 1fr; gap: 4px; font-size: 14px; margin-bottom: 8px; text-align: right; align-items: center;">
                    <div style="text-align: left; color: var(--text-dim); font-size: 13px;">TQQQ</div>
                    <div class="pg-val">{t_target_str}</div>
                    <div class="pg-val" style="color:var(--accent);">${tqqq_price:.2f}</div>
                    <div class="pg-val" style="color:{gap_color}; font-size: 14px;">{gap_val}</div>
                </div>
                <div style="display: grid; grid-template-columns: 45px 1fr 1fr 1fr; gap: 4px; font-size: 14px; text-align: right; align-items: center; padding-bottom: 4px; border-bottom: 1px dashed var(--border);">
                    <div style="text-align: left; color: var(--text-dim); font-size: 13px;">SOXL</div>
                    <div class="pg-val">{s_target_str}</div>
                    <div class="pg-val" style="color:var(--accent);">${soxl_price:.2f}</div>
                    <div class="pg-val" style="color:{gap_color}; font-size: 14px;">{gap_val}</div>
                </div>
            </div>
            <div class="detail-row" style="margin-top: 15px;"><span>{prog_label}</span><span class="detail-val">{stage_prog:.1f}%</span></div>
            <div class="progress-bg"><div class="progress-fill" style="width: {stage_prog}%"></div></div>
            <div class="detail-row" style="margin-top: 8px;"><span>可用利潤</span><span class="detail-val">{avail_profit_str}</span></div>
            <div class="detail-row" style="margin-top: 4px;"><span>尚欠金額</span><span class="detail-val" style="color:var(--accent);">{shortfall_str}</span></div>
        </div>"""

        if m['stage'] == 1 and prog1 >= 100:
            details = '<div style="font-size: 11px; color: var(--success); margin-bottom: 10px;">✅ 盈利已覆蓋 $45 萬雜費</div>' + details

        is_collapsed = "collapsed" if m['status'] == 'COMPLETED' else ""

        milestones_html += f"""<div class="milestone-card {is_collapsed}">
            <div class="m-header" onclick="this.parentElement.classList.toggle('collapsed')">
                <div style="display: flex; align-items: center; gap: 6px;">
                    <span class="m-title">Stage {m['stage']}: {m['name']}</span>
                    <span class="toggle-icon">▼</span>
                </div>
                <span class="m-status {status_class}">{m['status']}</span>
            </div>
            <div class="m-body">
                {details}<div class="m-strategy">{m['strategy']}</div>
            </div>
        </div>"""

    # 終極總目標
    total_target = 2000000
    overall_prog = min(100, max(0, (total_profit_hkd / total_target) * 100))
    overall_shortfall = max(0, total_target - total_profit_hkd)

    if total_profit_hkd >= total_target:
        overall_status = "COMPLETED"
        overall_status_class = "status-COMPLETED"
        overall_shortfall_str = "$0"
        is_overall_collapsed = "collapsed"
    else:
        overall_status = "IN_PROGRESS"
        overall_status_class = "status-IN_PROGRESS"
        overall_shortfall_str = format_hkd(overall_shortfall)
        is_overall_collapsed = ""

    milestones_html += f"""<div class="milestone-card {is_overall_collapsed}" style="border: 1px solid var(--accent); box-shadow: 0 0 15px rgba(59,130,246,0.1);">
        <div class="m-header" onclick="this.parentElement.classList.toggle('collapsed')">
            <div style="display: flex; align-items: center; gap: 6px;">
                <span class="m-title">🏆 終極總目標：純賺 200 萬</span>
                <span class="toggle-icon">▼</span>
            </div>
            <span class="m-status {overall_status_class}">{overall_status}</span>
        </div>
        <div class="m-body">
            <div class="progress-details" style="margin-top: 10px;">
                <div class="detail-row"><span>整體利潤進度</span><span class="detail-val">{overall_prog:.1f}%</span></div>
                <div class="progress-bg"><div class="progress-fill" style="width: {overall_prog}%; background: linear-gradient(90deg, #3b82f6, #10b981);"></div></div>
                <div class="detail-row" style="margin-top: 8px;"><span>目前總純利</span><span class="detail-val" style="color:var(--success);">{format_hkd(total_profit_hkd)}</span></div>
                <div class="detail-row" style="margin-top: 4px;"><span>距離 200 萬尚欠</span><span class="detail-val" style="color:var(--accent);">{overall_shortfall_str}</span></div>
            </div>
            <div class="m-strategy">不計成本，目標純利達到 $2,000,000 以完成所有規劃 (雜費、首期、裝修)。</div>
        </div>
    </div>"""

    # v8.0: Trade records HTML
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

    accounts_html = ""
    for acc in data['accounts']:
        rows = ""
        for h in acc['holdings']:
            avg = h['avg_price_usd']
            gain = ((h['current_price_usd'] - avg) / avg * 100) if avg else 0
            pl = (h['current_price_usd'] - avg) * h['quantity'] * rate
            rows += f"""<div class="asset-row"><div class="asset-info">
                <div class="asset-name">{h['asset']} <span class="qty">× {h['quantity']}</span></div>
                <div class="asset-cost">成本 ${avg} | 現價 ${h['current_price_usd']}</div></div>
                <div style="text-align: right;"><div class="asset-status {'up' if gain >= 0 else 'down'}">{'+' if gain >= 0 else ''}{gain:.1f}%</div>
                <div style="font-size: 10px; color: var(--text-dim);">{format_hkd(pl)}</div></div></div>"""
        # v5.12: 帳戶層利潤 % + 顏色警示
        a_profit = int(round(acc.get('total_profit_hkd', 0)))
        a_cost = int(round(acc.get('total_cost_hkd', 0)))
        a_pct = (a_profit / a_cost * 100) if a_cost > 0 else 0
        if a_pct <= -20:
            a_color, a_badge = '#ef4444', ' ⚠️'
        elif a_pct < 0:
            a_color, a_badge = '#f59e0b', ''
        else:
            a_color, a_badge = '#10b981', ''
        a_sign = '+' if a_profit >= 0 else '-'
        accounts_html += f"""<div class="account-block collapsed">
            <div class="account-header" onclick="this.parentElement.classList.toggle('collapsed')" style="cursor: pointer; user-select: none; border-left: 3px solid {a_color}; padding-left: 8px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span>{acc['account_name']}{a_badge}</span>
                    <span class="toggle-icon" style="font-size: 10px; color: var(--text-dim); transition: transform 0.3s ease;">▼</span>
                </div>
                <div style="text-align: right;">
                    <span class="acc-val">{format_hkd(acc['total_value_hkd'])}</span>
                    <div style="font-size: 10px; font-weight: 700; color: {a_color}; margin-top: 2px;">{a_sign}{format_hkd(abs(a_profit))} · {a_pct:+.1f}%</div>
                </div>
            </div>
            <div class="holdings-list">{rows}</div>
        </div>"""

    ticker_bar_html = ""
    for sym in active_tickers_sorted:
        p_data = prices_data[sym]
        chg = p_data['change_pct']
        chg_color = "var(--success)" if chg >= 0 else "var(--danger)"
        chg_sign = "+" if chg >= 0 else ""
        ticker_bar_html += f"""<a href="https://hk.finance.yahoo.com/quote/{sym}" target="_blank" class="ticker-item" style="text-decoration: none;">
            <div style="display: flex; align-items: center; gap: 6px; overflow: hidden;">
                <span class="ticker-symbol" style="flex-shrink: 0;">{sym}</span>
                <span class="ticker-price" id="ticker-price-{sym}" style="flex-shrink: 0;">${p_data['price']}</span>
                <span class="session-tag" id="ticker-session-{sym}" style="display:{'inline-block' if p_data['label'] == 'EXT' else 'none'}; flex-shrink: 0; font-size: 8px; padding: 0 2px;">{p_data['label']}</span>
            </div>
            <span id="ticker-chg-{sym}" style="font-size: 11px; font-weight: 700; color: {chg_color}; flex-shrink: 0;">{chg_sign}{chg:.1f}%</span>
        </a>\n"""

    # 合併持倉 (Combined Positions) 計算
    combined_data = {}
    for acc in data['accounts']:
        for h in acc['holdings']:
            sym = h['asset']
            if sym == 'USD 現金': continue
            qty = h['quantity']
            avg = h.get('avg_price_usd', 0)
            if sym not in combined_data:
                combined_data[sym] = {'qty': 0, 'cost_sum': 0}
            combined_data[sym]['qty'] += qty
            combined_data[sym]['cost_sum'] += qty * avg

    combined_html = ""
    for sym in active_tickers_sorted:
        if sym in combined_data:
            c = combined_data[sym]
            total_qty = c['qty']
            if total_qty <= 0: continue
            avg_cost = c['cost_sum'] / total_qty
            curr_p = prices_data[sym]['price']
            gain_pct = ((curr_p - avg_cost) / avg_cost * 100) if avg_cost else 0
            pl_hkd = (curr_p - avg_cost) * total_qty * rate
            
            total_cost_hkd_disp = avg_cost * total_qty * rate
            total_value_hkd_disp = curr_p * total_qty * rate
            combined_html += f"""<div class="asset-row" style="border-left: 4px solid var(--accent);">
                <div class="asset-info">
                    <div class="asset-name">{sym} <span class="qty">總共: {total_qty}</span></div>
                    <div class="asset-cost">平均成本 ${avg_cost:.3f} | 現價 ${curr_p}</div>
                    <div style="font-size: 10px; color: var(--text-dim); margin-top: 2px;">總成本: {format_hkd(total_cost_hkd_disp)} | 目前價值: {format_hkd(total_value_hkd_disp)}</div>
                </div>
                <div style="text-align: right;">
                    <div class="asset-status {'up' if gain_pct >= 0 else 'down'}">{'+' if gain_pct >= 0 else ''}{gain_pct:.1f}%</div>
                    <div style="font-size: 10px; color: var(--text-dim);">{format_hkd(pl_hkd)}</div>
                </div>
            </div>"""

    if combined_html:
        combined_html = f'<section style="margin-top: 32px; margin-bottom: 32px;"><h2>Combined Positions</h2>{combined_html}</section>'


    # v8.2: 風險指標 - 資產佔比 + 槓桿集中度 + 鎖定 vs 可操作
    leveraged_symbols = {'TQQQ', 'SOXL'}
    locked_value = 0
    available_value = 0
    for acc in data['accounts']:
        if acc.get('is_locked'):
            locked_value += acc.get('total_value_hkd', 0)
        else:
            available_value += acc.get('total_value_hkd', 0)

    asset_alloc_rows = ""
    leveraged_value = 0
    for sym in active_tickers_sorted:
        if sym in combined_data:
            c = combined_data[sym]
            total_qty = c['qty']
            if total_qty <= 0: continue
            curr_p = prices_data[sym]['price']
            sym_value_hkd = curr_p * total_qty * rate
            pct = (sym_value_hkd / total_value_hkd * 100) if total_value_hkd > 0 else 0
            if sym in leveraged_symbols:
                leveraged_value += sym_value_hkd
            bar_color = 'var(--accent)' if sym in leveraged_symbols else 'var(--success)'
            asset_alloc_rows += f"""<div style="margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px;">
                    <span>{sym}{' ⚠️槓桿' if sym in leveraged_symbols else ''}</span>
                    <span style="font-weight: 700;">{pct:.1f}%</span>
                </div>
                <div class="progress-bg"><div class="progress-fill" style="width: {pct}%; background: {bar_color};"></div></div>
            </div>"""

    leveraged_pct = (leveraged_value / total_value_hkd * 100) if total_value_hkd > 0 else 0
    locked_pct = (locked_value / total_value_hkd * 100) if total_value_hkd > 0 else 0
    available_pct = (available_value / total_value_hkd * 100) if total_value_hkd > 0 else 0
    leverage_warn_color = '#ef4444' if leveraged_pct >= 90 else ('#f59e0b' if leveraged_pct >= 70 else 'var(--success)')

    risk_html = f"""<section style="margin-top: 32px; margin-bottom: 32px;">
        <h2>Risk Indicators</h2>
        <div class="milestone-card" style="border: 1px dashed var(--border); box-shadow: none;">
            <div class="m-body" style="display: block;">
                <div style="font-size: 11px; font-weight: 700; color: var(--text-dim); margin-bottom: 10px;">資產佔比</div>
                {asset_alloc_rows}
                <div class="detail-row" style="margin-top: 14px; padding-top: 14px; border-top: 1px solid var(--border);">
                    <span style="font-size: 13px;">槓桿 ETF 總佔比 (TQQQ+SOXL)</span>
                    <span class="detail-val" style="color: {leverage_warn_color};">{leveraged_pct:.1f}%</span>
                </div>
                <div class="detail-row" style="margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border);">
                    <span style="font-size: 13px;">🔒 鎖定資產</span>
                    <span class="detail-val">{format_hkd(locked_value)} ({locked_pct:.1f}%)</span>
                </div>
                <div class="detail-row" style="margin-top: 4px;">
                    <span style="font-size: 13px;">✅ 可操作資產</span>
                    <span class="detail-val">{format_hkd(available_value)} ({available_pct:.1f}%)</span>
                </div>
            </div>
        </div>
    </section>"""

            # Stats HTML
    ny_tz = ZoneInfo("America/New_York")
    current_ny_date_str = datetime.now(ny_tz).strftime('%Y-%m-%d')
    history_stats = data.get('history_stats', {})
    highest_hkd = history_stats.get('highest_profit_hkd', 0)
    highest_date = history_stats.get('highest_profit_date', 'N/A')
    lowest_hkd = history_stats.get('lowest_profit_hkd', 0)
    lowest_date = history_stats.get('lowest_profit_date', 'N/A')
    
    # v6.1: 高/低分主次 —— 最高用鮮色，最低用暗色/中性，避免四個數一樣綠
    highest_color = '#10b981' if highest_hkd >= 0 else '#ef4444'
    lowest_color = '#a1a1aa' if lowest_hkd >= 0 else '#f87171'

    daily_stats = data.get('daily_stats', {})
    d_highest_hkd = daily_stats.get('highest_profit_hkd', 0)
    d_highest_time = daily_stats.get('highest_time', 'N/A')
    d_lowest_hkd = daily_stats.get('lowest_profit_hkd', 0)
    d_lowest_time = daily_stats.get('lowest_time', 'N/A')
    
    d_highest_color = '#10b981' if d_highest_hkd >= 0 else '#ef4444'
    d_lowest_color = '#a1a1aa' if d_lowest_hkd >= 0 else '#f87171'

    # v7.4: 今日變化 (現時利潤 vs 昨日收市利潤) - 用於 summary card 同 detail section
    d_prev_close = daily_stats.get('prev_close_profit_hkd')
    if d_prev_close is not None:
        d_change_hkd = int(round(total_profit_hkd)) - int(round(d_prev_close))
        d_change_color = '#10b981' if d_change_hkd >= 0 else '#ef4444'
        d_change_sign = '+' if d_change_hkd >= 0 else '-'
        d_change_pct_txt = ''
        if total_cost_hkd > 0:
            d_change_pct = (d_change_hkd / total_cost_hkd) * 100
            d_change_pct_txt = f"{d_change_pct:+.1f}%"
        # Format for summary card display
        today_profit_display = f"{d_change_sign}{format_hkd(abs(d_change_hkd))}"
        today_profit_pct_display = d_change_pct_txt
        d_change_row = f'''<div class="detail-row" style="margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid var(--border);">
                    <span style="font-size: 13px; font-weight: 700;">今日變化</span>
                    <div style="text-align: right;">
                        <div style="font-size: 17px; font-weight: 800; color: {d_change_color};">{today_profit_display}</div>
                        <div style="font-size: 10px; color: var(--text-dim); margin-top: 2px;">{today_profit_pct_display} · 昨收 {format_hkd(d_prev_close)}</div>
                    </div>
                </div>'''
    else:
        today_profit_display = "—"
        today_profit_pct_display = "—"
        d_change_color = "var(--text-dim)"
        d_change_row = '''<div class="detail-row" style="margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid var(--border);">
                    <span style="font-size: 13px; font-weight: 700;">今日變化</span>
                    <div style="text-align: right;">
                        <div style="font-size: 13px; color: var(--text-dim);">建立基準中…</div>
                        <div style="font-size: 10px; color: var(--text-dim); margin-top: 2px;">明日起可比較</div>
                    </div>
                </div>'''

    
    # v8.2: Create trade markers for chart
    trade_markers = []
    for t in trades_ledger:
        try:
            # Convert YYYY-MM-DD to timestamp
            dt = datetime.strptime(t['date'], '%Y-%m-%d')
            ts = int(dt.replace(tzinfo=ZoneInfo("America/New_York")).timestamp())
            trade_markers.append({
                "time": ts,
                "action": t['action'],
                "label": f"{t['asset']} {t['action']}"
            })
        except Exception: continue
    trade_markers_json_str = json.dumps(trade_markers)
    profit_history_json_str = json.dumps(profit_history)
    
    chart_html = f'''<section style="margin-top: 32px; margin-bottom: 32px;">
        <h2>Profit Trend</h2>
        <div style="display: flex; gap: 6px; margin-bottom: 10px;" id="chart-range-btns">
            <button class="range-btn" data-range="1">1D</button>
            <button class="range-btn" data-range="7">1W</button>
            <button class="range-btn" data-range="30">1M</button>
            <button class="range-btn active" data-range="0">All</button>
        </div>
        <div id="chart-container" style="width: 100%; height: 220px; background: var(--card); border: 1px solid var(--border); border-radius: 16px; overflow: hidden; position: relative;"></div>
        <div id="chart-fallback" style="display:none; font-size: 11px; color: var(--text-dim); text-align: center; margin-top: 8px;">圖表載入失敗（離線或 CDN 阻塞）</div>
        <script src="https://unpkg.com/lightweight-charts@4.2.3/dist/lightweight-charts.standalone.production.js"></script>
        <script>
        (function() {{
            if (typeof LightweightCharts === 'undefined') {{
                document.getElementById('chart-container').style.display = 'none';
                document.getElementById('chart-fallback').style.display = 'block';
                return;
            }}
            const chartOptions = {{ 
                layout: {{ textColor: '#71717a', background: {{ type: 'solid', color: 'transparent' }} }},
                grid: {{ vertLines: {{ visible: false }}, horzLines: {{ color: 'rgba(255, 255, 255, 0.05)' }} }},
                timeScale: {{ timeVisible: true, secondsVisible: false, borderVisible: false }},
                rightPriceScale: {{ borderVisible: false }}
            }};
            const chartContainer = document.getElementById('chart-container');
            const chart = LightweightCharts.createChart(chartContainer, chartOptions);
            const baselineSeries = chart.addBaselineSeries({{
                baseValue: {{ type: 'price', price: 0 }},
                topFillColor1: 'rgba(16, 185, 129, 0.28)',
                topFillColor2: 'rgba(16, 185, 129, 0.05)',
                topLineColor: 'rgba(16, 185, 129, 1)',
                bottomFillColor1: 'rgba(239, 68, 68, 0.05)',
                bottomFillColor2: 'rgba(239, 68, 68, 0.28)',
                bottomLineColor: 'rgba(239, 68, 68, 1)',
                lineWidth: 2,
            }});
            
            const profitData = {profit_history_json_str};
            const uniqueData = [];
            const seenTimes = new Set();
            for (const point of profitData) {{
                if (!seenTimes.has(point.time)) {{
                    seenTimes.add(point.time);
                    uniqueData.push(point);
                }}
            }}
            
            if (uniqueData.length === 1) {{
                uniqueData.unshift({{ time: uniqueData[0].time - 3600, value: uniqueData[0].value }});
            }}
            
            baselineSeries.setData(uniqueData);

            // v8.2: 交易事件標記
            const tradeEvents = {trade_markers_json_str};
            const markers = tradeEvents.map(t => ({{
                time: t.time,
                position: t.action === 'BUY' ? 'belowBar' : 'aboveBar',
                color: t.action === 'BUY' ? '#3b82f6' : '#ef4444',
                shape: t.action === 'BUY' ? 'arrowUp' : 'arrowDown',
                text: t.label
            }}));

            // v8.2: 高/低點標記
            if (uniqueData.length > 0) {{
                let maxPt = uniqueData[0], minPt = uniqueData[0];
                for (const p of uniqueData) {{
                    if (p.value > maxPt.value) maxPt = p;
                    if (p.value < minPt.value) minPt = p;
                }}
                markers.push(
                    {{ time: maxPt.time, position: 'aboveBar', color: '#10b981', shape: 'circle', text: '高' }},
                    {{ time: minPt.time, position: 'belowBar', color: '#f87171', shape: 'circle', text: '低' }}
                );
            }}
            if (markers.length > 0 && baselineSeries.setMarkers) {{
                baselineSeries.setMarkers(markers);
            }}

            chart.timeScale().fitContent();

            // v8.2: 時間範圍按鈕
            const rangeBtns = document.querySelectorAll('.range-btn');
            rangeBtns.forEach(btn => {{
                btn.addEventListener('click', () => {{
                    rangeBtns.forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    const days = parseInt(btn.dataset.range, 10);
                    if (days === 0) {{
                        chart.timeScale().fitContent();
                    }} else {{
                        const nowTs = uniqueData.length ? uniqueData[uniqueData.length - 1].time : Math.floor(Date.now()/1000);
                        chart.timeScale().setVisibleRange({{ from: nowTs - days * 86400, to: nowTs + 3600 }});
                    }}
                }});
            }});
            
            new ResizeObserver(entries => {{
                if (entries.length === 0 || entries[0].target !== chartContainer) {{ return; }}
                const newRect = entries[0].contentRect;
                chart.applyOptions({{ width: newRect.width, height: newRect.height }});
            }}).observe(chartContainer);
        }})();
        </script>
    </section>'''

    app_data_json = json.dumps(data)
    active_tickers_json = json.dumps(active_tickers_sorted)
    # v6.9: 前端 ticker bar 用嘅 previousClose，直接从後台 prices_data 攻，唔信 Finnhub 自己嘅 pc
    prev_close_map = {sym: d['prev_close'] for sym, d in prices_data.items()}
    prev_close_json = json.dumps(prev_close_map)

    history_html = f"""<section style="margin-top: 32px; margin-bottom: 32px;">
        <h2>Profit Stats (Today & History)</h2>
        <div class="milestone-card stats-card" style="border: 1px dashed var(--border); box-shadow: none;">
            <div class="m-body" style="display: block;">
                <div style="font-size: 11px; font-weight: 700; color: var(--text-dim); margin-bottom: 8px;">今日 ({current_ny_date_str} US)</div>
                {d_change_row}
                <div class="detail-row" style="margin-bottom: 12px;">
                    <span style="font-size: 13px;">今日最高利潤</span>
                    <div style="text-align: right;">
                        <div style="font-size: 15px; font-weight: 800; color: {d_highest_color};">{'+' if d_highest_hkd >= 0 else ''}{format_hkd(d_highest_hkd)}</div>
                        <div style="font-size: 10px; color: var(--text-dim); margin-top: 2px;">{d_highest_time}</div>
                    </div>
                </div>
                <div class="detail-row" style="margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid var(--border);">
                    <span style="font-size: 13px;">今日最低利潤</span>
                    <div style="text-align: right;">
                        <div style="font-size: 15px; font-weight: 800; color: {d_lowest_color};">{'+' if d_lowest_hkd >= 0 else ''}{format_hkd(d_lowest_hkd)}</div>
                        <div style="font-size: 10px; color: var(--text-dim); margin-top: 2px;">{d_lowest_time}</div>
                    </div>
                </div>
                
                <div style="font-size: 11px; font-weight: 700; color: var(--text-dim); margin-bottom: 8px;">歷史紀錄</div>
                <div class="detail-row" style="margin-bottom: 12px;">
                    <span style="font-size: 13px;">歷史最高利潤</span>
                    <div style="text-align: right;">
                        <div style="font-size: 15px; font-weight: 800; color: {highest_color};">{'+' if highest_hkd >= 0 else ''}{format_hkd(highest_hkd)}</div>
                        <div style="font-size: 10px; color: var(--text-dim); margin-top: 2px;">{highest_date}</div>
                    </div>
                </div>
                <div class="detail-row">
                    <span style="font-size: 13px;">歷史最低利潤</span>
                    <div style="text-align: right;">
                        <div style="font-size: 15px; font-weight: 800; color: {lowest_color};">{'+' if lowest_hkd >= 0 else ''}{format_hkd(lowest_hkd)}</div>
                        <div style="font-size: 10px; color: var(--text-dim); margin-top: 2px;">{lowest_date}</div>
                    </div>
                </div>
            </div>
        </div>
    </section>"""

    new_html = f"""<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover"><meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"><meta http-equiv="Pragma" content="no-cache"><meta http-equiv="Expires" content="0"><title>TQQQ Plan | {SCRIPT_VERSION} (Auto Cloud Sync)</title>
<style>
@keyframes pulse {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.3; }} 100% {{ opacity: 1; }} }}
:root {{ --bg: #09090b; --card: #18181b; --glass: rgba(255, 255, 255, 0.03); --border: rgba(255, 255, 255, 0.08); --accent: #3b82f6; --success: #10b981; --danger: #ef4444; --text-main: #fafafa; --text-dim: #71717a; }}
* {{ box-sizing: border-box; }}
body {{ font-family: -apple-system, system-ui, sans-serif; background: var(--bg); color: var(--text-main); margin: 0; display: flex; justify-content: center; padding: calc(24px + env(safe-area-inset-top)) calc(16px + env(safe-area-inset-right)) calc(24px + env(safe-area-inset-bottom)) calc(16px + env(safe-area-inset-left)); }}
.container {{ max-width: 480px; width: 100%; }}
header {{ margin-bottom: 28px; }}
.header-top {{ display: flex; justify-content: space-between; align-items: center; }}
h1 {{ font-size: 26px; font-weight: 800; margin: 0; }}
.v-tag {{ font-size: 10px; color: var(--text-dim); background: var(--glass); padding: 2px 6px; border-radius: 4px; border: 1px solid var(--border); }}
.last-update {{ font-size: 11px; color: var(--text-dim); margin-top: 6px; }}
.main-summary {{ background: var(--card); border: 1px solid var(--border); border-left: 4px solid var(--accent); padding: 18px; border-radius: 20px; margin-bottom: 24px; }}
.summary-card {{ background: var(--card); border: 1px solid var(--border); border-left: 4px solid var(--accent); padding: 18px 18px 18px 15px; border-radius: 20px; position: relative; overflow: hidden; }}
.summary-label {{ font-size: 11px; font-weight: 600; color: var(--text-dim); text-transform: uppercase; margin-bottom: 6px; }}
.summary-value {{ font-size: 20px; font-weight: 700; font-variant-numeric: tabular-nums; font-feature-settings: "tnum" 1; }}
.profit-display {{ display: flex; align-items: baseline; gap: 8px; }}
.profit-pct {{ font-size: 14px; font-weight: 700; padding-bottom: 1px; font-variant-numeric: tabular-nums; font-feature-settings: "tnum" 1; }}

.ticker-bar {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-bottom: 24px; }}
.ticker-item {{ background: var(--glass); border: 1px solid var(--border); padding: 10px 14px; border-radius: 14px; display: flex; align-items: center; justify-content: space-between; gap: 4px; }}
.ticker-symbol {{ font-weight: 700; font-size: 13px; color: var(--text-dim); }}
.ticker-price {{ font-family: monospace; font-size: 13px; color: #fff; font-variant-numeric: tabular-nums; }}
.session-tag {{ font-size: 9px; padding: 1px 4px; border-radius: 3px; background: rgba(59,130,246,0.2); color: var(--accent); margin-left: 4px; border: 0.5px solid var(--accent); }}

.sync-btn {{ display: block; width: 100%; padding: 14px; background: rgba(255,255,255,0.05); color: #fff; text-align: center; text-decoration: none; border-radius: 14px; font-size: 14px; font-weight: 600; border: 1px solid var(--border); margin-bottom: 32px; transition: background 0.2s; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
.sync-btn:active {{ background: rgba(255,255,255,0.1); transform: translateY(1px); }}

h2 {{ font-size: 13px; font-weight: 700; margin: 0 0 16px; color: var(--text-dim); letter-spacing: 0.1em; display: flex; align-items: center; gap: 10px; text-transform: uppercase; }}
h2::after {{ content: ''; flex: 1; height: 1px; background: var(--border); }}
.milestone-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 24px; padding: 20px; margin-bottom: 16px; transition: all 0.3s ease; }}
.m-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; cursor: pointer; user-select: none; }}
.m-header:active {{ opacity: 0.7; }}
.m-title {{ font-weight: 700; font-size: 17px; }}
.toggle-icon {{ font-size: 10px; color: var(--text-dim); transition: transform 0.3s ease; }}
.milestone-card.collapsed .m-body {{ display: none; }}
.milestone-card.collapsed .m-header {{ margin-bottom: 0; }}
.milestone-card.collapsed .toggle-icon {{ transform: rotate(-90deg); }}
.m-status {{ font-size: 9px; font-weight: 800; padding: 3px 8px; border-radius: 8px; }}
.status-COMPLETED {{ background: rgba(16,185,129,0.1); color: var(--success); border: 1px solid var(--success); }}
.status-IN_PROGRESS {{ background: rgba(59,130,246,0.1); color: var(--accent); border: 1px solid var(--accent); }}
.status-PENDING {{ background: rgba(161,161,170,0.1); color: var(--text-dim); border: 1px solid var(--border); }}
.price-gap-box {{ background: rgba(255,255,255,0.03); padding: 12px; border-radius: 16px; border: 1px solid var(--border); }}
.pg-row {{ display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px; color: var(--text-dim); }}
.pg-val {{ color: #fff; font-weight: 600; font-variant-numeric: tabular-nums; font-feature-settings: "tnum" 1; }}
.main-gap {{ margin-top: 8px; padding-top: 8px; border-top: 1px dashed var(--border); color: #fff; }}
.main-gap .pg-val {{ font-size: 15px; }}
.progress-details {{ margin-bottom: 14px; }}
.detail-row {{ display: flex; justify-content: space-between; font-size: 12px; color: var(--text-dim); margin-bottom: 4px; }}
.detail-val {{ font-weight: 700; color: #fff; font-variant-numeric: tabular-nums; font-feature-settings: "tnum" 1; }}
.m-strategy {{ font-size: 12px; color: var(--text-dim); line-height: 1.6; padding-top: 14px; border-top: 1px solid var(--border); margin-top: 15px; }}
.progress-bg {{ background: rgba(255,255,255,0.03); height: 8px; border-radius: 10px; overflow: hidden; }}
.progress-fill {{ background: linear-gradient(90deg, var(--accent), #60a5fa); height: 100%; border-radius: 10px; transition: width 0.5s ease; }}
.account-block {{ margin-bottom: 28px; }}
.account-header {{ display: flex; justify-content: space-between; font-size: 14px; font-weight: 700; margin-bottom: 12px; padding: 0 4px; transition: opacity 0.2s; }}
.account-header:active {{ opacity: 0.7; }}
.account-block.collapsed .holdings-list {{ display: none; }}
.account-block.collapsed .toggle-icon {{ transform: rotate(-90deg); }}
.account-block.collapsed .account-header {{ margin-bottom: 0; }}
.asset-row {{ background: var(--card); border: 1px solid var(--border); padding: 14px 18px; border-radius: 18px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
.asset-name {{ font-weight: 700; font-size: 15px; }}
.qty {{ font-size: 11px; color: var(--text-dim); margin-left: 6px; }}
.asset-cost {{ font-size: 11px; color: var(--text-dim); margin-top: 2px; font-variant-numeric: tabular-nums; }}
.asset-status {{ font-weight: 800; font-size: 15px; font-variant-numeric: tabular-nums; font-feature-settings: "tnum" 1; }}
.up {{ color: var(--success); }}
.down {{ color: var(--danger); }}
.tab-bar {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px; background: var(--glass); border: 1px solid var(--border); border-radius: 14px; padding: 4px; margin-bottom: 24px; position: sticky; top: calc(8px + env(safe-area-inset-top)); z-index: 20; backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); }}
.tab-btn {{ appearance: none; border: 0; background: transparent; color: var(--text-dim); font-family: inherit; font-size: 13px; font-weight: 700; padding: 9px 0; border-radius: 10px; cursor: pointer; transition: background 0.2s, color 0.2s; }}
.tab-btn.active {{ background: var(--card); color: var(--text-main); box-shadow: 0 1px 3px rgba(0,0,0,0.35); }}
.tab-btn:active {{ opacity: 0.7; }}
.tab-panel {{ display: none; }}
.tab-panel.active {{ display: block; }}
.tab-panel > section:first-child {{ margin-top: 0 !important; }}
</style></head>
<body><div class="container">
<header><div class="header-top"><h1>📈 TQQQ Plan</h1><div><span class="v-tag" id="live-indicator" style="background: rgba(16,185,129,0.2); color: var(--success); margin-right: 4px; border: 1px solid var(--success); display: none; align-items: center; gap: 4px;">LIVE<span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:var(--success); animation: pulse 1.5s infinite;"></span></span><span class="v-tag">{SCRIPT_VERSION}</span></div></div><div class="last-update"><span id="backend-update-time">Last Update: {current_time_str}</span><span id="js-update-time" style="margin-left:6px;"></span></div></header>
<section class="main-summary">
    <div style="display: flex; justify-content: space-between; align-items: baseline;">
    <div>
        <div class="summary-label">Total Value (HKD)</div>
        <div class="summary-value" id="summary-total-value" style="font-size: 22px;">{format_hkd(total_value_hkd)}</div>
    </div>
    <div style="text-align: right;">
        <div class="summary-label">Total Profit</div>
        <div class="profit-display" id="summary-profit-display" style="color:{total_profit_color}; justify-content: flex-end;">
            <div class="summary-value" id="summary-total-profit" style="font-size: 22px;">{format_hkd(total_profit_hkd)}</div>
            <div class="profit-pct" id="summary-profit-pct">{total_profit_sign}{total_profit_pct:.1f}%</div>
        </div>
    </div>
    </div>
    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--border);">
    <div style="font-size: 11px; color: var(--text-dim);">總成本: <span id="summary-total-cost">{format_hkd(total_cost_hkd)}</span></div>
    <div style="text-align: right; font-size: 11px; color: var(--text-dim);">TODAY <span id="summary-today-profit" style="color: {d_change_color}; font-weight: 700;">{today_profit_display}</span> <span id="summary-today-pct" style="color: {d_change_color};">{today_profit_pct_display}</span></div>
    </div>
    <div style="font-size: 10px; color: var(--text-dim); margin-top: 6px; padding-top: 6px; border-top: 1px dashed var(--border);">未實現: {format_hkd(total_profit_hkd)} | 已實現: $0 (無沽出記錄)</div>
</section>
<section class="ticker-bar">
    {ticker_bar_html}
</section>

<nav class="tab-bar" id="tab-bar">
    <button class="tab-btn active" data-tab="overview">走勢</button>
    <button class="tab-btn" data-tab="targets">目標</button>
    <button class="tab-btn" data-tab="holdings">持倉</button>
    <button class="tab-btn" data-tab="trades">交易</button>
    <button class="tab-btn" data-tab="risk">風險</button>
    <button class="tab-btn" data-tab="stats">統計</button>
</nav>
<div class="tab-panel active" id="tab-overview">{chart_html}</div>
<div class="tab-panel" id="tab-targets"><section><h2>Strategic Targets</h2>{milestones_html}</section></div>
<div class="tab-panel" id="tab-holdings">{combined_html}<section style="margin-top: 32px; margin-bottom: 32px;"><h2>Holdings</h2>{accounts_html}</section></div>
<div class="tab-panel" id="tab-trades">{trades_html}</div>
<div class="tab-panel" id="tab-risk">{risk_html}</div>
<div class="tab-panel" id="tab-stats">{history_html}</div>

<div style="font-size: 10px; color: var(--text-dim); text-align: center; margin-bottom: 16px; padding: 10px; background: rgba(255,255,255,0.03); border-radius: 10px;">
    <div style="margin-bottom: 4px;"><b>Last Sync:</b> <span id="last-sync-time">{current_time_str}</span></div>
    <div><b>API Status:</b> <span id="api-status" style="color: var(--success);">✓ OK</span> · <b>Data:</b> <span id="data-freshness">Live</span></div>
</div>
<a class="sync-btn" id="triggerBtn" href="https://github.com/tsy-del/tqqq/actions/workflows/sync.yml" target="_blank" rel="noopener noreferrer">
    🔄 前往 GitHub Actions 手動觸發更新
</a>
<script>
// v6.3: Tab 切換（記住上次揀嗎個 tab）
(function() {{
    const KEY = 'tqqq_active_tab';
    const btns = document.querySelectorAll('.tab-btn');
    const panels = document.querySelectorAll('.tab-panel');

    function activate(name) {{
    let matched = false;
    panels.forEach(p => {{
        const on = p.id === 'tab-' + name;
        p.classList.toggle('active', on);
        if (on) matched = true;
    }});
    if (!matched) return false;
    btns.forEach(b => b.classList.toggle('active', b.dataset.tab === name));
    try {{ localStorage.setItem(KEY, name); }} catch(e) {{}}
    // 圖表在隱藏狀態下量不到寬度，重新顯示時要叫一次 resize
    if (name === 'overview') window.dispatchEvent(new Event('resize'));
    return true;
    }}

    btns.forEach(b => b.addEventListener('click', () => activate(b.dataset.tab)));

    let saved = null;
    try {{ saved = localStorage.getItem(KEY); }} catch(e) {{}}
    if (!saved || !activate(saved)) activate('overview');
}})();
</script>
<script>
</script>
</div><script>
let APP_DATA = {app_data_json};
const ACTIVE_TICKERS = {active_tickers_json};
const USD_HKD_RATE = {rate};
const TOTAL_COST_HKD = {int(round(total_cost_hkd))};

// v7.1: 直接从後台 (yfinance) 攻嚟每個 symbol 嘅 previousClose，唔再信 Finnhub 自己嘅 pc
// (發現 Finnhub 免費版对高波動 3x 槓杆 ETF 嘅 previousClose 持續性不正確)
const PREV_CLOSE = {prev_close_json};

// v7.1: Debug mode
const DEBUG = true;

async function fetchLivePrices() {{
    // v7.3: 收市時唔 call Finnhub（免費版冇盤前盤後），開市先 poll
    const ind = document.getElementById('live-indicator');
    const isOpen = isMarketOpenNow();
    
    if (!isOpen) {{
    // 收市：隱藏 LIVE indicator
    if (ind) {{
        ind.style.display = 'none';
    }}
    if (DEBUG) console.log('[v7.3] Market closed, skipping Finnhub call');
    return;
    }}
    
    if (DEBUG) console.log('[v7.3] Market open, fetching live prices');

    try {{
    const symbols = ACTIVE_TICKERS.join(',');
    const fhKey = 'da47k3hr01qo2j879nc0da47k3hr01qo2j879ncg'; // Updated to valid API key
    
    const promises = ACTIVE_TICKERS.map(sym => 
        fetch(`https://finnhub.io/api/v1/quote?symbol=${{sym}}&token=${{fhKey}}`).then(res => res.json())
    );
    const results = await Promise.all(promises);
    
    let newTotalValueHkd = 0;
    const prices = {{}};
    let gotAnyPrice = false;

    ACTIVE_TICKERS.forEach((sym, index) => {{
        const q = results[index];
        if (!q || !q.c) return;
        // q.c: Current price, q.pc: Previous close
        const price = q.c;
        prices[sym] = price;
        gotAnyPrice = true;
        
        const priceEl = document.getElementById(`ticker-price-${{sym}}`);
        if(priceEl) priceEl.innerText = `$${{price.toFixed(2)}}`;
        
        const chgEl = document.getElementById(`ticker-chg-${{sym}}`);
        // v7.1: 用後台 yfinance 嘅 previousClose 計 %变動，唔利用 Finnhub 自己嘅 pc
        const pc = PREV_CLOSE[sym];

        if(chgEl && pc) {{
            const chgPct = ((price - pc) / pc) * 100;
            chgEl.innerText = (chgPct >= 0 ? '+' : '') + chgPct.toFixed(1) + '%';
            chgEl.style.color = chgPct >= 0 ? 'var(--success)' : 'var(--danger)';
        }}
    }});

    // v7.1: 記錄 JS 前端實際跳價嘅本機時間 (唔靠後台 cron 時間)
    if (gotAnyPrice) {{
        const jsTimeEl = document.getElementById('js-update-time');
        if (jsTimeEl) {{
            const nowLocal = new Date();
            const hh = String(nowLocal.getHours()).padStart(2, '0');
            const mm = String(nowLocal.getMinutes()).padStart(2, '0');
            const ss = String(nowLocal.getSeconds()).padStart(2, '0');
            jsTimeEl.innerText = ' · 跳價 ' + hh + ':' + mm + ':' + ss;
            if (DEBUG) console.log('[v7.1] Update time:', jsTimeEl.innerText);
        }}
    }}

    APP_DATA.accounts.forEach(acc => {{
        acc.holdings.forEach(h => {{
            if (h.asset !== 'USD 現金' && prices[h.asset]) {{
                newTotalValueHkd += (h.quantity * prices[h.asset] * USD_HKD_RATE);
            }} else if (h.asset === 'USD 現金') {{
                newTotalValueHkd += (h.quantity * USD_HKD_RATE);
            }}
        }});
    }});
    
    if (newTotalValueHkd > 0) {{
        newTotalValueHkd = Math.round(newTotalValueHkd);
        const newTotalProfit = Math.round(newTotalValueHkd - TOTAL_COST_HKD);
        const newTotalProfitPct = (newTotalProfit / TOTAL_COST_HKD) * 100;
        
        const valEl = document.getElementById('summary-total-value');
        if(valEl) valEl.innerText = '$' + newTotalValueHkd.toLocaleString('en-US');
        
        const profitEl = document.getElementById('summary-total-profit');
        if(profitEl) profitEl.innerText = (newTotalProfit >= 0 ? '$' : '-$') + Math.abs(newTotalProfit).toLocaleString('en-US');
        
        const profitPctEl = document.getElementById('summary-profit-pct');
        const displayEl = document.getElementById('summary-profit-display');
        if(profitPctEl && displayEl) {{
            profitPctEl.innerText = (newTotalProfit >= 0 ? '+' : '') + newTotalProfitPct.toFixed(1) + '%';
            displayEl.style.color = newTotalProfit >= 0 ? '#10b981' : '#ef4444';
        }}
    }}

    // v7.3: 開市時顯示綠色 LIVE indicator
    if(ind) {{
        ind.innerHTML = 'LIVE<span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:var(--success); animation: pulse 1.5s infinite;"></span>';
        ind.style.background = 'rgba(16,185,129,0.2)';
        ind.style.color = 'var(--success)';
        ind.style.borderColor = 'var(--success)';
        ind.style.display = 'inline-flex';
        if (DEBUG) console.log('[v7.3] LIVE indicator: GREEN (market open)');
    }}
    
    }} catch(e) {{
    console.error('[v7.1] fetchLivePrices ERROR:', e);
    }}
}}

// v7.1: 立即執行，避免等待
if (DEBUG) console.log('[v7.1] Init - calling fetchLivePrices immediately');
fetchLivePrices();
setInterval(fetchLivePrices, 10000);

// v6.2: 靜默同步後台 data.json (每 60 秒)，唔需要人手 refresh
let LAST_SEEN_UPDATE = APP_DATA.last_updated;

function isMarketOpenNow() {{
    const nyTime = new Date(new Date().toLocaleString("en-US", {{timeZone: "America/New_York"}}));
    const day = nyTime.getDay();
    const t = nyTime.getHours() * 100 + nyTime.getMinutes();
    return (day >= 1 && day <= 5) && (t >= 930 && t < 1600);
}}

function fmtSigned(n) {{
    return (n >= 0 ? '$' : '-$') + Math.abs(Math.round(n)).toLocaleString('en-US');
}}

async function syncBackendData() {{
    try {{
    const res = await fetch('data.json?t=' + Date.now(), {{ cache: 'no-store' }});
    if (!res.ok) return;
    const fresh = await res.json();
    if (!fresh || !fresh.last_updated) return;
    if (fresh.last_updated === LAST_SEEN_UPDATE) return;

    LAST_SEEN_UPDATE = fresh.last_updated;
    APP_DATA = fresh;

    const upEl = document.querySelector('.last-update');
    const backendTimeEl = document.getElementById('backend-update-time');
    if (backendTimeEl) backendTimeEl.innerText = 'Last Update: ' + fresh.last_updated;

    // 開市時 summary 由 Finnhub live 主導，唔好覆蓋；收市就用後台數字
    if (!isMarketOpenNow() && fresh.portfolio_summary) {{
        const s = fresh.portfolio_summary;
        const valEl = document.getElementById('summary-total-value');
        if (valEl) valEl.innerText = '$' + Math.round(s.total_value_hkd).toLocaleString('en-US');
        const costEl = document.getElementById('summary-total-cost');
        if (costEl) costEl.innerText = '$' + Math.round(s.total_cost_hkd).toLocaleString('en-US');
        const profitEl = document.getElementById('summary-total-profit');
        if (profitEl) profitEl.innerText = fmtSigned(s.total_profit_hkd);
        const pctEl = document.getElementById('summary-profit-pct');
        const dispEl = document.getElementById('summary-profit-display');
        if (pctEl && s.total_cost_hkd) {{
            const pct = (s.total_profit_hkd / s.total_cost_hkd) * 100;
            pctEl.innerText = (s.total_profit_hkd >= 0 ? '+' : '') + pct.toFixed(1) + '%';
        }}
        if (dispEl) dispEl.style.color = s.total_profit_hkd >= 0 ? '#10b981' : '#ef4444';
    }}

    // 閃一下 Last Update 提示收到新數據
    if (upEl) {{
        upEl.style.transition = 'color 0.3s';
        upEl.style.color = 'var(--success)';
        setTimeout(() => {{ upEl.style.color = 'var(--text-dim)'; }}, 1200);
    }}
    }} catch(e) {{
    console.error('Backend sync failed:', e);
    }}
}}

setInterval(syncBackendData, 60000);
document.addEventListener('visibilitychange', () => {{
    if (!document.hidden) syncBackendData();
}});
</script>
</body></html>"""


    return new_html
