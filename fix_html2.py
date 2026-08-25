with open("sync_prices.py", "r") as f:
    content = f.read()

target = "{history_html}"
replacement = "{chart_html}\n{history_html}"

if "{chart_html}\n{history_html}" not in content:
    content = content.replace(target, replacement)
    
with open("sync_prices.py", "w") as f:
    f.write(content)

