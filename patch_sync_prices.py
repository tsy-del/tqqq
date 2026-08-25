import re
import os

repo_dir = "/Users/tsy/.openclaw/workspace/tqqq-plan"
file_path = os.path.join(repo_dir, "sync_prices.py")

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace version
content = content.replace('SCRIPT_VERSION = "v5.6"', 'SCRIPT_VERSION = "v5.7"')

# Replace daily stats logic
old_daily_logic = """        # Daily Stats Tracking
        ny_tz = ZoneInfo("America/New_York")
        current_ny_date_str = datetime.now(ny_tz).strftime('%Y-%m-%d')
        if 'daily_stats' not in data or data['daily_stats'].get('date') != current_ny_date_str:
            data['daily_stats'] = {
                "date": current_ny_date_str,
                "highest_profit_hkd": total_profit_hkd,
                "lowest_profit_hkd": total_profit_hkd,
                "highest_time": current_time_str.split(' ')[1],
                "lowest_time": current_time_str.split(' ')[1]
            }
        else:"""

new_daily_logic = """        # Daily Stats Tracking
        ny_tz = ZoneInfo("America/New_York")
        ny_now = datetime.now(ny_tz)
        
        # Switch trading date at 09:30 NY time (US Market Open)
        if ny_now.hour < 9 or (ny_now.hour == 9 and ny_now.minute < 30):
            trading_date_str = (ny_now - timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            trading_date_str = ny_now.strftime('%Y-%m-%d')
            
        if 'daily_stats' not in data or data['daily_stats'].get('date') != trading_date_str:
            data['daily_stats'] = {
                "date": trading_date_str,
                "highest_profit_hkd": total_profit_hkd,
                "lowest_profit_hkd": total_profit_hkd,
                "highest_time": current_time_str.split(' ')[1],
                "lowest_time": current_time_str.split(' ')[1]
            }
        else:"""
content = content.replace(old_daily_logic, new_daily_logic)

# Replace display HTML logic
old_html_logic = """        # Stats HTML
        ny_tz = ZoneInfo("America/New_York")
        current_ny_date_str = datetime.now(ny_tz).strftime('%Y-%m-%d')
        history_stats = data.get('history_stats', {})"""

new_html_logic = """        # Stats HTML
        ny_tz = ZoneInfo("America/New_York")
        ny_now = datetime.now(ny_tz)
        if ny_now.hour < 9 or (ny_now.hour == 9 and ny_now.minute < 30):
            trading_date_str = (ny_now - timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            trading_date_str = ny_now.strftime('%Y-%m-%d')
            
        history_stats = data.get('history_stats', {})"""
content = content.replace(old_html_logic, new_html_logic)

# Replace the text in HTML
old_html_display = """            <h2>Profit Stats (Today & History)</h2>
            <div class="milestone-card" style="border: 1px dashed var(--border); box-shadow: none;">
                <div class="m-body" style="display: block;">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-dim); margin-bottom: 8px;">今日 ({current_ny_date_str} US)</div>
                    <div class="detail-row" style="margin-bottom: 12px;">"""

new_html_display = """            <h2>Profit Stats (Today & History)</h2>
            <div class="milestone-card" style="border: 1px dashed var(--border); box-shadow: none;">
                <div class="m-body" style="display: block;">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-dim); margin-bottom: 8px;">今日 ({trading_date_str} US)</div>
                    <div class="detail-row" style="margin-bottom: 12px;">"""
content = content.replace(old_html_display, new_html_display)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched sync_prices.py")
