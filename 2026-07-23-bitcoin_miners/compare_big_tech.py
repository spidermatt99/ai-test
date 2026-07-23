import yfinance as yf
import pandas as pd

big_tech = {
    'AAPL': 'Apple',
    'MSFT': 'Microsoft',
    'GOOGL': 'Alphabet (Google)',
    'AMZN': 'Amazon',
    'META': 'Meta',
    'NVDA': 'Nvidia',
    'TSLA': 'Tesla'
}

symbols = list(big_tech.keys())

data = yf.download(symbols, start="2022-11-30", end="2026-07-23")
if isinstance(data.columns, pd.MultiIndex):
    if 'Close' in data.columns.levels[0]:
        df = data['Close']
    else:
        df = data.xs('Close', axis=1, level=0)
else:
    df = data

df = df.ffill().bfill()

start_2026_idx = df.index[df.index <= '2025-12-31'][-1]
start_2026_prices = df.loc[start_2026_idx]

nov_2022_idx = df.index[df.index >= '2022-11-30'][0]
nov_2022_prices = df.loc[nov_2022_idx]

curr_prices = df.iloc[-1]

res = []
for s in symbols:
    if s in df.columns:
        gain_ytd = ((curr_prices[s] - start_2026_prices[s]) / start_2026_prices[s]) * 100
        gain_nov2022 = ((curr_prices[s] - nov_2022_prices[s]) / nov_2022_prices[s]) * 100
        res.append({
            'Company': big_tech[s],
            'Symbol': s,
            'Gain_Since_ChatGPT_Launch_%': round(float(gain_nov2022), 2),
            'Gain_2026_YTD_%': round(float(gain_ytd), 2)
        })

df_res = pd.DataFrame(res).sort_values(by='Gain_Since_ChatGPT_Launch_%', ascending=False)
print("=== BIG TECH PERFORMANCE ===")
print(df_res.to_string(index=False))
