import requests
from datetime import datetime
import time

def get_historical_price(coin_id, date_str):
    """
    Fetches the price of a coin on a specific date (dd-mm-yyyy).
    Uses CoinGecko's /history endpoint.
    """
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/history"
    params = {"date": date_str, "localization": "false"}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('market_data', {}).get('current_price', {}).get('usd')
    except Exception as e:
        print(f"Error fetching historical data for {coin_id}: {e}")
        return None

def get_current_data(coin_ids):
    """
    Fetches current market data for specified cryptocurrencies.
    """
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": ",".join(coin_ids),
        "order": "market_cap_desc",
        "price_change_percentage": "24h"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching current data: {e}")
        return []

def run_analysis():
    target_coins = ["zcash", "monero", "bitcoin", "ethereum"]
    start_date = "01-01-2026" # YTD start for the requested date of June 2026
    
    print(f"--- Crypto YTD Performance Analysis (Start Date: {start_date}) ---")
    print(f"{'Name':<12} | {'Jan 1 Price':<12} | {'Current Price':<14} | {'YTD Change %':<12} | {'24h %'}")
    print("-" * 75)
    
    current_data = {coin['id']: coin for coin in get_current_data(target_coins)}
    
    for coin_id in target_coins:
        coin_info = current_data.get(coin_id)
        if not coin_info:
            continue
            
        current_price = coin_info['current_price']
        p24h = coin_info.get('price_change_percentage_24h', 0)
        
        # Rate limit friendly sleep
        time.sleep(1.5) 
        jan_price = get_historical_price(coin_id, start_date)
        
        if jan_price and current_price:
            ytd_change = ((current_price - jan_price) / jan_price) * 100
            name = coin_info['name']
            print(f"{name:<12} | ${jan_price:>10,.2f} | ${current_price:>12,.2f} | {ytd_change:>11.2f}% | {p24h:>6.2f}%")
        else:
            print(f"{coin_id:<12} | Data Missing")

if __name__ == "__main__":
    run_analysis()
