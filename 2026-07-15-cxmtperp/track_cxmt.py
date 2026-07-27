#!/usr/bin/env python3
"""
Hyperliquid CXMT Perpetual Future Tracker
Fetches real-time market context and 1-minute historical candlestick data for today
from the Hyperliquid API, calculates implied valuations, and formats them into
Org-mode tables and summaries.
"""

import sys
import time
import requests
from datetime import datetime, timezone, timedelta

# Constants for ChangXin Memory Technologies (CXMT)
TOTAL_SHARES = 66_880_000_000      # 66.88 Billion post-IPO total shares
OFFERING_SHARES = 6,688,000,000    # 6.688 Billion IPO offering shares (10% of total)
USD_CNY_RATE = 7.25                # standard USD to CNY conversion rate

def get_realtime_context():
    """
    Fetches real-time metadata and asset context from Hyperliquid info endpoint
    """
    url = "https://api.hyperliquid.xyz/info"
    payload = {
        "type": "metaAndAssetCtxs",
        "dex": "xyz"
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        if isinstance(data, list) and len(data) > 1:
            meta, ctxs = data[0], data[1]
            universe = meta.get("universe", [])
            for idx, asset in enumerate(universe):
                if asset.get("name") == "xyz:CXMT":
                    ctx = ctxs[idx] if idx < len(ctxs) else {}
                    return asset, ctx
        return None, None
    except Exception as e:
        sys.stderr.write(f"Error fetching real-time context: {e}\n")
        return None, None

def get_today_candles():
    """
    Fetches 1-minute candles for CXMT for today
    """
    url = "https://api.hyperliquid.xyz/info"
    
    # Calculate timestamps for today (local UTC+8)
    tz_local = timezone(timedelta(hours=8))
    now_local = datetime.now(tz_local)
    
    # Start of today (00:00:00 UTC+8)
    start_today = datetime(now_local.year, now_local.month, now_local.day, 0, 0, 0, tzinfo=tz_local)
    start_time_ms = int(start_today.timestamp() * 1000)
    
    # End time is now
    end_time_ms = int(time.time() * 1000)
    
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": "xyz:CXMT",
            "interval": "1m",
            "startTime": start_time_ms,
            "endTime": end_time_ms
        }
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        candles = response.json()
        
        # Filter to ensure candles belong to today local time
        today_candles = []
        for c in candles:
            dt = datetime.fromtimestamp(c['t'] / 1000, tz=tz_local)
            if dt.date() == start_today.date():
                today_candles.append(c)
        return today_candles
    except Exception as e:
        sys.stderr.write(f"Error fetching candles: {e}\n")
        return []

def format_valuation(usd_val):
    """Formats valuation in billions (B) or trillions (T) USD"""
    if usd_val >= 1e12:
        return f"${usd_val / 1e12:.3f}T"
    return f"${usd_val / 1e9:.3f}B"

def format_valuation_rmb(rmb_val):
    """Formats valuation in billions (B) or trillions (T) RMB"""
    if rmb_val >= 1e12:
        return f"RMB {rmb_val / 1e12:.3f}T"
    return f"RMB {rmb_val / 1e9:.3f}B"

