with open("sync_prices.py", "r") as f:
    content = f.read()

# Add position:relative to chart-container is already there
# But we need to make sure LightweightCharts renders correctly on mobile/iOS where it sometimes needs an explicit height on parents.
# Wait, let's check if there's any CSS issue. 
# Another common issue is JS error blocking rendering. Let's add a console fallback.

chart_html_fix = """
        chart_html = f'''<section style="margin-top: 32px; margin-bottom: 32px;">
            <h2>Profit Trend</h2>
            <div id="chart-container" style="width: 100%; height: 220px; background: var(--card); border: 1px solid var(--border); border-radius: 16px; overflow: hidden; position: relative;"></div>
            <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
            <script>
                document.addEventListener('DOMContentLoaded', () => {{
                    try {{
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
                        
                        profitData.sort((a,b) => a.time - b.time);
                        
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
                    }} catch (e) {{
                        console.error("Chart Error:", e);
                        document.getElementById('chart-container').innerHTML = '<div style="padding:20px;color:red;font-size:12px;">圖表載入失敗: ' + e.message + '</div>';
                    }}
                }});
            </script>
        </section>'''
"""

import re
# Regex to replace the chart_html assignment block
content = re.sub(
    r"chart_html = f'''<section style=\"margin-top: 32px; margin-bottom: 32px;\">.*?</section>'''",
    chart_html_fix.strip(),
    content,
    flags=re.DOTALL
)

with open("sync_prices.py", "w") as f:
    f.write(content)
