with open("sync_prices.py", "r") as f:
    content = f.read()

target = '<section style="margin-top: 32px; margin-bottom: 32px;"><h2>Holdings</h2>{accounts_html}</section>\n{history_html}'
replacement = '<section style="margin-top: 32px; margin-bottom: 32px;"><h2>Holdings</h2>{accounts_html}</section>\n{chart_html}\n{history_html}'

if target in content:
    content = content.replace(target, replacement)
else:
    print("Could not find target string. Trying another...")
    target2 = '<section style="margin-top: 32px; margin-bottom: 32px;"><h2>Holdings</h2>{accounts_html}</section>\\n{history_html}'
    if target2 in content:
        content = content.replace(target2, replacement)
    else:
        # manual replace
        content = content.replace('{accounts_html}</section>\\n{history_html}', '{accounts_html}</section>\\n{chart_html}\\n{history_html}')
        content = content.replace('{accounts_html}</section>\n{history_html}', '{accounts_html}</section>\n{chart_html}\n{history_html}')

with open("sync_prices.py", "w") as f:
    f.write(content)

