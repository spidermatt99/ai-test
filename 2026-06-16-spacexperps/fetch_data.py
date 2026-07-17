import json
import urllib.request
import time
from datetime import datetime, date

# IPO Dates (public listings)
IPO_DATES = {
    "Cerebras": "2026-05-14",
    "SpaceX": "2026-06-12",
    "Quantinuum": "2026-06-04"
}

TICKERS = {
    "Cerebras": {"hl": "xyz:CBRS", "stock": "CBRS"},
    "SpaceX": {"hl": "xyz:SPCX", "stock": "SPCX"},
    "Quantinuum": {"hl": "xyz:QNT", "stock": "QNT"}
}

def fetch_hl_candles(coin, start_time_ms):
    url = "https://api.hyperliquid.xyz/info"
    headers = {"Content-Type": "application/json"}
    body = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": "1d",
            "startTime": start_time_ms
        }
    }
    req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode('utf-8'))
            return data
    except Exception as e:
        print(f"Error fetching HL candles for {coin}: {e}")
        return []

def fetch_yf_stock(symbol, start_ts):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?period1={start_ts}&period2={int(time.time())}&interval=1d"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode('utf-8'))
            result = data['chart']['result']
            if result:
                timestamps = result[0].get('timestamp', [])
                quote = result[0]['indicators']['quote'][0]
                close = quote.get('close', [])
                # Return dict mapping YYYY-MM-DD to close price
                stock_data = {}
                for ts, c in zip(timestamps, close):
                    if ts is not None and c is not None:
                        dt = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                        stock_data[dt] = round(c, 2)
                return stock_data
    except Exception as e:
        print(f"Error fetching YF stock for {symbol}: {e}")
    return {}

def merge_data(hl_candles, yf_dict, ipo_date_str):
    # Parse HL candles
    merged = []
    for candle in hl_candles:
        # t is ms timestamp
        date_str = datetime.fromtimestamp(candle['t'] / 1000).strftime('%Y-%m-%d')
        perp_close = round(float(candle['c']), 2)
        perp_vol = round(float(candle['v']), 2)
        
        # Determine stock price if listed
        stock_close = None
        if date_str >= ipo_date_str:
            stock_close = yf_dict.get(date_str, None)
            
        merged.append({
            "Date": date_str,
            "Perp_Close": perp_close,
            "Perp_Volume": perp_vol,
            "Stock_Close": stock_close
        })
    # Sort by date
    merged.sort(key=lambda x: x["Date"])
    return merged

def main():
    combined_results = {}
    for company, tickers in TICKERS.items():
        print(f"Processing {company}...")
        ipo_date = IPO_DATES[company]
        
        # Start fetching candles from May 1, 2026 (1774915200000 ms)
        hl_candles = fetch_hl_candles(tickers["hl"], 1774915200000)
        
        # Fetch stock data starting from IPO date - 1 day to be safe (convert to seconds)
        ipo_ts = int(datetime.strptime(ipo_date, "%Y-%m-%d").timestamp())
        stock_dict = fetch_yf_stock(tickers["stock"], ipo_ts - 86400)
        
        merged = merge_data(hl_candles, stock_dict, ipo_date)
        print(f"Merged {len(merged)} rows for {company}")
        
        combined_results[company] = {
            "ticker_hl": tickers["hl"],
            "ticker_stock": tickers["stock"],
            "ipo_date": ipo_date,
            "data": merged
        }
        
    with open("all_prices.json", "w") as f:
        json.dump(combined_results, f, indent=2)
    print("Successfully wrote data to all_prices.json")

if __name__ == "__main__":
    main()
