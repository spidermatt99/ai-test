import yfinance as yf
import pandas as pd

# November 30, 2022
start_date = "2022-11-30"
end_date = "2026-07-23"

miners = ['HUT', 'WULF', 'RIOT', 'CORZ', 'CIFR', 'CLSK', 'MARA', 'APLD', 'BTDR', 'IREN']
symbols = ['SMH'] + miners

data = yf.download(symbols, start=start_date, end=end_date)
if isinstance(data.columns, pd.MultiIndex):
    if 'Close' in data.columns.levels[0]:
        df = data['Close']
    else:
        df = data.xs('Close', axis=1, level=0)
else:
    df = data

df = df.ffill().bfill()

# Get prices on Nov 30, 2022
start_idx = df.index[df.index >= start_date][0]
start_prices = df.loc[start_idx]

# Get current prices
curr_prices = df.iloc[-1]

# Calculate gains
smh_gain = ((curr_prices['SMH'] - start_prices['SMH']) / start_prices['SMH']) * 100

miner_gains = []
for m in miners:
    if m in start_prices and m in curr_prices:
        g = ((curr_prices[m] - start_prices[m]) / start_prices[m]) * 100
        miner_gains.append(g)

avg_miner_gain = sum(miner_gains) / len(miner_gains)

print(f"SMH Gain: {smh_gain:.2f}%")
print(f"Avg Top 10 Miner Gain: {avg_miner_gain:.2f}%")
