import requests
import csv
import time
from datetime import datetime, timezone, timedelta

url = "https://api.hyperliquid.xyz/info"
coin = "xyz:UNITREE"
interval = "30m" # 30-minute intervals

# Safely name the file for Windows
safe_coin_name = coin.replace(":", "_")
csv_filename = f"{safe_coin_name}_30m_data.csv"

# Set timezone to Singapore Time (GMT+8)
sgt = timezone(timedelta(hours=8))
headers = ["Time (SGT)", "Open", "High", "Low", "Close", "Volume"]

print(f"Fetching {interval} data for {coin} going back to genesis...")

end_time = int(time.time() * 1000)
all_candles = []
last_first_candle_time = None

while True:
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": interval,
            "startTime": 0,
            "endTime": end_time
        }
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        data = None
        break

    if not data:
        break

    first_candle_time = data[0]['t']
    
    if last_first_candle_time and first_candle_time == last_first_candle_time:
        break
        
    all_candles = data + all_candles
    
    # If the API returns fewer than 4000 candles, we've likely hit genesis
    if len(data) < 4000:
        break
        
    last_first_candle_time = first_candle_time
    end_time = first_candle_time - 1
    time.sleep(0.1) # Avoid rate limits

if not all_candles:
    print("No data was returned from the API.")
else:
    print(f"Successfully fetched {len(all_candles)} candles. Writing to {csv_filename}...")
    with open(csv_filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        for candle in all_candles:
            # Convert timestamp to GMT+8
            ts = datetime.fromtimestamp(candle['t'] / 1000, tz=sgt).strftime('%Y-%m-%d %H:%M:%S')
            writer.writerow([ts, candle['o'], candle['h'], candle['l'], candle['c'], candle['v']])
            
    print("Done!")
