#!/usr/bin/env python3
"""
Exports 5-minute candle data for Monday (July 27, 2026) starting 00:00 GMT+8 to CSV.
"""

import sys
import csv
import time
import requests
from datetime import datetime, timezone, timedelta

TOTAL_SHARES = 66_880_000_000
USD_CNY_RATE = 7.25

def main():
    url = "https://api.hyperliquid.xyz/info"
    tz_gmt8 = timezone(timedelta(hours=8))
    
    monday_start = datetime(2026, 7, 27, 0, 0, 0, tzinfo=tz_gmt8)
    start_time_ms = int(monday_start.timestamp() * 1000)
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
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    candles = response.json()
    
    csv_filename = "cxmt_5m_monday_data.csv"
    with open(csv_filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Timestamp (GMT+8)", "Date", "Time", 
            "Open (USD)", "High (USD)", "Low (USD)", "Close (USD)", 
            "Volume (CXMT)", "Notional (USD)", 
            "Fully Diluted Val (USD)", "Fully Diluted Val (RMB)"
        ])
        
        for c in candles:
            dt = datetime.fromtimestamp(c['t'] / 1000, tz=tz_gmt8)
            date_str = dt.strftime('%Y-%m-%d')
            time_str = dt.strftime('%H:%M')
            full_ts = dt.strftime('%Y-%m-%d %H:%M:%S')
            
            o = float(c['o'])
            h = float(c['h'])
            l = float(c['l'])
            close = float(c['c'])
            v = float(c['v'])
            
            notional = close * v
            val_usd = close * TOTAL_SHARES
            val_rmb = val_usd * USD_CNY_RATE
            
            writer.writerow([
                full_ts, date_str, time_str, 
                f"{o:.4f}", f"{h:.4f}", f"{l:.4f}", f"{close:.4f}", 
                f"{v:.1f}", f"{notional:.2f}", 
                f"{val_usd:.2f}", f"{val_rmb:.2f}"
            ])
            
    print(f"Successfully exported {len(candles)} rows to {csv_filename}")

if __name__ == "__main__":
    main()
