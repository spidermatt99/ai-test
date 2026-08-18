import requests

data = requests.post('https://api.hyperliquid.xyz/info', json={'type': 'metaAndAssetCtxs', 'dex': 'xyz'}).json()
assets = data[0]['universe']
ctxs = data[1]

results = []
for a, c in zip(assets, ctxs):
    oi_usd = float(c['openInterest']) * float(c['markPx'])
    vol24h_usd = float(c['dayNtlVlm'])
    results.append({
        'name': a['name'],
        'oi': oi_usd,
        'vol': vol24h_usd
    })

results.sort(key=lambda x: x['oi'], reverse=True)

print("Top 10 Pre-IPO Perps by Open Interest:")
print(f"{'Asset':<15} | {'Open Interest (USD)':<25} | {'24h Volume (USD)':<20}")
print("-" * 65)

for r in results[:10]:
    print(f"{r['name']:<15} | ${r['oi']:>23,.2f} | ${r['vol']:>18,.2f}")
    
# also find unitree and cxmt explicitly just in case they are not in top 10
print("\nSpecific Lookup:")
for r in results:
    if r['name'] in ['xyz:UNITREE', 'xyz:CXMT']:
        print(f"{r['name']:<15} | ${r['oi']:>23,.2f} | ${r['vol']:>18,.2f}")
