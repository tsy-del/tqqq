with open("sync_prices.py", "r") as f:
    content = f.read()

# Fix sorting issue for Lightweight Charts
fix = """
                if (uniqueData.length === 1) {
"""

new_fix = """
                uniqueData.sort((a,b) => a.time - b.time);
                if (uniqueData.length === 1) {
"""

content = content.replace(fix, new_fix)
with open("sync_prices.py", "w") as f:
    f.write(content)
