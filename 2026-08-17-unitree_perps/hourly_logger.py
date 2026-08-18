import requests
import csv
import time
import os
from datetime import datetime, timezone, timedelta

url = "https://api.hyperliquid.xyz/info"
coin = "xyz:UNITREE"
interval = "1h" # Hourly candles
safe_coin_name = coin.replace(":", "_")
csv_filename = f"{safe_coin_name}_hourly_data.csv"

sgt = timezone(timedelta(hours=8))
headers = ["Time (SGT)", "Open", "High", "Low", "Close", "Volume"]

def fetch_candles(start_time, end_time):
    """Fetch candles between start_time and end_time (in milliseconds)."""
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": interval,
            "startTime": start_time,
            "endTime": end_time
        }
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def format_candle(candle):
    """Format candle data for CSV."""
    ts = datetime.fromtimestamp(candle['t'] / 1000, tz=sgt).strftime('%Y-%m-%d %H:%M:%S')
    return [ts, candle['o'], candle['h'], candle['l'], candle['c'], candle['v']]

def run_hourly_logger():
    # 1. Initialize or find the last fetched timestamp
    last_timestamp = 0
    file_exists = os.path.isfile(csv_filename)
    
    if file_exists:
        print(f"Found existing {csv_filename}, checking for new hourly data...")
        # A simple way to get the last timestamp is to just paginate forward from 0 
        # or we could parse the CSV. For robustness, let's just fetch from the last known time.
        # But we'll just fetch from 0 and append missing data.
    else:
        print(f"Creating new file {csv_filename} and downloading all historical hourly data...")
        with open(csv_filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)

    # Fetch all data from `last_timestamp` to now
    print(f"Fetching historical {interval} candles...")
    now = int(time.time() * 1000)
    all_candles = []
    end_time = now
    
    # Paginate backwards to get all history (or missing history)
    last_first_candle_time = None
    while True:
        data = fetch_candles(0, end_time)
        if not data:
            break
        
        first_candle_time = data[0]['t']
        if last_first_candle_time and first_candle_time == last_first_candle_time:
            break
            
        all_candles = data + all_candles
        
        if len(data) < 4000:
            break
            
        last_first_candle_time = first_candle_time
        end_time = first_candle_time - 1
        time.sleep(0.1)

    # Filter out candles we already have (if any) and write to CSV
    # If the file didn't exist, we just write them all.
    with open(csv_filename, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            for c in all_candles:
                writer.writerow(format_candle(c))
            print(f"Saved {len(all_candles)} historical hourly candles.")
        else:
            # We're just appending. To avoid duplicates efficiently without parsing the whole CSV,
            # in a real robust system we'd check the last line. 
            # For simplicity in this script, we'll rewrite the file with all unique candles.
            pass

    if file_exists:
        # Rewrite the whole file to ensure it's perfectly synced and sorted
        with open(csv_filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for c in all_candles:
                writer.writerow(format_candle(c))
        print(f"Updated CSV with latest data. Total {len(all_candles)} candles.")

    # 2. Continuous Hourly Logging Loop
    print("\nStarting continuous hourly logger. Press Ctrl+C to stop.")
    while True:
        # Calculate time until the next hour mark
        now_dt = datetime.now(timezone.utc)
        next_hour = (now_dt + timedelta(hours=1)).replace(minute=1, second=0, microsecond=0)
        sleep_seconds = (next_hour - now_dt).total_seconds()
        
        print(f"Waiting {sleep_seconds / 60:.1f} minutes until the next hourly update...")
        time.sleep(sleep_seconds)
        
        # Wake up and fetch the latest hour
        print(f"[{datetime.now(sgt).strftime('%H:%M:%S')}] Fetching latest hourly candle...")
        now_ms = int(time.time() * 1000)
        start_ms = now_ms - (2 * 60 * 60 * 1000) # Fetch last 2 hours to be safe
        
        latest_data = fetch_candles(start_ms, now_ms)
        if latest_data:
            latest_candle = latest_data[-2] # -1 is the currently open/incomplete candle, -2 is the last closed hour
            
            with open(csv_filename, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(format_candle(latest_candle))
                
            print(f"Appended candle for {format_candle(latest_candle)[0]}")

if __name__ == "__main__":
    run_hourly_logger()
