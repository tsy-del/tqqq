with open("sync_prices.py", "r") as f:
    content = f.read()

# Make sure chart_html is rendered by adding {chart_html} back to new_html
if "{chart_html}" not in content:
    content = content.replace("<section style=\"margin-top: 32px; margin-bottom: 32px;\"><h2>Holdings</h2>{accounts_html}</section>\n{history_html}", "<section style=\"margin-top: 32px; margin-bottom: 32px;\"><h2>Holdings</h2>{accounts_html}</section>\n{chart_html}\n{history_html}")
else:
    print("chart_html tag already there")
    
with open("sync_prices.py", "w") as f:
    f.write(content)
