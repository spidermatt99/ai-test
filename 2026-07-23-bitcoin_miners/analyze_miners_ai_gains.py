import datetime
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# Set style for modern visual look
plt.style.use('ggplot')

# Define tickers from chatgpt-research.md and benchmark indices / assets
# Stock tickers:
# HUT: Hut 8
# WULF: TeraWulf
# RIOT: Riot Platforms
# CORZ: Core Scientific
# CIFR: Cipher Digital
# CLSK: CleanSpark
# MARA: MARA Holdings
# APLD: Applied Digital
# BTDR: Bitdeer Technologies
# IREN: IREN (Iris Energy)
# BTBT: Bit Digital
# CAN: Canaan

# Benchmarks:
# BTC-USD: Bitcoin
# ^GSPC: S&P 500
# ^IXIC: Nasdaq Composite

tickers_miners = {
    'HUT': {'name': 'Hut 8', 'ai_pivot_date': '2024-09-01'},      # ~Sept 2024 H100 cluster / HPC focus
    'WULF': {'name': 'TeraWulf', 'ai_pivot_date': '2024-10-01'},   # ~Oct 2024 Nautilus sale & Lake Mariner HPC shift
    'RIOT': {'name': 'Riot Platforms', 'ai_pivot_date': '2025-01-01'}, # Early 2025 AMD Rockdale deal
    'CORZ': {'name': 'Core Scientific', 'ai_pivot_date': '2024-06-01'},# June 2024 CoreWeave 12-yr HPC contract
    'CIFR': {'name': 'Cipher Digital', 'ai_pivot_date': '2024-10-01'}, # Fall 2024 Barber Lake HPC pivot
    'CLSK': {'name': 'CleanSpark', 'ai_pivot_date': '2025-10-01'},     # Late 2025 dedicated AI strategy
    'MARA': {'name': 'MARA Holdings', 'ai_pivot_date': '2025-06-01'},  # Mid-2025 Exaion & Starwood AI partnership
    'APLD': {'name': 'Applied Digital', 'ai_pivot_date': '2023-05-01'},# May 2023 CoreWeave anchor lease
    'BTDR': {'name': 'Bitdeer', 'ai_pivot_date': '2023-11-01'},        # Late 2023 AI cloud launch
    'IREN': {'name': 'IREN', 'ai_pivot_date': '2023-11-01'},           # Late 2023 GPU cloud launch
    'BTBT': {'name': 'Bit Digital', 'ai_pivot_date': '2023-10-01'},    # Oct 2023 WhiteFiber GPU rollout
    'CAN': {'name': 'Canaan', 'ai_pivot_date': '2024-01-01'},          # Baseline comparison (no major AI pivot)
}

benchmarks = {
    'BTC-USD': 'Bitcoin',
    '^GSPC': 'S&P 500',
    '^IXIC': 'Nasdaq'
}

all_symbols = list(tickers_miners.keys()) + list(benchmarks.keys())

print("Fetching historical price data via yfinance...")
start_fetch = "2023-01-01"
end_fetch = "2026-07-23"

raw_data = yf.download(all_symbols, start=start_fetch, end=end_fetch)

# Extract Adj Close or Close
if 'Adj Close' in raw_data and not raw_data['Adj Close'].dropna().empty:
    df_data = raw_data['Adj Close']
else:
    df_data = raw_data['Close']

# Fill missing values forward and backward
df_data = df_data.ffill().bfill()

# 1. Calculate YTD Gains for 2026 (Dec 31, 2025 to latest 2026 date)
start_2026_idx = df_data.index[df_data.index <= '2025-12-31'][-1]
latest_idx = df_data.index[-1]

ytd_gains = {}

# Compute YTD for miners
for ticker, info in tickers_miners.items():
    start_price = df_data.loc[start_2026_idx, ticker]
    end_price = df_data.loc[latest_idx, ticker]
    gain_pct = ((end_price - start_price) / start_price) * 100
    ytd_gains[f"{info['name']} ({ticker})"] = (gain_pct, 'Miner')