def generate_price_chart(candles, filename="cxmt_price_chart.png"):
    """Generates a beautiful dark-mode price and volume chart using matplotlib"""
    try:
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError as e:
        sys.stderr.write(f"Warning: Could not import matplotlib for chart generation: {e}\n")
        return False

    if not candles:
        sys.stderr.write("Warning: No candles available to generate price chart.\n")
        return False

    try:
        tz_local = timezone(timedelta(hours=8))
        times = [datetime.fromtimestamp(c['t'] / 1000, tz=tz_local) for c in candles]
        closes = [float(c['c']) for c in candles]
        opens = [float(c['o']) for c in candles]
        volumes = [float(c['v']) for c in candles]
        
        # Create figure and subplots
        fig, (ax1, ax2) = plt.subplots(
            2, 1, 
            figsize=(11, 6), 
            sharex=True, 
            gridspec_kw={'height_ratios': [3, 1]}
        )
        
        # Sleek dark theme palette
        bg_color = "#131722"      # TradingView dark bg
        grid_color = "#2A2E39"    # Grid line color
        text_color = "#D9D9D9"    # Soft white for text
        line_color = "#00F0FF"    # Neon Cyan for close price
        
        fig.patch.set_facecolor(bg_color)
        ax1.set_facecolor(bg_color)
        ax2.set_facecolor(bg_color)
        
        # --- Top Panel: Price Line & Gradient Area ---
        ax1.plot(times, closes, color=line_color, linewidth=2.5, label="Close Price")
        
        # Calculate dynamic bottom for fill area
        min_close = min(closes)
        max_close = max(closes)
        y_bottom = min_close - (max_close - min_close) * 0.05 if max_close != min_close else min_close * 0.95
        ax1.fill_between(times, closes, y_bottom, color=line_color, alpha=0.1)
        
        # Grid lines
        ax1.grid(True, color=grid_color, linestyle='--', linewidth=0.5)
        
        # Title and Labels
        ax1.set_title("xyz:CXMT Perpetual Price & Volume (July 15, 2026)", color=text_color, fontsize=13, fontweight='bold', pad=12)
        ax1.set_ylabel("Price (USD)", color=text_color, fontsize=9, fontweight='bold')
        
        # Annotate latest price with a horizontal dotted line
        current_price = closes[-1]
        ax1.axhline(current_price, color=line_color, linestyle=':', alpha=0.6, linewidth=1.2)
        
        # Annotate Session High and Low
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
        
        # Print Current Price text right next to the last data point
        ax1.text(
            times[-1], current_price, f"  ${current_price:.4f}",
            color=line_color, fontweight='bold', va='center', ha='left', fontsize=9
        )
        
        # Styling axes spines
        for spine in ax1.spines.values():
            spine.set_color(grid_color)
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        
        # Tick parameters
        ax1.tick_params(colors=text_color, labelsize=9)
        
        # Adjust y-limit with padding
        y_range = max_close - min_close
        if y_range > 0:
            ax1.set_ylim(min_close - y_range * 0.1, max_close + y_range * 0.1)
        
        # --- Bottom Panel: Volume Bars ---
        # Volume bar colors: Green if close >= open, Red if close < open
        v_colors = ["#26a69a" if closes[i] >= opens[i] else "#ef5350" for i in range(len(candles))]
        
        # Matplotlib date-aware bar width (0.8 of a minute, in units of days)
        bar_width = 0.8 / 1440.0
        ax2.bar(times, volumes, width=bar_width, color=v_colors, alpha=0.85)
        
        # Grid lines
        ax2.grid(True, color=grid_color, linestyle='--', linewidth=0.5)
        ax2.set_ylabel("Volume", color=text_color, fontsize=9, fontweight='bold')
        
        # Styling axes spines
        for spine in ax2.spines.values():
            spine.set_color(grid_color)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        
        # Tick parameters
        ax2.tick_params(colors=text_color, labelsize=9)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax2.xaxis.set_major_locator(mdates.AutoDateLocator())
        
        # Autoturn date labels
        plt.gcf().autofmt_xdate()
        
        plt.tight_layout()
        plt.savefig(filename, facecolor=bg_color, edgecolor='none', dpi=150)
        plt.close()
        return True
    except Exception as e:
        sys.stderr.write(f"Error generating price chart: {e}\n")
        return False

