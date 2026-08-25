import json

path = '/Users/tsy/.openclaw/workspace/tqqq-plan/data.json'
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

new_account = {
  "account_name": "帳戶 D (滙豐 - P683880)",
  "total_value_hkd": 87750,
  "total_profit_hkd": 0,
  "total_cost_hkd": 87750,
  "holdings": [
    {
      "asset": "SPCX",
      "quantity": 75,
      "avg_price_usd": 150.00,
      "current_price_usd": 150.00
    }
  ]
}

data['accounts'].append(new_account)

with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
