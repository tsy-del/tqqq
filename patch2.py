import re

with open("sync_prices.py", "r") as f:
    content = f.read()

# Update version
content = content.replace('SCRIPT_VERSION = "v5.3"', 'SCRIPT_VERSION = "v5.4"')

# Add PROFIT_HISTORY_FILE
content = content.replace("INDEX_FILE = os.path.join(REPO_DIR, 'index.html')", 
                          "INDEX_FILE = os.path.join(REPO_DIR, 'index.html')\nPROFIT_HISTORY_FILE = os.path.join(REPO_DIR, 'profit_history.json')")

# Add Profit History Logging for Chart
history_logic = """        data['portfolio_summary']['total_profit_hkd'] = int(round(total_profit_hkd))

        # Profit History Logging for Chart
        if os.path.exists(PROFIT_HISTORY_FILE):
            with open(PROFIT_HISTORY_FILE, 'r', encoding='utf-8') as f:
                try:
                    profit_history = json.load(f)
                except:
                    profit_history = []
        else:
            profit_history = []
            
        current_unix_time = int(datetime.now(hk_tz).timestamp())
        
        if not profit_history or profit_history[-1]['time'] < current_unix_time:
            profit_history.append({
                "time": current_unix_time,
                "value": int(round(total_profit_hkd))
            })
            
        if len(profit_history) > 5000:
            profit_history = profit_history[-5000:]
            
        with open(PROFIT_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(profit_history, f, ensure_ascii=False)"""
content = content.replace("        data['portfolio_summary']['total_profit_hkd'] = int(round(total_profit_hkd))", history_logic)

chart_html = """        profit_history_json_str = json.dumps(profit_history)
        
        chart_html = f'''<section style="margin-top: 32px; margin-bottom: 32px;">
            <h2>Profit Trend</h2>
            <div id="chart-container" style="width: 100%; height: 220px; background: var(--card); border: 1px solid var(--border); border-radius: 16px; overflow: hidden; position: relative;"></div>
            <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
            <script>
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
                chart.timeScale().fitContent();
                
                new ResizeObserver(entries => {{
                    if (entries.length === 0 || entries[0].target !== chartContainer) {{ return; }}
                    const newRect = entries[0].contentRect;
                    chart.applyOptions({{ width: newRect.width, height: newRect.height }});
                }}).observe(chartContainer);
            </script>
        </section>'''

        history_html = f\"\"\"<section style=\"margin-top: 32px; margin-bottom: 32px;\">"""
content = content.replace("        history_html = f\"\"\"<section style=\"margin-top: 32px; margin-bottom: 32px;\">", chart_html)

# Insert chart HTML into new_html
content = content.replace("<section style=\"margin-top: 32px; margin-bottom: 32px;\"><h2>Holdings</h2>{accounts_html}</section>\\n{history_html}", "<section style=\"margin-top: 32px; margin-bottom: 32px;\"><h2>Holdings</h2>{accounts_html}</section>\\n{chart_html}\\n{history_html}")

# Add profit_history.json to git add
content = content.replace('run_git(["add", "data.json", "index.html", "sync_prices.py"])', 'run_git(["add", "data.json", "index.html", "sync_prices.py", "profit_history.json"])')

with open("sync_prices.py", "w") as f:
    f.write(content)

