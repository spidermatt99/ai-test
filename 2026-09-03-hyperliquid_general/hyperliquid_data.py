import urllib.request
import json
import time
import datetime
import csv
import sys

def fetch_candles(coin, interval, start_time_ms, end_time_ms):
    url = "https://api.hyperliquid.xyz/info"
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": interval,
            "startTime": start_time_ms,
            "endTime": end_time_ms
        }
    }
    
    req = urllib.request.Request(
        url, 
        data=json.dumps(payload).encode('utf-8'), 
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data
    except Exception as e:
        print(f"Error fetching data for {coin}: {e}")
        return []

def parse_date(date_str):
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
        return int(dt.timestamp() * 1000)
    except ValueError:
        return None

def main():
    print("=== Hyperliquid Historical Data Fetcher ===")
    print("Note: The Hyperliquid API generally only provides the most recent 5,000 candles.\n")
    
    tickers_input = input("Enter ticker(s) separated by commas (e.g., BTC, ETH): ").strip()
    if not tickers_input:
        print("No tickers provided. Exiting.")
        return
        
    tickers = []
    for t in tickers_input.split(','):
        t = t.strip()
        if ':' in t:
            parts = t.split(':', 1)
            tickers.append(f"{parts[0].lower()}:{parts[1].upper()}")
        else:
            tickers.append(t.upper())
    
    start_date_str = input("Enter start date (YYYY-MM-DD) or 'earliest': ").strip()
    if start_date_str.lower() == 'earliest':
        start_time_ms = 0
    else:
        start_time_ms = parse_date(start_date_str)
        if start_time_ms is None:
            print("Invalid start date format. Please use YYYY-MM-DD or 'earliest'. Exiting.")
            return
        
    end_date_str = input("Enter end date (YYYY-MM-DD) or 'latest': ").strip()
    if end_date_str.lower() == 'latest':
        end_time_ms = int(time.time() * 1000)
    else:
        end_time_ms = parse_date(end_date_str)
        if end_time_ms is None:
            print("Invalid end date format. Please use YYYY-MM-DD or 'latest'. Exiting.")
            return
        # Adjust end_time_ms to the end of the day (23:59:59.999) for inclusive date ranges
        end_time_ms += (24 * 60 * 60 * 1000) - 1
        
    interval = input("Enter time interval (e.g., 1m, 5m, 15m, 1h, 4h, 1d): ").strip()
    if not interval:
        interval = "1h"
    
    print("\nSelect data type to output:")
    print("1. Price (Open, High, Low, Close)")
    print("2. Volume")
    print("3. All (Price, Volume, Trades)")
    data_type_choice = input("Enter choice (1/2/3) [default: 3]: ").strip()
    
    show_markdown_input = input("Output as markdown table inline? (y/n) [default: y]: ").strip().lower()
    show_markdown = show_markdown_input != 'n'
    
    save_csv_input = input("Save data to CSV? (y/n) [default: y]: ").strip().lower()
    save_csv = save_csv_input != 'n'
    
    save_chart_input = input("Save a chart of the close price? (requires matplotlib) (y/n) [default: n]: ").strip().lower()
    save_chart = save_chart_input == 'y'
    
    columns = ["Time"]
    keys = ["t"]
    if data_type_choice == '1':
        columns.extend(["Open", "High", "Low", "Close"])
        keys.extend(["o", "h", "l", "c"])
    elif data_type_choice == '2':
        columns.extend(["Volume"])
        keys.extend(["v"])
    else:
        columns.extend(["Open", "High", "Low", "Close", "Volume", "Trades"])
        keys.extend(["o", "h", "l", "c", "v", "n"])
        
    for ticker in tickers:
        print(f"\nFetching data for {ticker}...")
        data = fetch_candles(ticker, interval, start_time_ms, end_time_ms)
        
        if not data:
            print(f"No data returned for {ticker}. The timeframe might be too old or the ticker is invalid.")
            continue
            
        print(f"Retrieved {len(data)} candles for {ticker}.")
            
        rows = []
        for candle in data:
            row = []
            for key in keys:
                if key == 't':
                    # Format timestamp as readable date
                    dt = datetime.datetime.fromtimestamp(candle[key] / 1000, datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                    row.append(dt)
                else:
                    row.append(str(candle.get(key, '')))
            rows.append(row)
            
        if show_markdown:
            print(f"\n### {ticker} Data ({start_date_str} to {end_date_str})")
            header = "| " + " | ".join(columns) + " |"
            separator = "|" + "|".join(["---" for _ in columns]) + "|"
            print(header)
            print(separator)
            for row in rows:
                print("| " + " | ".join(row) + " |")
                
        if save_csv:
            filename = f"{ticker}_data_{start_date_str}_to_{end_date_str}_{interval}.csv".replace(':', '_')
            try:
                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(columns)
                    writer.writerows(rows)
                print(f"\nSaved {ticker} data to {filename}")
            except Exception as e:
                print(f"Failed to save CSV for {ticker}: {e}")
                
        if save_chart:
            if "Close" not in columns:
                print(f"\nCannot save chart for {ticker} because 'Close' price was not selected in data type.")
            else:
                try:
                    import matplotlib.pyplot as plt
                    
                    times = []
                    closes = []
                    time_idx = columns.index("Time")
                    close_idx = columns.index("Close")
                    
                    for row in rows:
                        times.append(datetime.datetime.strptime(row[time_idx], '%Y-%m-%d %H:%M:%S'))
                        closes.append(float(row[close_idx]))
                        
                    plt.figure(figsize=(10, 6))
                    plt.plot(times, closes, label=f"{ticker} Close Price", color='blue')
                    plt.title(f"{ticker} Close Price ({start_date_str} to {end_date_str})")
                    plt.xlabel("Time (UTC)")
                    plt.ylabel("Price")
                    plt.grid(True)
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    
                    chart_filename = f"{ticker}_chart_{start_date_str}_to_{end_date_str}_{interval}.png".replace(':', '_')
                    plt.savefig(chart_filename)
                    plt.close()
                    print(f"Saved chart to {chart_filename}")
                except ImportError:
                    print(f"\nCould not save chart for {ticker}: 'matplotlib' is not installed. Please install it using 'pip install matplotlib'.")
                except Exception as e:
                    print(f"\nFailed to save chart for {ticker}: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
