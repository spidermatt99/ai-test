import urllib.request
import json
import datetime
import time
import pandas as pd
import yfinance as yf

# Define constants
COIN = "xyz:SPCX"
DEX = "xyz"
STOCK_TICKER = "SPCX"
START_DATE = datetime.date(2026, 6, 12)
OUTPUT_FILE = "spacex_daily_report.org"

def fetch_hl_daily_candles(coin, dex, start_date):
    url = "https://api.hyperliquid.xyz/info"
    # Query from a bit before start date to ensure we cover it
    dt_start = datetime.datetime.combine(start_date - datetime.timedelta(days=1), datetime.time.min, tzinfo=datetime.timezone.utc)
    start_ms = int(dt_start.timestamp() * 1000)
    now_ms = int(time.time() * 1000)
    
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": "1d",
            "startTime": start_ms,
            "endTime": now_ms
        },
        "dex": dex
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    
    candles_data = []
    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode("utf-8"))
            if not res or not isinstance(res, list):
                print("No candles returned from Hyperliquid.")
                return pd.DataFrame()
            
            for c in res:
                # Convert timestamp
                dt = datetime.datetime.fromtimestamp(c['t'] / 1000, tz=datetime.timezone.utc).date()
                if dt < start_date:
                    continue
                
                o = float(c['o'])
                h = float(c['h'])
                l = float(c['l'])
                c_val = float(c['c'])
                v = float(c['v'])
                
                # Estimate buy and sell volume split using price pressure
                # buy_ratio = 0.5 + 0.5 * (close - open) / (high - low)
                if h > l:
                    buy_ratio = 0.5 + 0.5 * (c_val - o) / (h - l)
                    buy_ratio = max(0.1, min(0.9, buy_ratio)) # Clamp to avoid extreme values
                else:
                    buy_ratio = 0.5
                
                buy_vol = v * buy_ratio
                sell_vol = v * (1.0 - buy_ratio)
                
                candles_data.append({
                    "Date": dt,
                    "HL_Open": o,
                    "HL_High": h,
                    "HL_Low": l,
                    "HL_Close": c_val,
                    "HL_Buy_Vol": buy_vol,
                    "HL_Sell_Vol": sell_vol
                })
    except Exception as e:
        print(f"Error fetching Hyperliquid candles: {e}")
        return pd.DataFrame()
    
    df = pd.DataFrame(candles_data)
    if not df.empty:
        df = df.set_index("Date")
    return df

def fetch_stock_daily_ohlc(ticker_symbol, start_date):
    try:
        ticker = yf.Ticker(ticker_symbol)
        df_stock = ticker.history(start=start_date.strftime("%Y-%m-%d"), interval="1d")
        if df_stock.empty:
            print(f"No stock data returned from yfinance for {ticker_symbol}.")
            return pd.DataFrame()
        # Convert index to date object
        df_stock.index = df_stock.index.tz_localize(None).date
        df_stock = df_stock[["Open", "High", "Low", "Close"]].rename(columns={
            "Open": "Stock_Open",
            "High": "Stock_High",
            "Low": "Stock_Low",
            "Close": "Stock_Close"
        })
        return df_stock
    except Exception as e:
        print(f"Error fetching stock data from yfinance: {e}")
        return pd.DataFrame()

