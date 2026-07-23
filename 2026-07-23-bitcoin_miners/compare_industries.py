import yfinance as yf
import pandas as pd

# Define industry ETFs
industries = {
    'XLK': 'Technology Sector',
    'SMH': 'Semiconductors',
    'XLU': 'Utilities Sector',
    'XLRE': 'Real Estate',
    'XLE': 'Energy Sector',
    'XLF': 'Financial Sector',
    'GDX': 'Gold Miners',
    'SPY': 'S&P 500 (Broad Market)',
    'QQQ': 'Nasdaq-100 (Tech Heavy)'
}

# Add top miners for comparison
miners = {
    'IREN': 'IREN (Top Miner Pivot)',
    'WULF': 'TeraWulf (Top Miner Pivot)',
    'HUT': 'Hut 8 (Top Miner Pivot)'
}

symbols = list(industries.keys()) + list(miners.keys())

data = yf.download(symbols, start="2023-01-01", end="2026-07-23")
if isinstance(data.columns, pd.MultiIndex):
    if 'Close' in data.columns.levels[0]:
        df = data['Close']
    else:
        df = data.xs('Close', axis=1, level=0)
else:
    df = data

df = df.ffill().bfill()

# Calculate returns
res = []
for s in symbols:
    if s in df.columns:
        s_series = df[s].dropna()
        if not s_series.empty:
            start_2023 = s_series.iloc[0]
            start_2026_idx = s_series.index[s_series.index <= '2025-12-31'][-1]
            start_2026 = s_series.loc[start_2026_idx]
            curr = s_series.iloc[-1]
            
            gain_from_2023 = ((curr - start_2023) / start_2023) * 100
            gain_ytd_2026 = ((curr - start_2026) / start_2026) * 100
            
            name = industries.get(s, miners.get(s))
            res.append({
                'Symbol': s,
                'Name/Industry': name,
                'Gain_Since_Jan_2023_%': round(float(gain_from_2023), 2),
                'Gain_2026_YTD_%': round(float(gain_ytd_2026), 2)
            })

df_res = pd.DataFrame(res).sort_values(by='Gain_Since_Jan_2023_%', ascending=False)
print(df_res.to_string(index=False))
