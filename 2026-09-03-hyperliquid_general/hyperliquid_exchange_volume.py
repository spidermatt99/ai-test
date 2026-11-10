"""
Hyperliquid Platform-Wide Exchange Volume Aggregator

Calculates total historical trading volume across all markets (Perpetuals and/or Spot)
on Hyperliquid for any specified time window.
"""

import urllib.request
import json
import time
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import csv
import sys
import os

HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"

def query_info(payload: dict) -> dict:
    """Helper to query Hyperliquid /info POST endpoint."""
    req = urllib.request.Request(
        HYPERLIQUID_INFO_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "HyperliquidVolumeAggregator/1.0"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get_perp_universe() -> list:
    """Fetches list of all active perpetual symbols."""
    data = query_info({"type": "meta"})
    return [u["name"] for u in data.get("universe", [])]

def get_spot_universe() -> list:
    """Fetches list of all active spot symbols."""
    data = query_info({"type": "spotMeta"})
    universe = []
    tokens = data.get("tokens", [])
    token_map = {t["index"]: t["name"] for t in tokens}
    for market in data.get("universe", []):
        base_name = market.get("name")
        if base_name:
            universe.append(f"@{market['index']}")  # spot markets can be queried by @index or name
        else:
            tok = market.get("tokens", [None, None])
            if tok[0] is not None and tok[1] is not None:
                universe.append(f"{token_map.get(tok[0], 'UNK')}/{token_map.get(tok[1], 'USDC')}")
    return universe

def fetch_candles_for_coin(coin: str, start_ms: int, end_ms: int, interval: str = "1d", max_retries: int = 3):
    """Fetches candles for a specific coin with retry support."""
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": interval,
            "startTime": start_ms,
            "endTime": end_ms
        }
    }
    for attempt in range(max_retries):
        try:
            candles = query_info(payload)
            if isinstance(candles, list):
                return coin, candles
            return coin, []
        except Exception as e:
            if attempt == max_retries - 1:
                return coin, []
            time.sleep(0.3 * (2 ** attempt))
    return coin, []

def parse_date_to_ms(date_str: str, is_end_of_day: bool = False) -> int:
    """Parses YYYY-MM-DD into UTC epoch milliseconds."""
    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
    ms = int(dt.timestamp() * 1000)
    if is_end_of_day:
        ms += (24 * 60 * 60 * 1000) - 1
    return ms

def aggregate_exchange_volume(start_date: str, end_date: str, include_perps: bool = True, include_spot: bool = False, max_workers: int = 10, interval: str = "1d"):
    """
    Fetches and aggregates volume across all markets over the given date range.
    """
    start_ms = parse_date_to_ms(start_date, is_end_of_day=False)
    end_ms = parse_date_to_ms(end_date, is_end_of_day=True)

    coins_to_fetch = []
    if include_perps:
        perp_coins = get_perp_universe()
        coins_to_fetch.extend(perp_coins)
        print(f"Loaded {len(perp_coins)} Perpetual markets.")
    
    if include_spot:
        spot_coins = get_spot_universe()
        coins_to_fetch.extend(spot_coins)
        print(f"Loaded {len(spot_coins)} Spot markets.")

    total_coins = len(coins_to_fetch)
    print(f"Fetching {interval} historical candles for {total_coins} markets ({start_date} to {end_date})...")

    t0 = time.time()
    daily_volume = defaultdict(float)
    coin_volume = defaultdict(float)
    coin_trades = defaultdict(int)
    total_trades = 0
    completed_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_coin = {
            executor.submit(fetch_candles_for_coin, coin, start_ms, end_ms, interval): coin
            for coin in coins_to_fetch
        }

        for future in as_completed(future_to_coin):
            completed_count += 1
            if completed_count % 30 == 0 or completed_count == total_coins:
                print(f"  Progress: {completed_count}/{total_coins} markets processed ({completed_count/total_coins*100:.1f}%)")

            coin, candles = future.result()
            for c in candles:
                candle_time = int(c.get("t", 0))
                if start_ms <= candle_time <= end_ms:
                    # Notional USD volume = volume * close price
                    vol_base = float(c.get("v", 0.0))
                    close_px = float(c.get("c", 0.0))
                    notional_usd = vol_base * close_px
                    trades = int(c.get("n", 0))

                    date_label = datetime.datetime.fromtimestamp(candle_time / 1000, datetime.timezone.utc).strftime("%Y-%m-%d")
                    daily_volume[date_label] += notional_usd
                    coin_volume[coin] += notional_usd
                    coin_trades[coin] += trades
                    total_trades += trades

    t1 = time.time()
    grand_total_usd = sum(daily_volume.values())

    return {
        "start_date": start_date,
        "end_date": end_date,
        "elapsed_seconds": t1 - t0,
        "markets_queried": total_coins,
        "grand_total_usd": grand_total_usd,
        "total_trades": total_trades,
        "daily_volume": dict(sorted(daily_volume.items())),
        "coin_volume": sorted(coin_volume.items(), key=lambda x: x[1], reverse=True),
        "coin_trades": coin_trades
    }

