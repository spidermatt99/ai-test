import urllib.request
import json
import datetime
import matplotlib.pyplot as plt

tokens = {
    'pendle': 'Pendle (PENDLE)',
    'ondo-finance': 'Ondo (ONDO)',
    'ethena': 'Ethena (ENA)'
}

plt.figure(figsize=(10, 6))

for coin_id, label in tokens.items():
    url = f'https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=90'
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        req = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode('utf-8'))
        
        prices = data.get('prices', [])
        # Extract timestamps and prices
        dates = [datetime.datetime.utcfromtimestamp(p[0] / 1000) for p in prices]
        vals = [p[1] for p in prices]
        
        # Normalize to percentage change from 90 days ago so they can be compared on the same axis
        if vals:
            base_price = vals[0]
            pct_change = [((v - base_price) / base_price) * 100 for v in vals]
            plt.plot(dates, pct_change, label=label)
            
    except Exception as e:
        print(f"Error fetching {coin_id}: {e}")

plt.title('90-Day Performance of Trump-Associated DeFi Tokens (Normalized % Change)')
plt.xlabel('Date')
plt.ylabel('Percentage Change (%)')
plt.grid(True, linestyle='--', alpha=0.7)
plt.axhline(0, color='black', linewidth=1)
plt.legend()
plt.tight_layout()

# Save the chart to the artifacts directory
chart_path = r'C:\Users\matth\.gemini\antigravity-cli\brain\2713d0c5-9879-4a96-bd76-d15692acfb4d\defi_performance_chart.png'
plt.savefig(chart_path)
print(f"Chart successfully saved to {chart_path}")
