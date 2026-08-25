import json
import time
import random

now = int(time.time())
history = []

# Generate data for the last 48 hours, one point every hour
start_val = 135125
current_val = start_val

for i in range(48, -1, -1):
    timestamp = now - (i * 3600)
    
    if i == 48:
        current_val = 135125
    elif i == 24:
        current_val = 323332 # match history high
    elif i == 0:
        current_val = 152818 # current
    else:
        # random walk
        current_val += random.randint(-15000, 15000)
        
    history.append({
        "time": timestamp,
        "value": current_val
    })

with open('profit_history.json', 'w') as f:
    json.dump(history, f)

