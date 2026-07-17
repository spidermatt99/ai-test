import json
import urllib.request
import time
import datetime
import pandas as pd
import yfinance as yf

# Listing dates (all dates in UTC)
LISTING_DATES = {
    "Cerebras": "2026-05-14",
    "SpaceX": "2026-06-12",
    "Quantinuum": "2026-06-04"
}

TICKERS = {
    "Cerebras": {"hl": "xyz:CBRS", "stock": "CBRS"},
    "SpaceX": {"hl": "xyz:SPCX", "stock": "SPCX"},
    "Quantinuum": {"hl": "xyz:QNT", "stock": "QNT"}
}

def fetch_hl_candles_range(coin, start_dt, end_dt, interval):
    url = "https://api.hyperliquid.xyz/info"
    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = int(end_dt.timestamp() * 1000)
    
    body = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": interval,
            "startTime": start_ts,
            "endTime": end_ts
        }
    }
    req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode('utf-8'))
            records = []
            for candle in data:
                dt = datetime.datetime.fromtimestamp(candle['t'] / 1000, tz=datetime.timezone.utc)
                if not (start_dt <= dt <= end_dt):
                    continue
                time_str = dt.strftime("%m-%d %H:%M")
                records.append({
                    "Time": time_str,
                    "Perp_O": round(float(candle['o']), 2),
                    "Perp_H": round(float(candle['h']), 2),
                    "Perp_L": round(float(candle['l']), 2),
                    "Perp_C": round(float(candle['c']), 2)
                })
            df = pd.DataFrame(records)
            if not df.empty:
                df = df.set_index("Time")
            return df
    except Exception as e:
        print(f"Error fetching HL candles for {coin}: {e}")
        return pd.DataFrame()

def fetch_yf_candles_range(symbol, start_dt, end_dt, interval):
    try:
        ticker = yf.Ticker(symbol)
        query_start = start_dt.strftime("%Y-%m-%d")
        query_end = (end_dt + datetime.timedelta(days=2)).strftime("%Y-%m-%d")
        df_stock = ticker.history(start=query_start, end=query_end, interval=interval)
        if df_stock.empty:
            return pd.DataFrame()
        df_stock.index = df_stock.index.tz_convert("UTC")
        records = []
        for idx, row in df_stock.iterrows():
            # Align timestamps to match Hyperliquid
            aligned_dt = idx.replace(second=0, microsecond=0)
            if interval == "1h":
                aligned_dt = aligned_dt.replace(minute=0)
            elif interval == "15m":
                # round minute to nearest 15 minute step (0, 15, 30, 45)
                m = (aligned_dt.minute // 15) * 15
                aligned_dt = aligned_dt.replace(minute=m)
                
            if not (start_dt <= aligned_dt <= end_dt):
                continue
            time_str = aligned_dt.strftime("%m-%d %H:%M")
            records.append({
                "Time": time_str,
                "Stock_O": round(float(row["Open"]), 2),
                "Stock_H": round(float(row["High"]), 2),
                "Stock_L": round(float(row["Low"]), 2),
                "Stock_C": round(float(row["Close"]), 2)
            })
        df = pd.DataFrame(records)
        if not df.empty:
            df = df.set_index("Time")
        return df
    except Exception as e:
        print(f"Error fetching YF hourly for {symbol}: {e}")
        return pd.DataFrame()

def main():
    hourly_comparisons = {}
    for company, tickers in TICKERS.items():
        print(f"Detecting start of trading for {company}...")
        
        # 1. First fetch hourly stock data to find the first traded hour
        listing_date_str = LISTING_DATES[company]
        listing_dt = datetime.datetime.strptime(listing_date_str, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
        query_end_dt = listing_dt + datetime.timedelta(days=2)
        
        df_initial_stock = fetch_yf_candles_range(tickers["stock"], listing_dt, query_end_dt, "1h")
        if df_initial_stock.empty:
            print(f"Could not find stock data for {company} listing day.")
            continue
            
        df_initial_stock = df_initial_stock.reset_index()
        first_time_str = df_initial_stock["Time"].iloc[0]
        first_dt = datetime.datetime.strptime(first_time_str, "%m-%d %H:%M").replace(year=2026, tzinfo=datetime.timezone.utc)
        
        # End at 20:00 UTC (4:00 PM EST) of listing day
        end_dt = first_dt.replace(hour=20, minute=0)
        
        # Determine the most granular matching interval (Cerebras must be 1h; SpaceX & Quantinuum have 15m)
        interval = "15m"
        if company == "Cerebras":
            interval = "1h"
            
        print(f"Selected granularity: {interval}. Trading hours: {first_dt.strftime('%H:%M')} to {end_dt.strftime('%H:%M')} UTC.")
        
        df_hl = fetch_hl_candles_range(tickers["hl"], first_dt, end_dt, interval)
        df_stock = fetch_yf_candles_range(tickers["stock"], first_dt, end_dt, interval)
        
        if not df_hl.empty:
            if not df_stock.empty:
                df_merged = df_hl.join(df_stock, how="inner").sort_index()
            else:
                df_merged = df_hl.copy()
                for col in ["Stock_O", "Stock_H", "Stock_L", "Stock_C"]:
                    df_merged[col] = None
            
            df_merged = df_merged.reset_index()
            data_list = []
            for _, row in df_merged.iterrows():
                data_list.append({
                    "Time": row["Time"].split(" ")[1], # Just HH:MM
                    "Perp_O": row["Perp_O"],
                    "Perp_H": row["Perp_H"],
                    "Perp_L": row["Perp_L"],
                    "Perp_C": row["Perp_C"],
                    "Stock_O": None if pd.isna(row["Stock_O"]) else row["Stock_O"],
                    "Stock_H": None if pd.isna(row["Stock_H"]) else row["Stock_H"],
                    "Stock_L": None if pd.isna(row["Stock_L"]) else row["Stock_L"],
                    "Stock_C": None if pd.isna(row["Stock_C"]) else row["Stock_C"]
                })
            
            hourly_comparisons[company] = {
                "listing_date": LISTING_DATES[company],
                "first_traded_hour": first_dt.strftime("%Y-%m-%d %H:%M UTC"),
                "ticker_hl": tickers["hl"],
                "ticker_stock": tickers["stock"],
                "granularity": interval,
                "hourly_data": data_list
            }
            print(f"Merged {len(data_list)} candles ({interval}) for {company}")
        else:
            print(f"No perp candles found for {company}")

    with open("listing_day_hourly.json", "w") as f:
        json.dump(hourly_comparisons, f, indent=2)
    print("Successfully wrote listing day hourly comparisons to listing_day_hourly.json")

if __name__ == "__main__":
    main()
