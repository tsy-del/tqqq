"""
portfolio_calculator.py — 持倉/利潤計算邏輯（從 sync_prices.py 拆出，項目 10）

負責：
- 格式化 HKD 金額
- Profit history 降採樣
- 持倉市值/成本/利潤計算（帳戶層 + 合併持倉）
- Milestone 進度計算
"""
from datetime import datetime


def format_hkd(num):
    return f"${num:,.0f}"


def downsample_history(history, now_ts):
    """v5.15: 分層降採樣，長期保留趨勢而唔會撞 5000 上限。

    分層規則（以距今時間計）：
      - 0-2 日      : 全保留（原始解析度）
      - 2-14 日     : 每 1 小時一個 bucket
      - 14-90 日    : 每 4 小時一個 bucket
      - 90 日以上   : 每 1 日一個 bucket

    每個 bucket 保留最高同最低兩點（去重後按時間排序），
    咁樣可以保住波幅上下限，唔會將尖頂尖底磨平。
    """
    if not history:
        return history

    DAY = 86400
    tiers = [
        (2 * DAY, 0),          # 全保留
        (14 * DAY, 3600),      # 1 小時
        (90 * DAY, 4 * 3600),  # 4 小時
        (None, DAY),           # 1 日
    ]

    def bucket_size_for(age):
        for max_age, size in tiers:
            if max_age is None or age < max_age:
                return size
        return DAY

    buckets = {}
    keep_raw = []
    for pt in history:
        t = pt.get('time')
        if t is None:
            continue
        age = now_ts - t
        size = bucket_size_for(age)
        if size == 0:
            keep_raw.append(pt)
        else:
            buckets.setdefault((size, t // size), []).append(pt)

    reduced = []
    for pts in buckets.values():
        hi = max(pts, key=lambda p: p['value'])
        lo = min(pts, key=lambda p: p['value'])
        picked = {hi['time']: hi, lo['time']: lo}
        reduced.extend(picked.values())

    out = reduced + keep_raw
    out.sort(key=lambda p: p['time'])

    # 去掉重複時間戳
    deduped = []
    seen = set()
    for pt in out:
        if pt['time'] in seen:
            continue
        seen.add(pt['time'])
        deduped.append(pt)
    return deduped


def compute_holdings_valuation(data, prices_data, rate):
    """計算每個帳戶及總體嘅市值/成本/利潤，並就地更新 data 內嘅帳戶。

    Returns: (total_value_hkd, total_cost_hkd, total_profit_hkd)
    """
    total_value_hkd = 0
    total_cost_hkd = 0
    for acc in data['accounts']:
        acc_val = 0
        acc_cost = 0
        for h in acc['holdings']:
            sym = h['asset']
            if sym in prices_data:
                h['current_price_usd'] = prices_data[sym]['price']

            asset_val = h['quantity'] * h['current_price_usd'] * rate
            asset_cost = h['quantity'] * h.get('avg_price_usd', 0) * rate
            acc_val += asset_val
            acc_cost += asset_cost

        acc['total_cost_hkd'] = int(round(acc_cost))
        acc['total_value_hkd'] = int(round(acc_val))
        acc['total_profit_hkd'] = int(round(acc_val - acc_cost))
        total_value_hkd += acc_val
        total_cost_hkd += acc_cost

    total_profit_hkd = total_value_hkd - total_cost_hkd
    return total_value_hkd, total_cost_hkd, total_profit_hkd


def compute_combined_positions(data):
    """按 symbol 合併所有帳戶嘅持倉數量及成本總額。

    Returns: dict[sym] -> {'qty': float, 'cost_sum': float}
    """
    combined_data = {}
    for acc in data['accounts']:
        for h in acc['holdings']:
            sym = h['asset']
            if sym == 'USD 現金':
                continue
            qty = h['quantity']
            avg = h.get('avg_price_usd', 0)
            if sym not in combined_data:
                combined_data[sym] = {'qty': 0, 'cost_sum': 0}
            combined_data[sym]['qty'] += qty
            combined_data[sym]['cost_sum'] += qty * avg
    return combined_data


def update_history_stats(data, current_profit, current_time_str):
    """更新歷史最高/最低利潤記錄，就地更新 data['history_stats']。"""
    if 'history_stats' not in data:
        data['history_stats'] = {
            "highest_profit_hkd": current_profit,
            "highest_profit_date": current_time_str,
            "lowest_profit_hkd": current_profit,
            "lowest_profit_date": current_time_str
        }
    else:
        if current_profit > int(round(data['history_stats'].get('highest_profit_hkd', -float('inf')))):
            data['history_stats']['highest_profit_hkd'] = current_profit
            data['history_stats']['highest_profit_date'] = current_time_str
        if current_profit < int(round(data['history_stats'].get('lowest_profit_hkd', float('inf')))):
            data['history_stats']['lowest_profit_hkd'] = current_profit
            data['history_stats']['lowest_profit_date'] = current_time_str
    # 清理歷史遺留小數位
    data['history_stats']['highest_profit_hkd'] = int(round(data['history_stats']['highest_profit_hkd']))
    data['history_stats']['lowest_profit_hkd'] = int(round(data['history_stats']['lowest_profit_hkd']))


def update_daily_stats(data, current_profit, current_ny_date_str, now_hms, profit_history):
    """更新今日最高/最低利潤及昨收基準，就地更新 data['daily_stats']。"""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    ny_tz = ZoneInfo("America/New_York")

    def _prev_close_from_history():
        try:
            for pt in reversed(profit_history):
                pt_date = datetime.fromtimestamp(pt['time'], ny_tz).strftime('%Y-%m-%d')
                if pt_date < current_ny_date_str:
                    return int(round(pt['value']))
        except Exception:
            pass
        return None

    prev_day = data.get('daily_stats') or {}
    if prev_day.get('date') != current_ny_date_str:
        prev_close = prev_day.get('last_profit_hkd')
        if prev_close is None:
            prev_close = _prev_close_from_history()
        data['daily_stats'] = {
            "date": current_ny_date_str,
            "highest_profit_hkd": current_profit,
            "lowest_profit_hkd": current_profit,
            "highest_time": now_hms,
            "lowest_time": now_hms,
            "prev_close_profit_hkd": int(round(prev_close)) if prev_close is not None else None,
            "last_profit_hkd": current_profit
        }
    else:
        ds = data['daily_stats']
        if current_profit > int(round(ds.get('highest_profit_hkd', -float('inf')))):
            ds['highest_profit_hkd'] = current_profit
            ds['highest_time'] = now_hms
        if current_profit < int(round(ds.get('lowest_profit_hkd', float('inf')))):
            ds['lowest_profit_hkd'] = current_profit
            ds['lowest_time'] = now_hms
        if ds.get('prev_close_profit_hkd') is None:
            bootstrap = _prev_close_from_history()
            if bootstrap is not None:
                ds['prev_close_profit_hkd'] = bootstrap
        ds['last_profit_hkd'] = current_profit
        ds['highest_profit_hkd'] = int(round(ds['highest_profit_hkd']))
        ds['lowest_profit_hkd'] = int(round(ds['lowest_profit_hkd']))


def compute_milestone_progress(total_profit_hkd, stage1_target=450000, stage2_target=1000000, stage3_target=550000):
    """計算三個 milestone stage 嘅進度百分比及可用利潤。

    Returns dict with prog1/2/3, profit_for_stage1/2/3, available_for_stage2/3
    """
    profit_for_stage1 = max(0, min(total_profit_hkd, stage1_target))
    prog1 = (profit_for_stage1 / stage1_target) * 100

    available_for_stage2 = total_profit_hkd - stage1_target
    profit_for_stage2 = max(0, min(available_for_stage2, stage2_target)) if available_for_stage2 > 0 else 0
    prog2 = (profit_for_stage2 / stage2_target) * 100

    available_for_stage3 = available_for_stage2 - stage2_target
    profit_for_stage3 = max(0, min(available_for_stage3, stage3_target)) if available_for_stage3 > 0 else 0
    prog3 = (profit_for_stage3 / stage3_target) * 100

    return {
        'prog1': prog1, 'profit_for_stage1': profit_for_stage1,
        'prog2': prog2, 'profit_for_stage2': profit_for_stage2, 'available_for_stage2': available_for_stage2,
        'prog3': prog3, 'profit_for_stage3': profit_for_stage3, 'available_for_stage3': available_for_stage3,
    }
