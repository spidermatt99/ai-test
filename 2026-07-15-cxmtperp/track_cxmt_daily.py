#!/usr/bin/env python3
"""
Hyperliquid CXMT Perpetual Future Daily Tracker
Fetches daily (1d) historical candlestick data from the Hyperliquid API,
saves it to a CSV file, generates a graph, and outputs an org-mode table.
"""

import sys
import csv
import time
from datetime import datetime, timezone, timedelta
import requests

# Constants for ChangXin Memory Technologies (CXMT)
TOTAL_SHARES = 66_880_000_000
USD_CNY_RATE = 7.25

def get_daily_candles():
    url = "https://api.hyperliquid.xyz/info"
    # Launch date: July 15, 2026
    start_time_ms = int(datetime(2026, 7, 15, 0, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    end_time_ms = int(time.time() * 1000)
    
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": "xyz:CXMT",
            "interval": "1d",
            "startTime": start_time_ms,
            "endTime": end_time_ms
        }
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        sys.stderr.write(f"Error fetching candles: {e}\n")
        return []

def format_valuation(usd_val):
    if usd_val >= 1e12:
        return f"${usd_val / 1e12:.3f}T"
    return f"${usd_val / 1e9:.3f}B"

def format_valuation_rmb(rmb_val):
    if rmb_val >= 1e12:
        return f"RMB {rmb_val / 1e12:.3f}T"
    return f"RMB {rmb_val / 1e9:.3f}B"

def generate_daily_price_chart(candles, filename="cxmt_daily_chart.png"):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError as e:
        sys.stderr.write(f"Warning: Could not import matplotlib: {e}\n")
        return False

    if not candles:
        return False

    try:
        tz_local = timezone(timedelta(hours=8))
        times = [datetime.fromtimestamp(c['t'] / 1000, tz=tz_local) for c in candles]
        closes = [float(c['c']) for c in candles]
        opens = [float(c['o']) for c in candles]
        volumes = [float(c['v']) for c in candles]
        
        fig, (ax1, ax2) = plt.subplots(
            2, 1, 
            figsize=(11, 6), 
            sharex=True, 
            gridspec_kw={'height_ratios': [3, 1]}
        )
        
        bg_color = "#131722"
        grid_color = "#2A2E39"
        text_color = "#D9D9D9"
        line_color = "#00F0FF"
        
        fig.patch.set_facecolor(bg_color)
        ax1.set_facecolor(bg_color)
        ax2.set_facecolor(bg_color)
        
        ax1.plot(times, closes, color=line_color, marker='o', linewidth=2)
        
        min_close = min(closes)
        max_close = max(closes)
        y_bottom = min_close * 0.95
        ax1.fill_between(times, closes, y_bottom, color=line_color, alpha=0.1)
        
        ax1.grid(True, color=grid_color, linestyle='--', linewidth=0.5)
        ax1.set_title("xyz:CXMT Perpetual Daily Price & Volume", color=text_color, fontsize=13, fontweight='bold', pad=12)
        ax1.set_ylabel("Price (USD)", color=text_color, fontsize=9, fontweight='bold')
        
        for spine in ax1.spines.values():
            spine.set_color(grid_color)
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.tick_params(colors=text_color, labelsize=9)
        
        v_colors = ["#26a69a" if closes[i] >= opens[i] else "#ef5350" for i in range(len(candles))]
        
        ax2.bar(times, volumes, color=v_colors, alpha=0.85, width=0.5)
        ax2.grid(True, color=grid_color, linestyle='--', linewidth=0.5)
        ax2.set_ylabel("Volume", color=text_color, fontsize=9, fontweight='bold')
        
        for spine in ax2.spines.values():
            spine.set_color(grid_color)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        
        ax2.tick_params(colors=text_color, labelsize=9)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.gcf().autofmt_xdate()
        
        plt.tight_layout()
        plt.savefig(filename, facecolor=bg_color, edgecolor='none', dpi=150)
        plt.close()
        return True
    except Exception as e:
        sys.stderr.write(f"Error generating chart: {e}\n")
        return False

def main():
    candles = get_daily_candles()
    tz_local = timezone(timedelta(hours=8))

    # Generate Chart
    chart_filename = "cxmt_daily_chart.png"
    chart_generated = generate_daily_price_chart(candles, chart_filename)

    # Export to CSV
    csv_filename = "cxmt_daily_data.csv"
    with open(csv_filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Open", "High", "Low", "Close", "Volume", "Notional (USD)", "Fully Diluted Val (USD)", "Fully Diluted Val (RMB)"])
        for c in candles:
            dt = datetime.fromtimestamp(c['t'] / 1000, tz=tz_local)
            date_str = dt.strftime('%Y-%m-%d')
            o, h, l, close, v = float(c['o']), float(c['h']), float(c['l']), float(c['c']), float(c['v'])
            notional = close * v
            val_usd = close * TOTAL_SHARES
            val_rmb = val_usd * USD_CNY_RATE
            writer.writerow([date_str, o, h, l, close, v, notional, val_usd, val_rmb])

    # Output Org Mode Table
    print("* Daily Pricing Data")
    print("Showing daily historical data for the CXMT perpetual contract.")
    print(f"Data also saved to [[file:{csv_filename}]]")
    print()
    if chart_generated:
        print(f"[[file:{chart_filename}]]")
        print()

    print("#+CAPTION: CXMT Daily Candlestick Data")
    print("| Date | Open (USD) | High (USD) | Low (USD) | Close (USD) | Volume (CXMT) | Notional (USD) | Fully Diluted Val (USD) | Fully Diluted Val (RMB) |")
    print("|------+------------+------------+-----------+-------------+---------------+----------------+-------------------------+-------------------------|")
    
    for c in candles:
        dt = datetime.fromtimestamp(c['t'] / 1000, tz=tz_local)
        date_str = dt.strftime('%Y-%m-%d')
        o, h, l, close, v = float(c['o']), float(c['h']), float(c['l']), float(c['c']), float(c['v'])
        notional = close * v
        val_usd = close * TOTAL_SHARES
        val_rmb = val_usd * USD_CNY_RATE
        
        val_usd_str = format_valuation(val_usd)
        val_rmb_str = format_valuation_rmb(val_rmb)
        
        print(f"| {date_str} | {o:10.4f} | {h:10.4f} | {l:9.4f} | {close:11.4f} | {v:13.1f} | ${notional:13.2f} | {val_usd_str:23} | {val_rmb_str:23} |")

if __name__ == "__main__":
    main()
