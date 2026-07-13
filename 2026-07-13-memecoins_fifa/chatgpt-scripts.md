Done — I generated the Python script here:

```python
#!/usr/bin/env python3
"""
soccer_memecoin_data_compiler.py

Compile historical price and trading-volume data for World Cup / soccer / football
meme-style crypto tokens.

Outputs:
  - daily_history.csv: normalized daily price/volume rows
  - token_summary.csv: since-first-available metrics by token
  - fetch_log.csv: source, status, and errors per token
  - plots/*.png: optional price/volume charts

Data sources used, in priority order:
  1) CoinGecko coin market_chart API: best for listed tokens; gives price,
     market cap, and 24h volume from earliest CoinGecko coverage.
  2) CoinMarketCap Pro API, optional: use CMC_API_KEY for tokens that are on
     CMC but not CoinGecko. Historical coverage/plan access varies.
  3) GeckoTerminal public API: useful for DEX-only tokens and recent Solana or
     BSC launches. OHLCV historical coverage can be limited, so for older 2022
     tokens this is not always true launch-to-date history.

Important caveats:
  - "Since launch" means since the earliest available historical data returned
    by the selected data source. For some sources that is the first listing date,
    not necessarily the on-chain deployment timestamp.
  - Many meme tokens reuse the same symbol/name. Prefer exact contract or pool
    addresses in TOKENS or in a custom --tokens-file to avoid false matches.
  - This is research tooling only, not financial advice.

Install:
  python -m pip install requests pandas numpy matplotlib

Examples:
  python soccer_memecoin_data_compiler.py --out-dir out
  python soccer_memecoin_data_compiler.py --include-adjacent --include-fan-tokens --plot
  CMC_API_KEY=... python soccer_memecoin_data_compiler.py --use-cmc
  python soccer_memecoin_data_compiler.py --discover-dex --dex-discovery-limit 5

Custom token file:
  JSON list or CSV with any of these columns:
    name,symbol,category,coingecko_id,cmc_slug,cmc_id,gt_network,gt_pool,contract,notes
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests

CG_PUBLIC_BASE = "https://api.coingecko.com/api/v3"
CG_PRO_BASE = "https://pro-api.coingecko.com/api/v3"
CMC_BASE = "https://pro-api.coinmarketcap.com"
GT_BASE = "https://api.geckoterminal.com/api/v2"
DEX_BASE = "https://api.dexscreener.com/latest/dex"

USER_AGENT = "soccer-memecoin-data-compiler/1.0 (+research script)"

# Seed universe: direct World Cup/soccer meme-style tokens plus soccer-adjacent
# GameFi/community tokens. Official club/national fan tokens are deliberately
# separate because they are generally not memecoins.
TOKENS: List[Dict[str, Any]] = [
    # Direct World Cup / FIFA / football meme or community tokens
    {"name": "Football World Community", "symbol": "FWC", "category": "meme_core", "coingecko_id": "football-world-community", "cmc_slug": "qatar-2022-token", "notes": "Formerly/also surfaced as Qatar 2022 Token on some data sites."},
    {"name": "World Cup Token", "symbol": "WCT", "category": "meme_core", "cmc_slug": "world-cup-token"},
    {"name": "FIFA World Cup Fans", "symbol": "FIFA", "category": "meme_core", "cmc_slug": "fifa-world-cup-fans"},
    {"name": "FIFA", "symbol": "FIFA", "category": "meme_core", "cmc_slug": "fifa"},
    {"name": "WORLD CUP INU", "symbol": "WCI", "category": "meme_core", "cmc_slug": "world-cup-inu", "contract": "0xc5a9bc46a7dbe1c6de493e84a18f02e70e2c5a32", "notes": "Ethereum token contract from Etherscan/CMC."},
    {"name": "FIFA-Laeeb", "symbol": "LAEEB", "category": "meme_core", "cmc_slug": "laeeb-"},
    {"name": "Laeeb Inu", "symbol": "LAEEB", "category": "meme_core", "cmc_slug": "laeebinu"},
    {"name": "Fifa Inu", "symbol": "FINU", "category": "meme_core", "cmc_slug": "fifa-inu"},
    {"name": "Football INU", "symbol": "FOOTBALL", "category": "meme_core", "cmc_slug": "football-inu"},
    {"name": "SoccerInu", "symbol": "SOCCER", "category": "meme_core", "cmc_slug": "soccerinu"},
    {"name": "World Cup Willie", "symbol": "WILLIE", "category": "meme_core", "cmc_slug": "world-cup-willie"},
    {"name": "Shiba World Cup", "symbol": "SWC", "category": "meme_core", "cmc_slug": "shiba-world-cup"},
    {"name": "FIFADOGE", "symbol": "FDOGE", "category": "meme_core", "cmc_slug": "fifadoge"},
    {"name": "WORLD CUP DOGE", "symbol": "WCDOGE", "category": "meme_core", "cmc_slug": "world-cup-doge"},
    {"name": "World Cup Pot", "symbol": "WCP", "category": "meme_core", "cmc_slug": "world-cup-pot"},
    {"name": "WORLD CUP COIN", "symbol": "WORLDCUP", "category": "meme_core", "cmc_slug": "worldcupcoin-online", "notes": "CMC slug worldcupcoin-online."},
    {"name": "WORLD CUP COIN", "symbol": "WORLDCUP", "category": "meme_core", "cmc_slug": "world-cup-coin", "notes": "CMC slug world-cup-coin / WORLDCUP_X."},
    {"name": "WORLD CUP 2026", "symbol": "WORLDCUP26", "category": "meme_core", "cmc_slug": "world-cup-2026"},
    {"name": "FIFA WORLD CUP", "symbol": "FWC", "category": "meme_core", "cmc_slug": "fifa-world-cup-worldcupmoon-space"},
    {"name": "World Cup Coin", "symbol": "WORLDCUP", "category": "meme_core", "gt_network": "solana", "gt_pool": "ETMhxtENfkMK85TAcveEbZdBv9htziWzDSddmShRP2wB", "contract": "33eum82LaAhtv5YkUq1BdwEviSErH5CnFxqVNLT5pump", "notes": "Solana 2026 World Cup-themed memecoin; verify pool before use."},
    {"name": "WORLD CUP 2026", "symbol": "W26", "category": "meme_core", "gt_network": "solana", "gt_pool": "Dw6DJuPog4piqa8fWz4e7avJ217QPJH4Wzg8UmiDiACV", "notes": "One W26/SOL pool found on GeckoTerminal; duplicate W26 tokens exist."},
    {"name": "2026 World Cup Mascots", "symbol": "MASCOTS", "category": "meme_core", "gt_network": "solana", "gt_pool": "D2g8AAUqBzLpX7mxp6yg8v3Psau6hVc2dRLqjuaQXZyP", "contract": "8GxLxKA8tf3h8JUkXFfP4dNyn6D2vvwyGif5wanRpump"},
    {"name": "WorldCup26Goals", "symbol": "WCGOALS", "category": "meme_core", "gt_network": "solana", "gt_pool": "7CdzGHZNL9Fp9h4L69bA7K9cpGkB2ThGX57CFRmM725d"},
    {"name": "Messi Coin", "symbol": "MESSI", "category": "player_meme", "cmc_slug": "messi-coin-eth"},
    {"name": "Cristiano Ronaldo Meme", "symbol": "CR7", "category": "player_meme", "cmc_slug": "cristiano-ronaldo-meme"},
    {"name": "WATER Coin", "symbol": "WATER", "category": "player_promoted_not_soccer_brand", "coingecko_id": "water-coin", "cmc_slug": "water", "notes": "Not soccer-branded, but footballer-promoted; include/exclude depending on research scope."},

    # Soccer / World Cup adjacent GameFi, utility, betting, or community tokens.
    # Include with --include-adjacent.
    {"name": "FIFA Champs", "symbol": "CHAMPS", "category": "sports_gamefi_or_utility", "cmc_slug": "fifa-champs"},
    {"name": "World Football", "symbol": "WOFO", "category": "sports_gamefi_or_utility", "cmc_slug": "world-football"},
    {"name": "FiFaSport", "symbol": "FFS", "category": "sports_gamefi_or_utility", "cmc_slug": "fifasport"},
    {"name": "World Bet Club", "symbol": "WBT", "category": "sports_gamefi_or_utility", "cmc_slug": "world-bet-club"},
    {"name": "Soccer Galaxy", "symbol": "SOG", "category": "sports_gamefi_or_utility", "cmc_slug": "soccer-galaxy"},
    {"name": "Football Decentralized", "symbol": "FBD", "category": "sports_gamefi_or_utility", "cmc_slug": "football-decentralized"},
    {"name": "Futuball", "symbol": "FB", "category": "sports_gamefi_or_utility", "cmc_slug": "futuball"},
    {"name": "Football Stars", "symbol": "FootballStars", "category": "sports_gamefi_or_utility", "cmc_slug": "football-stars"},
    {"name": "Minifootball", "symbol": "MINIFOOTBALL", "category": "sports_gamefi_or_utility", "cmc_slug": "minifootball"},
    {"name": "SoccerHub", "symbol": "SCH", "category": "sports_gamefi_or_utility", "cmc_slug": "soccerhub"},
    {"name": "FootBallGo", "symbol": "FGSPORT", "category": "sports_gamefi_or_utility", "cmc_slug": "footballgo"},
    {"name": "Soccer Infinity", "symbol": "SOCIN", "category": "sports_gamefi_or_utility", "cmc_slug": "soccer-infinity"},
    {"name": "FootballCoin", "symbol": "FBC", "category": "sports_gamefi_or_utility", "cmc_slug": "footballcoin-fbc"},
    {"name": "Football Coin", "symbol": "XFC", "category": "sports_gamefi_or_utility", "coingecko_id": "football-coin", "cmc_slug": "footballcoin"},
    {"name": "Football Battle", "symbol": "FBL", "category": "sports_gamefi_or_utility", "cmc_slug": "football-battle"},
    {"name": "Pitch World Cup", "symbol": "PITCH", "category": "sports_gamefi_or_utility", "cmc_slug": "pitch-world-cup"},
]

FAN_TOKENS: List[Dict[str, Any]] = [
    # Official/club/national fan tokens are not memecoins, but can be included
    # for broader soccer-token benchmarking with --include-fan-tokens.
    {"name": "Atletico De Madrid Fan Token", "symbol": "ATM", "category": "fan_token", "coingecko_id": "atletico-madrid", "cmc_slug": "atletico-de-madrid-fan-token"},
    {"name": "Paris Saint-Germain Fan Token", "symbol": "PSG", "category": "fan_token", "coingecko_id": "paris-saint-germain-fan-token", "cmc_slug": "paris-saint-germain-fan-token"},
    {"name": "AS Roma Fan Token", "symbol": "ASR", "category": "fan_token", "coingecko_id": "as-roma-fan-token", "cmc_slug": "as-roma-fan-token"},
    {"name": "Galatasaray Fan Token", "symbol": "GAL", "category": "fan_token", "coingecko_id": "galatasaray-fan-token", "cmc_slug": "galatasaray-fan-token"},
    {"name": "FC Barcelona Fan Token", "symbol": "BAR", "category": "fan_token", "coingecko_id": "fc-barcelona-fan-token", "cmc_slug": "fc-barcelona-fan-token"},
    {"name": "Manchester City Fan Token", "symbol": "CITY", "category": "fan_token", "coingecko_id": "manchester-city-fan-token", "cmc_slug": "manchester-city-fan-token"},
    {"name": "Juventus Fan Token", "symbol": "JUV", "category": "fan_token", "coingecko_id": "juventus-fan-token", "cmc_slug": "juventus-fan-token"},
    {"name": "AC Milan Fan Token", "symbol": "ACM", "category": "fan_token", "coingecko_id": "ac-milan-fan-token", "cmc_slug": "ac-milan-fan-token"},
    {"name": "Argentine Football Association Fan Token", "symbol": "ARG", "category": "fan_token", "coingecko_id": "argentine-football-association-fan-token", "cmc_slug": "argentine-football-association-fan-token"},
    {"name": "Portugal National Team Fan Token", "symbol": "POR", "category": "fan_token", "coingecko_id": "portugal-national-team-fan-token", "cmc_slug": "portugal-national-team-fan-token"},
    {"name": "Santos FC Fan Token", "symbol": "SANTOS", "category": "fan_token", "coingecko_id": "santos-fc-fan-token", "cmc_slug": "santos-fc-fan-token"},
    {"name": "Lazio Fan Token", "symbol": "LAZIO", "category": "fan_token", "coingecko_id": "lazio-fan-token", "cmc_slug": "lazio-fan-token"},
    {"name": "FC Porto", "symbol": "PORTO", "category": "fan_token", "coingecko_id": "fc-porto", "cmc_slug": "fc-porto"},
]

DISCOVERY_TERMS = [
    "world cup",
    "world cup 2026",
    "fifa world cup",
    "fifa",
    "soccer inu",
    "football inu",
    "laeeb",
    "world cup mascots",
    "messi coin",
    "ronaldo meme",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(text).lower())


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


class APIError(RuntimeError):
    pass


class APIClient:
    def __init__(self, sleep_seconds: float = 1.2, retries: int = 3, timeout: int = 30):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
        self.sleep_seconds = sleep_seconds
        self.retries = retries
        self.timeout = timeout

    def get_json(self, url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        last_err: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            try:
                response = self.session.get(url, params=params, headers=headers, timeout=self.timeout)
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    pause = float(retry_after) if retry_after and retry_after.isdigit() else self.sleep_seconds * attempt * 3
                    time.sleep(pause)
                    continue
                if response.status_code >= 400:
                    raise APIError(f"HTTP {response.status_code}: {response.text[:500]}")
                try:
                    return response.json()
                except ValueError as exc:
                    raise APIError(f"Invalid JSON: {response.text[:500]}") from exc
            except Exception as exc:  # requests exceptions or APIError
                last_err = exc
                if attempt < self.retries:
                    time.sleep(self.sleep_seconds * attempt)
                else:
                    break
        raise APIError(str(last_err))


def coingecko_headers(api_key: Optional[str], pro: bool) -> Dict[str, str]:
    if not api_key:
        return {}
    return {"x-cg-pro-api-key" if pro else "x-cg-demo-api-key": api_key}


def coingecko_base(pro: bool) -> str:
    return CG_PRO_BASE if pro else CG_PUBLIC_BASE


def load_coingecko_coin_list(client: APIClient, cache_dir: Path, api_key: Optional[str], pro: bool, refresh: bool = False) -> List[Dict[str, Any]]:
    ensure_dir(cache_dir)
    cache_file = cache_dir / "coingecko_coins_list.json"
    if cache_file.exists() and not refresh:
        with cache_file.open("r", encoding="utf-8") as f:
            return json.load(f)
    url = f"{coingecko_base(pro)}/coins/list"
    data = client.get_json(url, params={"include_platform": "true"}, headers=coingecko_headers(api_key, pro))
    with cache_file.open("w", encoding="utf-8") as f:
        json.dump(data, f)
    return data


def infer_coingecko_id(token: Dict[str, Any], coins_list: List[Dict[str, Any]]) -> Optional[str]:
    if token.get("coingecko_id"):
        return str(token["coingecko_id"])

    name_key = normalize_key(token.get("name", ""))
    symbol_key = normalize_key(token.get("symbol", ""))
    if not name_key and not symbol_key:
        return None

    exact_name = []
    exact_symbol = []
    for c in coins_list:
        c_name_key = normalize_key(c.get("name", ""))
        c_symbol_key = normalize_key(c.get("symbol", ""))
        if name_key and c_name_key == name_key:
            exact_name.append(c)
        if symbol_key and c_symbol_key == symbol_key:
            exact_symbol.append(c)

    if len(exact_name) == 1:
        return exact_name[0].get("id")

    if exact_name:
        # Tie-break by symbol if possible.
        for c in exact_name:
            if normalize_key(c.get("symbol", "")) == symbol_key:
                return c.get("id")
        return exact_name[0].get("id")

    # Conservative fallback: only accept symbol match when the name contains a
    # meaningful football/world-cup token keyword.
    keywords = ["world", "cup", "fifa", "football", "soccer", "laeeb", "messi", "ronaldo"]
    candidates = [c for c in exact_symbol if any(k in normalize_key(c.get("name", "")) for k in keywords)]
    if len(candidates) == 1:
        return candidates[0].get("id")
    return None


def coingecko_market_chart(
    client: APIClient,
    coin_id: str,
    vs_currency: str,
    api_key: Optional[str],
    pro: bool,
    days: str = "max",
    interval: str = "daily",
) -> pd.DataFrame:
    url = f"{coingecko_base(pro)}/coins/{coin_id}/market_chart"
    params = {"vs_currency": vs_currency, "days": days, "interval": interval}
    data = client.get_json(url, params=params, headers=coingecko_headers(api_key, pro))
    if not data.get("prices"):
        return pd.DataFrame()

    frames = []
    mapping = {
        "prices": "price_usd" if vs_currency.lower() == "usd" else f"price_{vs_currency.lower()}",
        "market_caps": "market_cap_usd" if vs_currency.lower() == "usd" else f"market_cap_{vs_currency.lower()}",
        "total_volumes": "volume_usd" if vs_currency.lower() == "usd" else f"volume_{vs_currency.lower()}",
    }
    for key, col in mapping.items():
        rows = data.get(key, [])
        if not rows:
            continue
        df = pd.DataFrame(rows, columns=["timestamp_ms", col])
        df["datetime_utc"] = pd.to_datetime(df["timestamp_ms"], unit="ms", utc=True)
        df["date"] = df["datetime_utc"].dt.date.astype(str)
        df = df.sort_values("datetime_utc").groupby("date", as_index=False).last()[["date", col]]
        frames.append(df)

    if not frames:
        return pd.DataFrame()
    out = frames[0]
    for f in frames[1:]:
        out = out.merge(f, on="date", how="outer")
    out["date"] = pd.to_datetime(out["date"], utc=True)
    out = out.sort_values("date")
    return out


def cmc_headers(api_key: str) -> Dict[str, str]:
    return {"X-CMC_PRO_API_KEY": api_key, "Accept": "application/json"}


def cmc_find_id(client: APIClient, token: Dict[str, Any], api_key: str) -> Optional[int]:
    if token.get("cmc_id"):
        try:
            return int(token["cmc_id"])
        except Exception:
            return None
    symbol = token.get("symbol")
    slug = token.get("cmc_slug")
    if not symbol:
        return None
    url = f"{CMC_BASE}/v1/cryptocurrency/map"
    params = {
        "symbol": symbol,
        "listing_status": "active,inactive,untracked",
        "aux": "platform,first_historical_data,last_historical_data,is_active,status",
    }
    data = client.get_json(url, params=params, headers=cmc_headers(api_key))
    entries = data.get("data", [])
    if not entries:
        return None
    if slug:
        for item in entries:
            if str(item.get("slug", "")).lower() == str(slug).lower():
                return int(item["id"])
    # Fallback by name.
    name_key = normalize_key(token.get("name", ""))
    for item in entries:
        if normalize_key(item.get("name", "")) == name_key:
            return int(item["id"])
    return int(entries[0]["id"])


def cmc_historical_quotes(
    client: APIClient,
    cmc_id: int,
    vs_currency: str,
    api_key: str,
    time_start: str = "2013-01-01T00:00:00Z",
    time_end: Optional[str] = None,
    interval: str = "daily",
) -> pd.DataFrame:
    # Note: this endpoint often requires paid CMC plan access. The script logs
    # the API error instead of failing the whole run if unavailable.
    url = f"{CMC_BASE}/v2/cryptocurrency/quotes/historical"
    params = {
        "id": str(cmc_id),
        "time_start": time_start,
        "time_end": time_end or utc_now_iso(),
        "interval": interval,
        "convert": vs_currency.upper(),
        "aux": "price,volume,market_cap,timestamp",
    }
    data = client.get_json(url, params=params, headers=cmc_headers(api_key))
    payload = data.get("data", {})
    if isinstance(payload, dict) and str(cmc_id) in payload:
        payload = payload[str(cmc_id)]
    quotes = payload.get("quotes", []) if isinstance(payload, dict) else []
    rows = []
    quote_key = vs_currency.upper()
    for q in quotes:
        quote = q.get("quote", {}).get(quote_key, {})
        ts = q.get("timestamp") or quote.get("timestamp")
        if not ts:
            continue
        rows.append(
            {
                "date": pd.to_datetime(ts, utc=True),
                "price_usd" if vs_currency.lower() == "usd" else f"price_{vs_currency.lower()}": quote.get("price"),
                "volume_usd" if vs_currency.lower() == "usd" else f"volume_{vs_currency.lower()}": quote.get("volume_24h") or quote.get("volume"),
                "market_cap_usd" if vs_currency.lower() == "usd" else f"market_cap_{vs_currency.lower()}": quote.get("market_cap"),
            }
        )
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).sort_values("date")
    df["date"] = pd.to_datetime(df["date"], utc=True).dt.floor("D")
    df = df.groupby("date", as_index=False).last()
    return df


def parse_gt_timestamp(value: Any) -> pd.Timestamp:
    v = float(value)
    unit = "ms" if v > 10_000_000_000 else "s"
    return pd.to_datetime(v, unit=unit, utc=True)


def geckoterminal_search_pools(client: APIClient, query: str) -> List[Dict[str, Any]]:
    url = f"{GT_BASE}/search/pools"
    data = client.get_json(url, params={"query": query})
    return data.get("data", [])


def network_from_gt_pool_item(item: Dict[str, Any]) -> Optional[str]:
    rel = item.get("relationships", {})
    network = rel.get("network", {}).get("data", {}).get("id")
    if network:
        return network
    item_id = str(item.get("id", ""))
    if "_" in item_id:
        return item_id.split("_", 1)[0]
    return None


def address_from_gt_pool_item(item: Dict[str, Any]) -> Optional[str]:
    attrs = item.get("attributes", {})
    if attrs.get("address"):
        return attrs.get("address")
    item_id = str(item.get("id", ""))
    if "_" in item_id:
        return item_id.split("_", 1)[1]
    return item_id or None


def discover_tokens_from_geckoterminal(client: APIClient, terms: List[str], per_term_limit: int) -> List[Dict[str, Any]]:
    discovered: List[Dict[str, Any]] = []
    seen = set()
    for term in terms:
        try:
            pools = geckoterminal_search_pools(client, term)
        except Exception as exc:
            print(f"Warning: GeckoTerminal discovery failed for {term!r}: {exc}", file=sys.stderr)
            continue
        scored = []
        for item in pools:
            attrs = item.get("attributes", {})
            name = attrs.get("name") or term
            network = network_from_gt_pool_item(item)
            address = address_from_gt_pool_item(item)
            if not network or not address:
                continue
            # Use h24 volume and reserve for rough ordering.
            vol = attrs.get("volume_usd", {})
            if isinstance(vol, dict):
                vol_value = float(vol.get("h24") or 0)
            else:
                try:
                    vol_value = float(vol or 0)
                except Exception:
                    vol_value = 0.0
            try:
                reserve = float(attrs.get("reserve_in_usd") or 0)
            except Exception:
                reserve = 0.0
            scored.append((vol_value + reserve * 0.01, item, network, address, name))
        scored.sort(key=lambda x: x[0], reverse=True)
        for _, item, network, address, name in scored[:per_term_limit]:
            key = (network, address)
            if key in seen:
                continue
            seen.add(key)
            symbol = str(name).split("/")[0].strip()[:30]
            discovered.append(
                {
                    "name": name,
                    "symbol": symbol,
                    "category": "dex_discovered",
                    "gt_network": network,
                    "gt_pool": address,
                    "notes": f"Discovered via GeckoTerminal search term: {term}",
                }
            )
    return discovered


def geckoterminal_pool_ohlcv(
    client: APIClient,
    network: str,
    pool_address: str,
    aggregate: int = 1,
    timeframe: str = "day",
    max_pages: int = 6,
    before_timestamp: Optional[int] = None,
) -> pd.DataFrame:
    all_rows: List[List[Any]] = []
    before = before_timestamp
    for _ in range(max_pages):
        url = f"{GT_BASE}/networks/{network}/pools/{pool_address}/ohlcv/{timeframe}"
        params: Dict[str, Any] = {"aggregate": aggregate, "limit": 1000, "currency": "usd", "token": "base"}
        if before:
            params["before_timestamp"] = int(before)
        data = client.get_json(url, params=params)
        ohlcv = data.get("data", {}).get("attributes", {}).get("ohlcv_list", [])
        if not ohlcv:
            break
        all_rows.extend(ohlcv)
        timestamps = [float(row[0]) for row in ohlcv if row]
        if not timestamps:
            break
        min_ts = min(timestamps)
        # GT expects seconds for before_timestamp even when the list is ms.
        before = int(min_ts / 1000) - 1 if min_ts > 10_000_000_000 else int(min_ts) - 1
        # Stop if this page returned fewer than max rows.
        if len(ohlcv) < 1000:
            break
        time.sleep(client.sleep_seconds)

    if not all_rows:
        return pd.DataFrame()

    # GeckoTerminal standard OHLCV order is [timestamp, open, high, low, close, volume].
    df = pd.DataFrame(all_rows, columns=["timestamp", "open", "high", "low", "close", "volume_usd"])
    df["date"] = df["timestamp"].apply(parse_gt_timestamp).dt.floor("D")
    for col in ["open", "high", "low", "close", "volume_usd"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.sort_values("date")
    # If pages overlap, keep the last occurrence per day.
    daily = df.groupby("date", as_index=False).agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume_usd=("volume_usd", "sum"),
    )
    daily["price_usd"] = daily["close"]
    return daily


def dexscreener_snapshot_by_query(client: APIClient, query: str, limit: int = 5) -> pd.DataFrame:
    url = f"{DEX_BASE}/search"
    data = client.get_json(url, params={"q": query})
    pairs = data.get("pairs") or []
    rows = []
    for pair in pairs[:limit]:
        rows.append(
            {
                "query": query,
                "chainId": pair.get("chainId"),
                "dexId": pair.get("dexId"),
                "pairAddress": pair.get("pairAddress"),
                "baseTokenName": (pair.get("baseToken") or {}).get("name"),
                "baseTokenSymbol": (pair.get("baseToken") or {}).get("symbol"),
                "priceUsd": pair.get("priceUsd"),
                "fdv": pair.get("fdv"),
                "liquidity_usd": (pair.get("liquidity") or {}).get("usd"),
                "volume_h24": (pair.get("volume") or {}).get("h24"),
                "price_change_h24_pct": (pair.get("priceChange") or {}).get("h24"),
                "url": pair.get("url"),
            }
        )
    return pd.DataFrame(rows)


def load_tokens_from_file(path: Path) -> List[Dict[str, Any]]:
    if path.suffix.lower() == ".json":
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("JSON token file must be a list of objects")
        return [dict(x) for x in data]
    if path.suffix.lower() in [".csv", ".tsv"]:
        sep = "\t" if path.suffix.lower() == ".tsv" else ","
        df = pd.read_csv(path, sep=sep)
        return df.replace({np.nan: None}).to_dict(orient="records")
    raise ValueError("Token file must be .json, .csv, or .tsv")


def select_tokens(args: argparse.Namespace) -> List[Dict[str, Any]]:
    if args.tokens_file:
        tokens = load_tokens_from_file(Path(args.tokens_file))
    else:
        tokens = list(TOKENS)
        if not args.include_adjacent:
            tokens = [t for t in tokens if t.get("category") not in {"sports_gamefi_or_utility"}]
        if args.include_fan_tokens:
            tokens.extend(FAN_TOKENS)
    return tokens


def dedupe_tokens(tokens: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for token in tokens:
        key = (
            normalize_key(token.get("name", "")),
            normalize_key(token.get("symbol", "")),
            str(token.get("coingecko_id") or ""),
            str(token.get("cmc_slug") or ""),
            str(token.get("gt_network") or ""),
            str(token.get("gt_pool") or ""),
            str(token.get("contract") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(token)
    return out


def add_token_metadata(df: pd.DataFrame, token: Dict[str, Any], source: str, source_id: str) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["token_name"] = token.get("name")
    df["symbol"] = token.get("symbol")
    df["category"] = token.get("category")
    df["source"] = source
    df["source_id"] = source_id
    df["cmc_slug"] = token.get("cmc_slug")
    df["coingecko_id"] = token.get("coingecko_id")
    df["gt_network"] = token.get("gt_network")
    df["gt_pool"] = token.get("gt_pool")
    df["contract"] = token.get("contract")
    df["notes"] = token.get("notes")
    return df


def finite_first(series: pd.Series) -> Optional[float]:
    s = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    s = s[s > 0]
    if s.empty:
        return None
    return float(s.iloc[0])


def finite_last(series: pd.Series) -> Optional[float]:
    s = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    s = s[s > 0]
    if s.empty:
        return None
    return float(s.iloc[-1])


def max_drawdown_pct(prices: pd.Series) -> Optional[float]:
    p = pd.to_numeric(prices, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    p = p[p > 0]
    if len(p) < 2:
        return None
    running_max = p.cummax()
    drawdown = p / running_max - 1.0
    return float(drawdown.min() * 100.0)


def summarize_token_history(df: pd.DataFrame, token: Dict[str, Any], source: str, source_id: str) -> Dict[str, Any]:
    price_col = "price_usd" if "price_usd" in df.columns else next((c for c in df.columns if c.startswith("price_")), None)
    volume_col = "volume_usd" if "volume_usd" in df.columns else next((c for c in df.columns if c.startswith("volume_")), None)
    market_cap_col = "market_cap_usd" if "market_cap_usd" in df.columns else next((c for c in df.columns if c.startswith("market_cap_")), None)

    out: Dict[str, Any] = {
        "token_name": token.get("name"),
        "symbol": token.get("symbol"),
        "category": token.get("category"),
        "source": source,
        "source_id": source_id,
        "cmc_slug": token.get("cmc_slug"),
        "coingecko_id": token.get("coingecko_id"),
        "gt_network": token.get("gt_network"),
        "gt_pool": token.get("gt_pool"),
        "contract": token.get("contract"),
        "notes": token.get("notes"),
        "rows": int(len(df)),
    }
    if df.empty or not price_col:
        return out

    d = df.copy().sort_values("date")
    d[price_col] = pd.to_numeric(d[price_col], errors="coerce")
    valid_price = d[d[price_col].notna() & (d[price_col] > 0)].copy()
    if valid_price.empty:
        return out

    launch_price = finite_first(valid_price[price_col])
    last_price = finite_last(valid_price[price_col])
    first_row = valid_price.iloc[0]
    last_row = valid_price.iloc[-1]
    out.update(
        {
            "first_available_date": pd.to_datetime(first_row["date"]).date().isoformat(),
            "last_available_date": pd.to_datetime(last_row["date"]).date().isoformat(),
            "first_available_price": launch_price,
            "last_price": last_price,
            "days_covered": int((pd.to_datetime(last_row["date"]) - pd.to_datetime(first_row["date"])).days + 1),
        }
    )
    if launch_price and last_price:
        out["return_since_first_available_pct"] = (last_price / launch_price - 1.0) * 100.0

    ath_idx = valid_price[price_col].idxmax()
    atl_idx = valid_price[price_col].idxmin()
    ath_row = valid_price.loc[ath_idx]
    atl_row = valid_price.loc[atl_idx]
    out.update(
        {
            "ath_price": float(ath_row[price_col]),
            "ath_date": pd.to_datetime(ath_row["date"]).date().isoformat(),
            "atl_price": float(atl_row[price_col]),
            "atl_date": pd.to_datetime(atl_row["date"]).date().isoformat(),
            "max_drawdown_pct": max_drawdown_pct(valid_price[price_col]),
        }
    )

    if volume_col and volume_col in d.columns:
        vol = pd.to_numeric(d[volume_col], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
        out["total_reported_volume"] = float(vol.sum())
        out["average_daily_volume"] = float(vol.mean()) if len(vol) else None
        if len(vol) and vol.max() > 0:
            max_vol_idx = vol.idxmax()
            out["max_daily_volume"] = float(vol.max())
            out["max_daily_volume_date"] = pd.to_datetime(d.loc[max_vol_idx, "date"]).date().isoformat()

    if market_cap_col and market_cap_col in d.columns:
        mc = pd.to_numeric(d[market_cap_col], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if not mc.empty:
            out["last_market_cap"] = float(mc.iloc[-1])
            out["max_market_cap"] = float(mc.max())

    return out


def fetch_token_history(
    client: APIClient,
    token: Dict[str, Any],
    args: argparse.Namespace,
    coins_list: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    log: Dict[str, Any] = {
        "token_name": token.get("name"),
        "symbol": token.get("symbol"),
        "category": token.get("category"),
        "status": "not_fetched",
        "source": None,
        "source_id": None,
        "error": None,
        "timestamp_utc": utc_now_iso(),
    }

    # 1. CoinGecko by explicit or inferred ID.
    cg_id = token.get("coingecko_id")
    if not cg_id and args.autodiscover_coingecko and coins_list is not None:
        cg_id = infer_coingecko_id(token, coins_list)
    if cg_id:
        try:
            df = coingecko_market_chart(
                client,
                str(cg_id),
                args.vs_currency,
                args.cg_api_key,
                args.cg_pro,
                days="max",
                interval="daily",
            )
            if not df.empty:
                token = dict(token)
                token["coingecko_id"] = str(cg_id)
                log.update({"status": "ok", "source": "coingecko", "source_id": str(cg_id), "rows": len(df)})
                return add_token_metadata(df, token, "coingecko", str(cg_id)), log
            log.update({"status": "empty", "source": "coingecko", "source_id": str(cg_id)})
        except Exception as exc:
            log.update({"status": "error", "source": "coingecko", "source_id": str(cg_id), "error": str(exc)})

    # 2. Optional CoinMarketCap Pro API.
    if args.use_cmc and args.cmc_api_key and (token.get("cmc_id") or token.get("cmc_slug") or token.get("symbol")):
        try:
            cmc_id = cmc_find_id(client, token, args.cmc_api_key)
            if cmc_id:
                df = cmc_historical_quotes(client, cmc_id, args.vs_currency, args.cmc_api_key)
                if not df.empty:
                    log.update({"status": "ok", "source": "coinmarketcap", "source_id": str(cmc_id), "rows": len(df)})
                    return add_token_metadata(df, token, "coinmarketcap", str(cmc_id)), log
                log.update({"status": "empty", "source": "coinmarketcap", "source_id": str(cmc_id)})
        except Exception as exc:
            previous_error = log.get("error")
            log.update({"status": "error", "source": "coinmarketcap", "error": (previous_error + " | " if previous_error else "") + str(exc)})

    # 3. GeckoTerminal by explicit pool.
    if token.get("gt_network") and token.get("gt_pool"):
        try:
            df = geckoterminal_pool_ohlcv(
                client,
                str(token["gt_network"]),
                str(token["gt_pool"]),
                aggregate=args.gt_aggregate,
                timeframe=args.gt_timeframe,
                max_pages=args.gt_max_pages,
            )
            if not df.empty:
                source_id = f"{token['gt_network']}:{token['gt_pool']}"
                log.update({"status": "ok", "source": "geckoterminal", "source_id": source_id, "rows": len(df)})
                return add_token_metadata(df, token, "geckoterminal", source_id), log
            log.update({"status": "empty", "source": "geckoterminal", "source_id": f"{token['gt_network']}:{token['gt_pool']}"})
        except Exception as exc:
            previous_error = log.get("error")
            log.update({"status": "error", "source": "geckoterminal", "error": (previous_error + " | " if previous_error else "") + str(exc)})

    # 4. Optional fallback: search GeckoTerminal by name and use highest-ranked pool.
    if args.fallback_search_gt:
        query = f"{token.get('name', '')} {token.get('symbol', '')}".strip()
        if query:
            try:
                pools = geckoterminal_search_pools(client, query)
                best = None
                best_score = -1.0
                for item in pools:
                    network = network_from_gt_pool_item(item)
                    address = address_from_gt_pool_item(item)
                    attrs = item.get("attributes", {})
                    if not network or not address:
                        continue
                    name = normalize_key(attrs.get("name", ""))
                    # Require name evidence to reduce false positives.
                    wanted = normalize_key(token.get("name", ""))
                    sym = normalize_key(token.get("symbol", ""))
                    if wanted and wanted not in name and sym and sym not in name:
                        continue
                    vol = attrs.get("volume_usd", {})
                    if isinstance(vol, dict):
                        score = float(vol.get("h24") or 0)
                    else:
                        score = float(vol or 0)
                    try:
                        score += float(attrs.get("reserve_in_usd") or 0) * 0.01
                    except Exception:
                        pass
                    if score > best_score:
                        best = (network, address)
                        best_score = score
                if best:
                    network, address = best
                    df = geckoterminal_pool_ohlcv(client, network, address, args.gt_aggregate, args.gt_timeframe, args.gt_max_pages)
                    if not df.empty:
                        source_id = f"{network}:{address}"
                        token = dict(token)
                        token["gt_network"] = network
                        token["gt_pool"] = address
                        token["notes"] = (token.get("notes") or "") + " | GT pool found by fallback search; verify token identity."
                        log.update({"status": "ok", "source": "geckoterminal_search", "source_id": source_id, "rows": len(df)})
                        return add_token_metadata(df, token, "geckoterminal_search", source_id), log
            except Exception as exc:
                previous_error = log.get("error")
                log.update({"status": "error", "source": "geckoterminal_search", "error": (previous_error + " | " if previous_error else "") + str(exc)})

    return pd.DataFrame(), log


def write_token_universe(tokens: List[Dict[str, Any]], out_dir: Path) -> None:
    with (out_dir / "token_universe.json").open("w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2, ensure_ascii=False)
    pd.DataFrame(tokens).to_csv(out_dir / "token_universe.csv", index=False)


def plot_outputs(history: pd.DataFrame, out_dir: Path) -> None:
    import matplotlib.pyplot as plt

    plot_dir = out_dir / "plots"
    ensure_dir(plot_dir)
    if history.empty or "price_usd" not in history.columns:
        return
    for (name, symbol, source_id), group in history.groupby(["token_name", "symbol", "source_id"], dropna=False):
        g = group.sort_values("date").copy()
        if g["price_usd"].dropna().empty:
            continue
        safe_name = normalize_key(f"{name}_{symbol}_{source_id}")[:120] or "token"

        plt.figure(figsize=(10, 5))
        plt.plot(pd.to_datetime(g["date"]), g["price_usd"])
        plt.xlabel("Date")
        plt.ylabel("Price USD")
        plt.title(f"{name} ({symbol}) price")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(plot_dir / f"{safe_name}_price.png", dpi=140)
        plt.close()

        if "volume_usd" in g.columns and not g["volume_usd"].dropna().empty:
            plt.figure(figsize=(10, 5))
            plt.plot(pd.to_datetime(g["date"]), g["volume_usd"])
            plt.xlabel("Date")
            plt.ylabel("Volume USD")
            plt.title(f"{name} ({symbol}) reported volume")
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(plot_dir / f"{safe_name}_volume.png", dpi=140)
            plt.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compile World Cup/soccer memecoin price and volume history.")
    parser.add_argument("--out-dir", default="soccer_memecoin_output", help="Output directory")
    parser.add_argument("--tokens-file", default=None, help="Optional JSON/CSV/TSV token list to use instead of the built-in seed list")
    parser.add_argument("--include-adjacent", action="store_true", help="Include soccer GameFi/utility/community tokens beyond core memecoins")
    parser.add_argument("--include-fan-tokens", action="store_true", help="Include official club/national fan tokens for benchmarking")
    parser.add_argument("--vs-currency", default="usd", help="Quote currency, default usd")

    parser.add_argument("--cg-api-key", default=os.getenv("COINGECKO_API_KEY"), help="Optional CoinGecko Demo/Pro API key")
    parser.add_argument("--cg-pro", action="store_true", help="Use CoinGecko Pro base URL and x-cg-pro-api-key header")
    parser.add_argument("--autodiscover-coingecko", action="store_true", help="Try to infer CoinGecko IDs for tokens missing coingecko_id")
    parser.add_argument("--refresh-caches", action="store_true", help="Refresh local API mapping caches")

    parser.add_argument("--use-cmc", action="store_true", help="Use optional CoinMarketCap Pro API fallback")
    parser.add_argument("--cmc-api-key", default=os.getenv("CMC_API_KEY"), help="CoinMarketCap Pro API key")

    parser.add_argument("--gt-timeframe", default="day", choices=["minute", "hour", "day"], help="GeckoTerminal OHLCV timeframe")
    parser.add_argument("--gt-aggregate", type=int, default=1, help="GeckoTerminal OHLCV aggregate value")
    parser.add_argument("--gt-max-pages", type=int, default=6, help="Max pages of GT OHLCV per pool")
    parser.add_argument("--fallback-search-gt", action="store_true", help="If no direct source works, search GeckoTerminal pools by token name/symbol")
    parser.add_argument("--discover-dex", action="store_true", help="Add tokens discovered from GeckoTerminal search terms")
    parser.add_argument("--dex-discovery-limit", type=int, default=3, help="Max GT pools to add per discovery term")
    parser.add_argument("--discovery-terms", default=None, help="Comma-separated GeckoTerminal discovery search terms")

    parser.add_argument("--dexscreener-snapshots", action="store_true", help="Also save live DexScreener search snapshots; not historical")
    parser.add_argument("--plot", action="store_true", help="Write simple PNG price and volume plots")
    parser.add_argument("--sleep", type=float, default=1.2, help="Delay/retry backoff between API calls")
    parser.add_argument("--retries", type=int, default=3, help="HTTP retries")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    ensure_dir(out_dir)
    cache_dir = out_dir / ".cache"
    ensure_dir(cache_dir)

    client = APIClient(sleep_seconds=args.sleep, retries=args.retries)
    tokens = select_tokens(args)

    if args.discover_dex:
        terms = [t.strip() for t in (args.discovery_terms.split(",") if args.discovery_terms else DISCOVERY_TERMS) if t.strip()]
        discovered = discover_tokens_from_geckoterminal(client, terms, args.dex_discovery_limit)
        tokens.extend(discovered)
        print(f"Added {len(discovered)} GeckoTerminal-discovered pool tokens.", file=sys.stderr)

    tokens = dedupe_tokens(tokens)
    write_token_universe(tokens, out_dir)

    coins_list = None
    if args.autodiscover_coingecko:
        try:
            coins_list = load_coingecko_coin_list(client, cache_dir, args.cg_api_key, args.cg_pro, refresh=args.refresh_caches)
        except Exception as exc:
            print(f"Warning: Could not load CoinGecko coin list: {exc}", file=sys.stderr)
            coins_list = None

    all_history: List[pd.DataFrame] = []
    summaries: List[Dict[str, Any]] = []
    logs: List[Dict[str, Any]] = []

    for idx, token in enumerate(tokens, 1):
        label = f"{token.get('name')} ({token.get('symbol')})"
        print(f"[{idx}/{len(tokens)}] Fetching {label}...", file=sys.stderr)
        df, log = fetch_token_history(client, token, args, coins_list)
        logs.append(log)
        if not df.empty:
            all_history.append(df)
            summaries.append(summarize_token_history(df, token, str(log.get("source")), str(log.get("source_id"))))
        else:
            summaries.append(summarize_token_history(df, token, str(log.get("source") or "none"), str(log.get("source_id") or "")))
        time.sleep(args.sleep)

    if all_history:
        history = pd.concat(all_history, ignore_index=True, sort=False)
        # Put common columns first.
        first_cols = [
            "token_name", "symbol", "category", "date", "price_usd", "open", "high", "low", "close",
            "volume_usd", "market_cap_usd", "source", "source_id", "coingecko_id", "cmc_slug",
            "gt_network", "gt_pool", "contract", "notes",
        ]
        cols = [c for c in first_cols if c in history.columns] + [c for c in history.columns if c not in first_cols]
        history = history[cols].sort_values(["token_name", "source_id", "date"])
    else:
        history = pd.DataFrame()

    summary = pd.DataFrame(summaries)
    if not summary.empty:
        sort_cols = [c for c in ["category", "token_name", "symbol"] if c in summary.columns]
        summary = summary.sort_values(sort_cols)

    fetch_log = pd.DataFrame(logs)

    history.to_csv(out_dir / "daily_history.csv", index=False)
    summary.to_csv(out_dir / "token_summary.csv", index=False)
    fetch_log.to_csv(out_dir / "fetch_log.csv", index=False)

    with (out_dir / "run_metadata.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at_utc": utc_now_iso(),
                "token_count": len(tokens),
                "history_rows": int(len(history)),
                "arguments": {k: ("***" if "key" in k and v else v) for k, v in vars(args).items()},
                "caveat": "Since launch means earliest source-available historical row; verify contracts/pools for duplicate meme tokens.",
            },
            f,
            indent=2,
        )

    if args.dexscreener_snapshots:
        snap_frames = []
        terms = [t.strip() for t in (args.discovery_terms.split(",") if args.discovery_terms else DISCOVERY_TERMS) if t.strip()]
        for term in terms:
            try:
                snap_frames.append(dexscreener_snapshot_by_query(client, term, limit=args.dex_discovery_limit))
                time.sleep(args.sleep)
            except Exception as exc:
                print(f"Warning: DexScreener snapshot failed for {term!r}: {exc}", file=sys.stderr)
        if snap_frames:
            pd.concat(snap_frames, ignore_index=True).to_csv(out_dir / "dexscreener_live_snapshots.csv", index=False)

    if args.plot and not history.empty:
        plot_outputs(history, out_dir)

    print(f"\nWrote outputs to: {out_dir.resolve()}")
    print(f"  daily_history.csv rows: {len(history)}")
    print(f"  token_summary.csv rows: {len(summary)}")
    print("  fetch_log.csv records each source success/error.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

I treated “memecoin” broadly, but kept **official club/national fan tokens separate** because they are usually utility/fan-engagement assets rather than meme tokens. CoinMarketCap’s Soccer category is the broadest indexed base I found; it lists 53 soccer-related crypto assets and includes both official fan tokens and long-tail World Cup/soccer meme or parody tokens. ([CoinMarketCap][1])

## Core World Cup / soccer memecoin seed list

The script includes these as the default core universe:

| Token / theme                               |           Symbol | Notes                                                                                                                                               |
| ------------------------------------------- | ---------------: | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Football World Community / Qatar 2022 Token |              FWC | World Cup / football community token; CoinGecko ID included.                                                                                        |
| World Cup Token                             |              WCT | CMC describes it as a meme project for football fans and Qatar 2022 World Cup season. ([CoinMarketCap][2])                                          |
| FIFA World Cup Fans                         |             FIFA | Soccer / World Cup fan-style token.                                                                                                                 |
| FIFA                                        |             FIFA | FIFA-named long-tail token, not official FIFA.                                                                                                      |
| WORLD CUP INU                               |              WCI | World Cup / Inu meme token.                                                                                                                         |
| FIFA-Laeeb                                  |            LAEEB | 2022 World Cup mascot-themed token.                                                                                                                 |
| Laeeb Inu                                   |            LAEEB | Laeeb / World Cup / Inu variant.                                                                                                                    |
| Fifa Inu                                    |             FINU | FIFA / Inu meme token.                                                                                                                              |
| Football INU                                |         FOOTBALL | Football / Inu meme token.                                                                                                                          |
| SoccerInu                                   |           SOCCER | Soccer-themed meme token; GeckoTerminal describes a Solana revival as football-inspired and born in World Cup 2022. ([GeckoTerminal][3])            |
| World Cup Willie                            |           WILLIE | Mascot-themed meme token.                                                                                                                           |
| Shiba World Cup                             |              SWC | Shiba / World Cup meme token.                                                                                                                       |
| FIFADOGE                                    |            FDOGE | FIFA / Doge meme token.                                                                                                                             |
| WORLD CUP DOGE                              |           WCDOGE | World Cup / Doge meme token.                                                                                                                        |
| World Cup Pot                               |              WCP | World Cup-themed token.                                                                                                                             |
| WORLD CUP COIN                              |         WORLDCUP | CMC variants plus Solana pool seed.                                                                                                                 |
| WORLD CUP 2026                              | WORLDCUP26 / W26 | 2026 World Cup-themed tokens; duplicate names/symbols exist, so pool verification matters.                                                          |
| FIFA WORLD CUP                              |              FWC | 2026 / World Cup-named CMC token variant.                                                                                                           |
| 2026 World Cup Mascots                      |          MASCOTS | Solana memecoin referencing the 2026 mascots; contract/pool included. ([$MASCOTS · 2026 World Cup][4])                                              |
| WorldCup26Goals                             |          WCGOALS | 2026 goals / Golden Boot-themed Solana token.                                                                                                       |
| Messi Coin                                  |            MESSI | Player-themed meme token.                                                                                                                           |
| Cristiano Ronaldo Meme                      |              CR7 | Player-themed meme token; CMC has also warned about fake Ronaldo-inspired tokens and rug-pull behavior around CR7 narratives. ([CoinMarketCap][5])  |
| WATER Coin                                  |            WATER | Not soccer-branded, but included as optional footballer-promoted research scope because Messi promoted WaterCoin on Instagram. ([CoinMarketCap][6]) |

## Soccer-adjacent tokens included with `--include-adjacent`

These are not necessarily memecoins, but they are useful for a broader soccer-token benchmark:

FIFA Champs, World Football, FiFaSport, World Bet Club, Soccer Galaxy, Football Decentralized, Futuball, Football Stars, Minifootball, SoccerHub, FootBallGo, Soccer Infinity, FootballCoin/FBC, Football Coin/XFC, Football Battle, and Pitch World Cup. CoinMarketCap’s Soccer category lists many of these long-tail soccer assets alongside World Cup Token, FIFA Champs, FIFA World Cup Fans, WORLD CUP INU, FIFA-Laeeb, SoccerInu, Fifa Inu, World Cup Willie, Shiba World Cup, FIFADOGE, and World Cup Pot. ([CoinMarketCap][1])

## What the script does

The script compiles daily history and summary metrics for each token:

* First available date and price.
* Last price.
* Return since first available source record.
* ATH / ATL and dates.
* Max drawdown.
* Total reported volume and average daily volume.
* Max daily volume and date.
* Source success/error logs.

It outputs:

```text
daily_history.csv
token_summary.csv
fetch_log.csv
token_universe.csv
token_universe.json
run_metadata.json
```

It uses CoinGecko first because its historical market chart endpoint returns price, market cap, and total volume arrays for a coin ID. ([CoinGecko API][7]) For newer DEX-only launches, it falls back to GeckoTerminal OHLCV by pool, whose API supports pool OHLCV endpoints, though historical coverage can be limited. ([CoinGecko][8]) It also supports optional CoinMarketCap Pro API if you provide `CMC_API_KEY`; CMC’s API docs include historical quote endpoints. ([CoinMarketCap][9])

## Example usage

```bash
python -m pip install requests pandas numpy matplotlib

