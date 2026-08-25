import json
import time
import math
import random

now = int(time.time())
history = []

# 模擬過去 30 日嘅數據 (每小時一點)
for i in range(720, 0, -1):
    timestamp = now - (i * 3600)
    progress = 1 - (i / 720.0)
    
    # 趨勢：由負數 (-50,000) 慢慢升到而家嘅 158,000
    trend = -50000 + (158000 - (-50000)) * progress
    
    # 波浪：加入幾個起伏
    wave = math.sin(progress * math.pi * 3.5) * 60000
    
    # 噪音
    noise = random.randint(-5000, 5000)
    
    val = int(trend + wave + noise)
    
    history.append({
        "time": timestamp,
        "value": val
    })

# 保留本身最後一兩點嘅真數據，我哋讀取返出嚟
try:
    with open('profit_history.json', 'r') as f:
        real_data = json.load(f)
        for point in real_data:
            if point['time'] > history[-1]['time']:
                history.append(point)
except:
    pass

with open('profit_history.json', 'w') as f:
    json.dump(history, f)
