with open("sync_prices.py", "r") as f:
    content = f.read()

target = "if (uniqueData.length === 1) {"
replacement = "uniqueData.sort((a,b) => a.time - b.time);\n                if (uniqueData.length === 1) {"

if target in content and "uniqueData.sort" not in content:
    content = content.replace(target, replacement)

with open("sync_prices.py", "w") as f:
    f.write(content)

