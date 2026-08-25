with open("sync_prices.py", "r") as f:
    content = f.read()

# Fix the sort issue properly. Lightweight charts requires strictly increasing time
fix = """
                const uniqueData = [];
                const seenTimes = new Set();
                for (const point of profitData) {
                    if (!seenTimes.has(point.time)) {
                        seenTimes.add(point.time);
                        uniqueData.push(point);
                    }
                }
                
                if (uniqueData.length === 1) {
                    uniqueData.unshift({ time: uniqueData[0].time - 3600, value: uniqueData[0].value });
                }
"""

new_fix = """
                const uniqueData = [];
                const seenTimes = new Set();
                
                // Ensure data is sorted by time
                profitData.sort((a,b) => a.time - b.time);
                
                for (const point of profitData) {
                    if (!seenTimes.has(point.time)) {
                        seenTimes.add(point.time);
                        uniqueData.push(point);
                    }
                }
                
                if (uniqueData.length === 1) {
                    uniqueData.unshift({ time: uniqueData[0].time - 3600, value: uniqueData[0].value });
                }
"""

if "profitData.sort((a,b) => a.time - b.time);" not in content:
    content = content.replace(fix, new_fix)
    print("Fixed sorting")

with open("sync_prices.py", "w") as f:
    f.write(content)