# Compute YTD for benchmarks
for symbol, name in benchmarks.items():
    start_price = df_data.loc[start_2026_idx, symbol]
    end_price = df_data.loc[latest_idx, symbol]
    gain_pct = ((end_price - start_price) / start_price) * 100
    ytd_gains[f"{name} [{symbol}]"] = (gain_pct, 'Benchmark')

df_ytd = pd.DataFrame([
    {'Asset': k, 'YTD_Gain_%': v[0], 'Type': v[1]} for k, v in ytd_gains.items()
]).sort_values(by='YTD_Gain_%', ascending=True)

# 2. Calculate Since-AI-Pivot Gains for Miners
pivot_gains = []
for ticker, info in tickers_miners.items():
    pivot_date = info['ai_pivot_date']
    valid_dates = df_data.index[df_data.index >= pivot_date]
    if len(valid_dates) > 0:
        p_date = valid_dates[0]
        start_price = df_data.loc[p_date, ticker]
        end_price = df_data.loc[latest_idx, ticker]
        gain_pct = ((end_price - start_price) / start_price) * 100
        pivot_gains.append({
            'Ticker': ticker,
            'Company': info['name'],
            'Pivot_Date': pivot_date,
            'Start_Price': round(float(start_price), 2),
            'Current_Price': round(float(end_price), 2),
            'Gain_Since_Pivot_%': round(float(gain_pct), 2)
        })

df_pivot = pd.DataFrame(pivot_gains).sort_values(by='Gain_Since_Pivot_%', ascending=False)

print("\n========================================================")
print(" 1. 2026 YTD PERFORMANCE COMPARISON")
print("========================================================")
for idx, row in df_ytd.iloc[::-1].iterrows():
    print(f"{row['Asset']:<25}: {row['YTD_Gain_%']:>7.2f}%  [{row['Type']}]")

print("\n========================================================")
print(" 2. GAINS SINCE LEANING INTO AI / PIVOT DATE")
print("========================================================")
print(df_pivot.to_string(index=False))

# 3. Create Horizontal Bar Chart comparing YTD gains to Bitcoin, S&P 500, and Nasdaq
fig, ax = plt.subplots(figsize=(12, 7))

colors = ['#2b5c8f' if t == 'Miner' else '#f2a900' if 'Bitcoin' in a else '#2e7d32' for a, t in zip(df_ytd['Asset'], df_ytd['Type'])]

bars = ax.barh(df_ytd['Asset'], df_ytd['YTD_Gain_%'], color=colors, edgecolor='black', alpha=0.88, height=0.65)

# Add values next to bars
min_val = df_ytd['YTD_Gain_%'].min()
max_val = df_ytd['YTD_Gain_%'].max()

for bar in bars:
    width = bar.get_width()
    offset = 1.0 if width >= 0 else -4.5
    ax.text(width + offset, bar.get_y() + bar.get_height()/2, f"{width:+.1f}%",
            va='center', ha='left' if width >= 0 else 'right', fontsize=9.5, fontweight='bold')

ax.set_title("2026 YTD Stock Gains: AI Bitcoin Miners vs. Benchmarks (Bitcoin, S&P 500, Nasdaq)", fontsize=13, pad=15, fontweight='bold')
ax.set_xlabel("2026 YTD Return (%)", fontsize=11, labelpad=10)
ax.axvline(0, color='black', linewidth=1.0, linestyle='--')

# Custom legend
legend_elements = [
    Patch(facecolor='#2b5c8f', edgecolor='black', label='Bitcoin Miners'),
    Patch(facecolor='#f2a900', edgecolor='black', label='Bitcoin (BTC-USD)'),
    Patch(facecolor='#2e7d32', edgecolor='black', label='Stock Indices (S&P 500 / Nasdaq)')
]
ax.legend(handles=legend_elements, loc='lower right', frameon=True, facecolor='white', framealpha=0.9)

plt.tight_layout()
output_img = "bitcoin_miners_ai_ytd_gains.png"
plt.savefig(output_img, dpi=300)
print(f"\nChart saved successfully as '{output_img}'.")