def main():
    print(f"Fetching SpaceX Hyperliquid Perp ({COIN}) daily data...")
    df_hl = fetch_hl_daily_candles(COIN, DEX, START_DATE)
    
    print(f"Fetching SpaceX Stock ({STOCK_TICKER}) daily data...")
    df_stock = fetch_stock_daily_ohlc(STOCK_TICKER, START_DATE)
    
    if df_hl.empty:
        print("Error: Hyperliquid data is empty. Cannot proceed.")
        return
        
    # Merge datasets
    df = df_hl.join(df_stock, how="outer").sort_index()
    
    # Calculate averages in Python for pre-population
    avg_row = {}
    for col in df.columns:
        avg_row[col] = df[col].mean()
    
    # Build Org-Mode Table
    table_lines = []
    # Header
    table_lines.append("| Date | HL Open | HL High | HL Low | HL Close | HL Buy Vol | HL Sell Vol | Stock Open | Stock High | Stock Low | Stock Close |")
    table_lines.append("|------+---------+---------+--------+----------+------------+-------------+------------+------------+-----------+-------------|")
    
    # Rows
    for dt, row in df.iterrows():
        # Date string
        dt_str = dt.strftime("%Y-%m-%d")
        
        # Format cells
        cells = [dt_str]
        for col in df.columns:
            val = row[col]
            if pd.isna(val):
                cells.append("")
            else:
                cells.append(f"{val:.2f}")
        table_lines.append("| " + " | ".join(cells) + " |")
        
    table_lines.append("|------+---------+---------+--------+----------+------------+-------------+------------+------------+-----------+-------------|")
    
    # Average Row
    avg_cells = ["Average"]
    for col in df.columns:
        val = avg_row[col]
        if pd.isna(val):
            avg_cells.append("")
        else:
            avg_cells.append(f"{val:.2f}")
    table_lines.append("| " + " | ".join(avg_cells) + " |")
    
    # Add Org-mode formula
    # Columns are 1-indexed: 
    # $2: HL Open, $3: HL High, $4: HL Low, $5: HL Close, $6: HL Buy Vol, $7: HL Sell Vol
    # $8: Stock Open, $9: Stock High, $10: Stock Low, $11: Stock Close
    formula_parts = []
    for col_idx in range(2, 12):
        formula_parts.append(f"@>${col_idx}=vmean(@2..@-1);format(\"%.2f\")")
    formula_str = "#+TBLFM: " + "::".join(formula_parts)
    table_lines.append(formula_str)
    
    table_content = "\n".join(table_lines)
    
    # Generate Org-Mode Document
    report_text = f"""#+TITLE: SpaceX Daily Trading & Volume Report (Stock vs Hyperliquid Perp)
#+DATE: [{datetime.datetime.now().strftime('%Y-%m-%d %a %H:%M')}]
#+AUTHOR: SpaceX Market Analyzer
#+DESCRIPTION: Daily comparison of SpaceX (NASDAQ: SPCX) stock and Hyperliquid synthetic perp (xyz:SPCX) prices and volume split.
#+OPTIONS: toc:nil num:nil

* Overview
This report contains a comparative daily breakdown of Space Exploration Technologies Corp. (SpaceX) assets starting from the NASDAQ IPO debut on June 12, 2026 to the present date. 

It tracks:
1. *Hyperliquid SPCX Perp (xyz:SPCX)*: Synthetic perpetual futures contract trading 24/7.
2. *NASDAQ SpaceX Stock (SPCX)*: Official equity traded on public markets during standard exchange hours.

** Buy and Sell Volume Methodology
Since the Hyperliquid API's historical public endpoints do not store a pre-computed daily buy/sell breakdown, this report derives the split by analyzing intra-day price pressure:
- *Buy Ratio* is estimated as: 0.5 + 0.5 * (Close - Open) / (High - Low) (clamped between 10% and 90% to manage range anomalies).
- *Sell Ratio* is 1.0 - Buy Ratio.
- Daily Buy and Sell volumes are calculated by multiplying these ratios by the daily total candlestick volume.

* Daily Price and Volume Comparison Table

{table_content}

* Analysis and Interpretation
- *Off-Hours Action*: The Hyperliquid perpetual contract continues to trade on weekends and holidays (like June 13-14, June 19, and June 20-21) when traditional public markets are closed.
- *Volume Split*: Daily buy and sell volumes fluctuate based on price movements. Days with a large positive close-open spread reflect stronger buy-side pressure and higher buy volumes.
- *Average Values*: The bottom row displays the arithmetic mean of all trading days. Averages for the stock columns are computed only over the days traditional stock trading was available (business days).
"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"Daily report generated successfully and written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
