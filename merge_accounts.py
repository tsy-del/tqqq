import json

path = '/Users/tsy/.openclaw/workspace/tqqq-plan/data.json'
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

acc_a = None
acc_d = None
for acc in data['accounts']:
    if acc['account_name'].startswith('帳戶 A'):
        acc_a = acc
    elif acc['account_name'].startswith('帳戶 D'):
        acc_d = acc

if acc_a and acc_d:
    holdings_a = {h['asset']: h for h in acc_a['holdings']}
    
    for hd in acc_d['holdings']:
        asset = hd['asset']
        if asset in holdings_a:
            ha = holdings_a[asset]
            qty_a = ha['quantity']
            avg_a = ha['avg_price_usd']
            qty_d = hd['quantity']
            avg_d = hd['avg_price_usd']
            
            new_qty = qty_a + qty_d
            new_avg = ((qty_a * avg_a) + (qty_d * avg_d)) / new_qty
            
            ha['quantity'] = new_qty
            ha['avg_price_usd'] = round(new_avg, 4)
        else:
            acc_a['holdings'].append(hd)
            
    # Optionally update account A name
    # acc_a['account_name'] = "帳戶 A (滾動首期 + 滙豐)"
            
    data['accounts'] = [a for a in data['accounts'] if not a['account_name'].startswith('帳戶 D')]
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("Merge successful")
else:
    print("Could not find A or D")
