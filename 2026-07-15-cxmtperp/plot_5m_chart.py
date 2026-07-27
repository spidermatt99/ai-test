#!/usr/bin/env python3
"""
Hyperliquid xyz:CXMT 5-Minute Intraday Price Chart Generator
Fetches 5-minute candles for today (July 27, 2026) and renders a dark-mode price & volume chart.
"""

import sys
import time
import requests
from datetime import datetime, timezone, timedelta

def get_today_5m_candles():
    url = "https://api.hyperliquid.xyz/info"
    tz_local = timezone(timedelta(hours=8))
    now_local = datetime.now(tz_local)
    
    # Start of today 00:00:00 local time
    start_today = datetime(now_local.year, now_local.month, now_local.day, 0, 0, 0, tzinfo=tz_local)
    start_time_ms = int(start_today.timestamp() * 1000)
    end_time_ms = int(time.time() * 1000)
    
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": "xyz:CXMT",
            "interval": "5m",
            "startTime": start_time_ms,
            "endTime": end_time_ms
        }
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        candles = response.json()
        
        today_candles = []
        for c in candles:
            dt = datetime.fromtimestamp(c['t'] / 1000, tz=tz_local)
            if dt.date() == start_today.date():
                today_candles.append(c)
        return today_candles
    except Exception as e:
        sys.stderr.write(f"Error fetching 5m candles: {e}\n")
        return []

def plot_5m_chart(candles, filename="cxmt_5m_chart.png"):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    if not candles:
        sys.stderr.write("No candles available to plot.\n")
        return False

    tz_local = timezone(timedelta(hours=8))
    times = [datetime.fromtimestamp(c['t'] / 1000, tz=tz_local) for c in candles]
    closes = [float(c['c']) for c in candles]
    opens = [float(c['o']) for c in candles]
    highs = [float(c['h']) for c in candles]
    lows = [float(c['l']) for c in candles]
    volumes = [float(c['v']) for c in candles]

    # Create figure and subplots
    fig, (ax1, ax2) = plt.subplots(
        2, 1, 
        figsize=(12, 6.5), 
        sharex=True, 
        gridspec_kw={'height_ratios': [3, 1]}
    )

    # Sleek dark theme palette
    bg_color = "#131722"      # Dark bg
    grid_color = "#2A2E39"    # Grid line color
    text_color = "#D9D9D9"    # Soft white
    line_color = "#00F0FF"    # Neon Cyan

    fig.patch.set_facecolor(bg_color)
    ax1.set_facecolor(bg_color)
    ax2.set_facecolor(bg_color)

    # --- Top Panel: Price Line & Gradient Area ---
    ax1.plot(times, closes, color=line_color, linewidth=2.2, marker='o', markersize=3, label="Close Price (5m)")

    min_close = min(closes)
    max_close = max(closes)
    y_bottom = min_close * 0.98
    ax1.fill_between(times, closes, y_bottom, color=line_color, alpha=0.12)

    ax1.grid(True, color=grid_color, linestyle='--', linewidth=0.5)
    ax1.set_title("xyz:CXMT Perpetual 5-Minute Intraday Chart (July 27, 2026)", color=text_color, fontsize=13, fontweight='bold', pad=12)
    ax1.set_ylabel("Price (USD)", color=text_color, fontsize=9, fontweight='bold')

    current_price = closes[-1]
    ax1.axhline(current_price, color=line_color, linestyle=':', alpha=0.7, linewidth=1.2)

    # Annotate High and Low
    high_idx = closes.index(max_close)
    low_idx = closes.index(min_close)

    ax1.annotate(
        f"High: ${max_close:.4f}",
        xy=(times[high_idx], max_close),
        xytext=(10, 10),
        textcoords="offset points",
        arrowprops=dict(arrowstyle="->", color="#00E676", lw=1.2),
        color="#00E676",
        fontweight="bold",
        fontsize=9
    )

    ax1.annotate(
        f"Low: ${min_close:.4f}",
        xy=(times[low_idx], min_close),
        xytext=(10, -18),
        textcoords="offset points",
        arrowprops=dict(arrowstyle="->", color="#FF5252", lw=1.2),
        color="#FF5252",
        fontweight="bold",
        fontsize=9
    )

    # Current Price tag
    ax1.text(
        times[-1], current_price, f"  ${current_price:.4f}",
        color=line_color, fontweight='bold', va='center', ha='left', fontsize=9
    )

    for spine in ax1.spines.values():
        spine.set_color(grid_color)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.tick_params(colors=text_color, labelsize=9)

    y_range = max_close - min_close
    if y_range > 0:
        ax1.set_ylim(min_close - y_range * 0.08, max_close + y_range * 0.08)

    # --- Bottom Panel: Volume Bars ---
    v_colors = ["#26a69a" if closes[i] >= opens[i] else "#ef5350" for i in range(len(candles))]
    bar_width = 4.0 / 1440.0  # 4 minutes width in days

    ax2.bar(times, volumes, width=bar_width, color=v_colors, alpha=0.85)
    ax2.grid(True, color=grid_color, linestyle='--', linewidth=0.5)
    ax2.set_ylabel("Volume", color=text_color, fontsize=9, fontweight='bold')

    for spine in ax2.spines.values():
        spine.set_color(grid_color)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    ax2.tick_params(colors=text_color, labelsize=9)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax2.xaxis.set_major_locator(mdates.HourLocator(interval=1))

    plt.gcf().autofmt_xdate()
    plt.tight_layout()
    plt.savefig(filename, facecolor=bg_color, edgecolor='none', dpi=150)
    plt.close()
    print(f"Chart successfully saved to {filename}")
    return True

if __name__ == "__main__":
    candles = get_today_5m_candles()
    plot_5m_chart(candles)