def print_report(res: dict, top_n: int = 10):
    print("\n" + "=" * 65)
    print(f"HYPERLIQUID PLATFORM VOLUME REPORT")
    print(f"Period: {res['start_date']} to {res['end_date']} (UTC)")
    print(f"Markets Queried: {res['markets_queried']} | Query Time: {res['elapsed_seconds']:.2f}s")
    print("=" * 65)
    print(f"GRAND TOTAL VOLUME:  ${res['grand_total_usd']:,.2f} USD")
    print(f"TOTAL TRADES COUNT:  {res['total_trades']:,}")
    print("-" * 65)
    
    print("\nDAILY VOLUME BREAKDOWN:")
    print(f"{'Date (UTC)':<15} {'Volume (USD)':<22} {'Daily Share':<12}")
    print("-" * 50)
    for date, vol in res["daily_volume"].items():
        share = (vol / res["grand_total_usd"] * 100) if res["grand_total_usd"] > 0 else 0
        print(f"{date:<15} ${vol:>18,.2f}   {share:>6.2f}%")
        
    print(f"\nTOP {top_n} MARKETS BY VOLUME:")
    print(f"{'Rank':<6} {'Market':<10} {'Volume (USD)':<22} {'Market Share':<14} {'Trades':<12}")
    print("-" * 65)
    for i, (coin, vol) in enumerate(res["coin_volume"][:top_n], start=1):
        share = (vol / res["grand_total_usd"] * 100) if res["grand_total_usd"] > 0 else 0
        trades = res["coin_trades"].get(coin, 0)
        print(f"{i:<6} {coin:<10} ${vol:>18,.2f}   {share:>8.2f}%   {trades:>10,}")
    print("=" * 65)

def save_to_csv(res: dict, filename: str):
    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["=== HYPERLIQUID PLATFORM VOLUME SUMMARY ==="])
        writer.writerow(["Start Date", res["start_date"]])
        writer.writerow(["End Date", res["end_date"]])
        writer.writerow(["Grand Total USD", f"{res['grand_total_usd']:.2f}"])
        writer.writerow(["Total Trades", res["total_trades"]])
        writer.writerow([])
        writer.writerow(["Date (UTC)", "Daily Volume (USD)"])
        for date, vol in res["daily_volume"].items():
            writer.writerow([date, f"{vol:.2f}"])
        writer.writerow([])
        writer.writerow(["Rank", "Market", "Volume (USD)", "Market Share (%)", "Trade Count"])
        for i, (coin, vol) in enumerate(res["coin_volume"], start=1):
            share = (vol / res["grand_total_usd"] * 100) if res["grand_total_usd"] > 0 else 0
            trades = res["coin_trades"].get(coin, 0)
            writer.writerow([i, coin, f"{vol:.2f}", f"{share:.2f}", trades])
    print(f"Results successfully saved to CSV: {filename}")

def main():
    print("=== Hyperliquid Platform-Wide Volume Aggregator ===\n")
    
    # Defaults to the last 7 complete days if skipped
    today = datetime.datetime.now(datetime.timezone.utc).date()
    default_end = (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    default_start = (today - datetime.timedelta(days=7)).strftime("%Y-%m-%d")

    start_date = input(f"Enter start date (YYYY-MM-DD) [default: {default_start}]: ").strip() or default_start
    end_date = input(f"Enter end date (YYYY-MM-DD) [default: {default_end}]: ").strip() or default_end

    print("\nSelect market scope:")
    print("1. Perpetuals Only (recommended, ~98% of exchange volume)")
    print("2. Spot Only")
    print("3. Both (Perpetuals + Spot)")
    choice = input("Enter choice (1/2/3) [default: 1]: ").strip() or "1"
    
    include_perps = choice in ("1", "3")
    include_spot = choice in ("2", "3")

    res = aggregate_exchange_volume(start_date, end_date, include_perps=include_perps, include_spot=include_spot)
    print_report(res)

    save_csv_input = input("\nSave results to CSV? (y/n) [default: y]: ").strip().lower()
    if save_csv_input != "n":
        filename = f"hyperliquid_platform_volume_{start_date}_to_{end_date}.csv"
        save_to_csv(res, filename)

if __name__ == "__main__":
    main()