def main():
    asset, ctx = get_realtime_context()
    candles = get_today_candles()
    
    tz_local = timezone(timedelta(hours=8))
    
    # Title / Header
    print("#+TITLE: Hyperliquid xyz:CXMT Tracker")
    print(f"#+DATE: {datetime.now(tz_local).strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)")
    print()

    if not asset or not ctx:
        print("Error: Could not retrieve real-time context for CXMT perp. Check API connection.")
        return

    # Generate price chart if candles are present
    chart_filename = "cxmt_price_chart.png"
    chart_generated = generate_price_chart(candles, chart_filename)

    # Extract real-time info
    mark_px = float(ctx.get('markPx', 0))
    mid_px = float(ctx.get('midPx', 0))
    prev_day_px = float(ctx.get('prevDayPx', 0))
    day_ntl_vlm = float(ctx.get('dayNtlVlm', 0))
    day_base_vlm = float(ctx.get('dayBaseVlm', 0))
    open_interest = float(ctx.get('openInterest', 0))
    funding_rate = float(ctx.get('funding', 0))
    premium = float(ctx.get('premium', 0)) if ctx.get('premium') is not None else 0.0
    
    # Calculate real-time valuations
    implied_val_usd = mark_px * TOTAL_SHARES
    implied_val_rmb = implied_val_usd * USD_CNY_RATE
    offering_val_usd = mark_px * 6_688_000_000
    offering_val_rmb = offering_val_usd * USD_CNY_RATE
    
    # Formatting funding
    funding_hourly_pct = funding_rate * 100
    funding_apr = funding_rate * 24 * 365 * 100

    # 1. Output Real-time Market Context Table
    print("* Real-Time Market Context")
    print("This table shows the latest real-time market data and calculated implied valuations based on the current mark price.")
    print()
    print("#+CAPTION: CXMT Real-Time Market Context")
    print("| Metric | Value | Description |")
    print("|--------+-------+-------------|")
    print(f"| Mark Price | ${mark_px:.4f} | Current fair value price used for liquidations |")
    print(f"| Mid Price | ${mid_px:.4f} | Midpoint of the current order book bid-ask spread |")
    print(f"| 24h Volume (USD) | ${day_ntl_vlm:,.2f} | Cumulative dollar trading volume in the last 24h |")
    print(f"| 24h Volume (CXMT) | {day_base_vlm:,.1f} | Cumulative contract trading volume in the last 24h |")
    print(f"| Open Interest | {open_interest:,.1f} | Outstanding active perpetual positions |")
    print(f"| Funding Rate | {funding_hourly_pct:.6f}% / hr | Hourly premium rate (APR: {funding_apr:.2f}%) |")
    print(f"| Spot Oracle Premium | {premium * 100:+.2f}% | Premium of perp price relative to index oracle |")
    print(f"| Implied IPO Offering Valuation | {format_valuation(offering_val_usd)} ({format_valuation_rmb(offering_val_rmb)}) | Valuation of the 6.688B new shares offered |")
    print(f"| Implied Fully Diluted Valuation | {format_valuation(implied_val_usd)} ({format_valuation_rmb(implied_val_rmb)}) | Total company valuation based on 66.88B shares |")
    print()

    # 1.5. Output Price Chart
    if chart_generated:
        print("* Price Chart")
        print("Visual representation of today's intraday price movement and trading volume.")
        print()
        print(f"[[file:{chart_filename}]]")
        print()

    # 2. Output Historical Table
    print("* Today's Pricing Data (1-Minute Candles)")
    print(f"Showing all granular 1-minute historical data for today (July 15, 2026). In total, {len(candles)} minutes of trading data are available.")
    print()
    print("#+CAPTION: CXMT 1-Minute Candlestick Data")
    print("| Time (Local) | Open (USD) | High (USD) | Low (USD) | Close (USD) | Volume (CXMT) | Notional (USD) | Fully Diluted Val (USD) | Fully Diluted Val (RMB) |")
    print("|--------------+------------+------------+-----------+-------------+---------------+----------------+-------------------------+-------------------------|")
    
    total_volume_candles = 0.0
    total_notional_candles = 0.0
    high_price_candles = -1.0
    low_price_candles = 1e9
    
    for c in candles:
        t_ms = c['t']
        dt = datetime.fromtimestamp(t_ms / 1000, tz=tz_local)
        time_str = dt.strftime('%Y-%m-%d %H:%M')
        
        o = float(c['o'])
        h = float(c['h'])
        l = float(c['l'])
        close = float(c['c'])
        v = float(c['v'])
        
        notional = close * v
        val_usd = close * TOTAL_SHARES
        val_rmb = val_usd * USD_CNY_RATE
        
        total_volume_candles += v
        total_notional_candles += notional
        if h > high_price_candles:
            high_price_candles = h
        if l < low_price_candles:
            low_price_candles = l
            
        val_usd_str = format_valuation(val_usd)
        val_rmb_str = format_valuation_rmb(val_rmb)
        
        print(f"| {time_str} | {o:10.4f} | {h:10.4f} | {l:9.4f} | {close:11.4f} | {v:13.1f} | ${notional:13.2f} | {val_usd_str:23} | {val_rmb_str:23} |")
        
    print()

    # 3. Output Market Summary
    if candles:
        first_candle = candles[0]
        last_candle = candles[-1]
        launch_price = float(first_candle['o'])
        current_price = float(last_candle['c'])
        price_change = current_price - launch_price
        pct_change = (price_change / launch_price) * 100
        
        print("* Market Summary Statistics")
        print("Summary of CXMT market activity since launch today:")
        print()
        print("#+CAPTION: CXMT Launch-to-Date Performance")
        print("| Metric | Value | Description |")
        print("|--------+-------+-------------|")
        print(f"| Launch Price | ${launch_price:.4f} | Opening price of first 1m candle |")
        print(f"| Current Price | ${current_price:.4f} | Closing price of most recent candle |")
        print(f"| Net Price Change | ${price_change:+.4f} ({pct_change:+.2f}%) | Price difference since launch |")
        print(f"| Session High | ${high_price_candles:.4f} | Highest traded price today |")
        print(f"| Session Low | ${low_price_candles:.4f} | Lowest traded price today |")
        print(f"| Cumulative Volume (CXMT) | {total_volume_candles:,.1f} tokens | Total contracts traded today |")
        print(f"| Cumulative Notional (USD) | ${total_notional_candles:,.2f} | Total USD value exchanged today |")
        print(f"| Implied Valuation (USD) | {format_valuation(current_price * TOTAL_SHARES)} | Based on current price & 66.88B shares |")
        print(f"| Implied Valuation (RMB) | {format_valuation_rmb(current_price * TOTAL_SHARES * USD_CNY_RATE)} | Converted at USD/CNY = {USD_CNY_RATE} |")
    else:
        print("* Market Summary Statistics")
        print("No historical candlestick data available for today yet.")

if __name__ == "__main__":
    main()
