import requests
import time

url = "https://api.hyperliquid.xyz/info"

def get_total_volume(coin):
    end_time = int(time.time() * 1000)
    total_volume_base = 0.0
    total_volume_quote = 0.0
    last_first_candle_time = None

    while True:
        payload = {
            "type": "candleSnapshot",
            "req": {
                "coin": coin,
                "interval": "1h", # Use 1h for faster pagination
                "startTime": 0,
                "endTime": end_time
            }
        }
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException:
            data = None

        if not data:
            break

        first_candle_time = data[0]['t']
        if last_first_candle_time and first_candle_time == last_first_candle_time:
            break
            
        for candle in data:
            v = float(candle['v'])
            c = float(candle['c'])
            total_volume_base += v
            total_volume_quote += v * c
        
        if len(data) < 4000:
            break
            
        last_first_candle_time = first_candle_time
        end_time = first_candle_time - 1
        time.sleep(0.1)
        
    return total_volume_base, total_volume_quote

for symbol in ["xyz:UNITREE", "xyz:CXMT"]:
    print(f"Fetching data for {symbol}...")
    base_v, quote_v = get_total_volume(symbol)
    print(f"{symbol} Total Volume (Base): {base_v:,.2f}")
    print(f"{symbol} Total Volume (Quote/USD): ${quote_v:,.2f}\n")
