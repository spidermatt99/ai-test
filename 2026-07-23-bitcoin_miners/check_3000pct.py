import yfinance as yf
import pandas as pd

symbols = ['HUT', 'WULF', 'RIOT', 'CORZ', 'CIFR', 'CLSK', 'MARA', 'APLD', 'BTDR', 'IREN', 'BTBT', 'CAN', 'NVDA', 'BTC-USD', 'SMCI']
data = yf.download(symbols, start="2023-01-01", end="2026-07-23")
if isinstance(data.columns, pd.MultiIndex):
    if 'Close' in data.columns.levels[0]:
        df = data['Close']
    else:
        df = data.xs('Close', axis=1, level=0)
else:
    df = data

df = df.ffill().bfill()

res = []
for s in symbols:
    if s in df.columns:
        s_series = df[s].dropna()
        if not s_series.empty:
            low_2023 = s_series.loc['2023-01-01':'2023-12-31'].min()
            high_all = s_series.max()
            curr = s_series.iloc[-1]
            gain_low_to_curr = ((curr - low_2023) / low_2023) * 100
            gain_low_to_max = ((high_all - low_2023) / low_2023) * 100
            res.append({
                'Symbol': s,
                'Low_2023': round(float(low_2023), 2),
                'Max_Price': round(float(high_all), 2),
                'Current_Price': round(float(curr), 2),
                'Max_Peak_Gain_%': round(float(gain_low_to_max), 2),
                'Current_Gain_From_2023_Low_%': round(float(gain_low_to_curr), 2)
            })

df_res = pd.DataFrame(res).sort_values(by='Max_Peak_Gain_%', ascending=False)
print(df_res.to_string(index=False))
