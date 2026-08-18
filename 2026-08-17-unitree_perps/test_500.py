import requests
import time

# Endpoint for Hyperliquid Info API
url = "https://api.hyperliquid.xyz/info"

def test_hyperliquid_500_error(coin: str):
    """
    Tests the candleSnapshot endpoint for a given coin to see if it causes a 500 Server Error.
    """
    now = int(time.time() * 1000)
    
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": "5m",
            "startTime": 0, # Or any valid timestamp
            "endTime": now
        }
    }
    
    print(f"--- Testing Coin: {coin} ---")
    
    # 1. First, let's verify if the coin actually exists in the active universe
    meta_response = requests.post(url, json={"type": "meta"})
    if meta_response.status_code == 200:
        universe = [asset['name'] for asset in meta_response.json()['universe']]
        exists = coin in universe
        print(f"Is '{coin}' in the active trading universe? {exists}")
    else:
        print("Failed to fetch meta universe.")

    # 2. Now try fetching the candles for it
    print(f"Requesting candles for {coin}...")
    res = requests.post(url, json=payload)
    
    print(f"Response Status Code: {res.status_code}")
    if res.status_code == 500:
        print("Result: 500 Internal Server Error triggered!")
        print("Cause: Hyperliquid's API returns a 500 error (instead of a 404 or empty list) when you request candlestick data for a coin symbol that does not exist on their platform.")
    elif res.status_code == 200:
        print(f"Result: 200 OK. Successfully fetched data.")
    
    print("-" * 40 + "\n")

if __name__ == "__main__":
    # Test a valid coin (should return 200 OK)
    test_hyperliquid_500_error("BTC")
    
    # Test the requested coin (this triggers the 500 error because it doesn't exist on the exchange)
    test_hyperliquid_500_error("UNITREE")
    
    # Test absolute gibberish to prove it's the non-existent coin name causing the crash
    test_hyperliquid_500_error("INVALID_COIN_123")