python soccer_memecoin_data_compiler.py --out-dir out
```

Broader universe, including GameFi/utility soccer tokens:

```bash
python soccer_memecoin_data_compiler.py --include-adjacent --out-dir out
```

Add official club/national fan tokens for comparison:

```bash
python soccer_memecoin_data_compiler.py --include-adjacent --include-fan-tokens --out-dir out
```

Try to discover additional DEX-only World Cup clones:

```bash
python soccer_memecoin_data_compiler.py --discover-dex --fallback-search-gt --out-dir out
```

Use CoinMarketCap fallback if you have a key:

```bash
CMC_API_KEY=your_key python soccer_memecoin_data_compiler.py --use-cmc --out-dir out
```

Key caveat: for meme tokens, “since launch” often means **since earliest available data from the source**, not necessarily the exact on-chain deployment moment. The script writes this distinction into `run_metadata.json` and `fetch_log.csv`.

[1]: https://coinmarketcap.com/view/soccer/ "Top Soccer Tokens by Market Capitalization | CoinMarketCap"
[2]: https://coinmarketcap.com/currencies/world-cup-token/ "World Cup Token price today, WCT to USD live price, marketcap and chart | CoinMarketCap"
[3]: https://www.geckoterminal.com/solana/pools/3Bkae5Yhd27RzfhPogDfWRJms2HbKMSQn6MQyD8tH8nw?utm_source=chatgpt.com "SOCCERINU/SOL - SoccerInu Price on PumpSwap | GeckoTerminal"
[4]: https://www.worldcupmascots.xyz/?utm_source=chatgpt.com "$MASCOTS · 2026 World Cup Mascots — Solana Memecoin"
[5]: https://coinmarketcap.com/academy/article/cr7-token-hits-dollar143m-market-cap-before-98percent-crash?utm_source=chatgpt.com "CR7 Token Hits $143M Market Cap Before 98% Crash | CoinMarketCap"
[6]: https://coinmarketcap.com/academy/article/lionel-messi-promotes-solana-based-memecoin-watercoin-on-instagram?utm_source=chatgpt.com "Lionel Messi Promotes Solana-Based Memecoin WaterCoin ... - CoinMarketCap"
[7]: https://docs.coingecko.com/reference/coins-id-market-chart-range "Coin Historical Chart Data within Time Range by ID - CoinGecko API"
[8]: https://www.coingecko.com/learn/dex-data-api "How to Get Onchain Data with GeckoTerminal API | CoinGecko API"
[9]: https://coinmarketcap.com/api/documentation/pro-api-reference?utm_source=chatgpt.com "CoinMarketCap Cryptocurrency API Documentation"
