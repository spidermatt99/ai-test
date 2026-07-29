import argparse
import requests
import time
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone

def fetch_candles(coin="xyz:SKHX", interval="15m", days=3):
    """Fetches candle data from Hyperliquid info API."""
    url = "https://api.hyperliquid.xyz/info"
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - (days * 24 * 3600 * 1000)
    
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": interval,
            "startTime": start_ms,
            "endTime": now_ms
        }
    }
    
    res = requests.post(url, json=payload).json()
    return res

def process_data(candles):
    """Converts candle list into a structured pandas DataFrame."""
    df = pd.DataFrame(candles)
    df['datetime_utc'] = pd.to_datetime(df['t'], unit='ms', utc=True)
    
    for col in ['o', 'h', 'l', 'c', 'v']:
        df[col] = df[col].astype(float)
        
    df.rename(columns={
        't': 'timestamp_ms',
        'o': 'open',
        'h': 'high',
        'l': 'low',
        'c': 'close',
        'v': 'volume_shares',
        'n': 'trade_count'
    }, inplace=True)
    
    df['volume_usd'] = df['close'] * df['volume_shares']
    
    csv_cols = ['datetime_utc', 'timestamp_ms', 'open', 'high', 'low', 'close', 'volume_shares', 'volume_usd', 'trade_count']
    return df[csv_cols]

def plot_chart(df, output_img="skhynix_perps_3d_chart.png", days=3):
    """Plots dark-themed price and volume chart with bright, high-contrast text."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
    
    fig.patch.set_facecolor('#0b0f19')
    ax1.set_facecolor('#111827')
    ax2.set_facecolor('#111827')
    
    # Price Plot
    ax1.plot(df['datetime_utc'], df['close'], color='#38bdf8', linewidth=2.0, label='SKHX Close Price ($)')
    ax1.fill_between(df['datetime_utc'], df['low'], df['high'], color='#38bdf8', alpha=0.18, label='15m High-Low Range')
    ax1.set_title(f'SK Hynix Perps (xyz:SKHX) - Hyperliquid {days}-Day ({df.attrs.get("interval", "15-Minute")}) Price Movement', fontsize=16, fontweight='bold', color='#ffffff', pad=15)
    ax1.set_ylabel('Price ($)', fontsize=13, fontweight='bold', color='#ffffff')
    ax1.grid(True, linestyle='--', alpha=0.25, color='#94a3b8')
    ax1.tick_params(colors='#ffffff', labelsize=11)
    ax1.legend(loc='upper left', facecolor='#1e293b', edgecolor='#475569', labelcolor='#ffffff', fontsize=11)
    
    # Volume Plot
    colors = ['#22c55e' if row['close'] >= row['open'] else '#f43f5e' for _, row in df.iterrows()]
    ax2.bar(df['datetime_utc'], df['volume_usd'] / 1e6, width=0.007, color=colors, alpha=0.85)
    ax2.set_ylabel('Volume ($M)', fontsize=13, fontweight='bold', color='#ffffff')
    ax2.set_xlabel('Date / Time (UTC)', fontsize=13, fontweight='bold', color='#ffffff')
    ax2.grid(True, linestyle='--', alpha=0.25, color='#94a3b8')
    ax2.tick_params(colors='#ffffff', labelsize=11)
    
    # X-axis date formatting
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %d\n%H:%M'))
    ax2.xaxis.set_major_locator(mdates.HourLocator(interval=6))
    
    for ax in [ax1, ax2]:
        for spine in ax.spines.values():
            spine.set_color('#475569')
            
    plt.tight_layout()
    plt.savefig(output_img, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    print(f"Chart successfully saved to {output_img}")

def main():
    parser = argparse.ArgumentParser(description="Fetch Hyperliquid SK Hynix perps data and generate chart & CSV.")
    parser.add_argument("--days", type=int, default=3, help="Number of historical days (default: 3)")
    parser.add_argument("--interval", type=str, default="15m", help="Candle interval (default: 15m)")
    parser.add_argument("--csv", type=str, default="skhynix_perps_3d_15m.csv", help="Output CSV filename")
    parser.add_argument("--chart", type=str, default="skhynix_perps_3d_chart.png", help="Output chart image filename")
    args = parser.parse_args()

    print(f"Fetching {args.days}-day {args.interval} candle data from Hyperliquid...")
    candles = fetch_candles(coin="xyz:SKHX", interval=args.interval, days=args.days)
    
    if not candles:
        print("No data received from API.")
        return

    df = process_data(candles)
    interval_display = f"{args.interval} Candles"
    df.attrs['interval'] = interval_display
    df.to_csv(args.csv, index=False)
    print(f"Saved {len(df)} rows to {args.csv}")

    plot_chart(df, output_img=args.chart, days=args.days)

if __name__ == "__main__":
    main()
