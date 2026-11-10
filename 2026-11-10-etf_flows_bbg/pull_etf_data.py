"""Export Bloomberg FUND_FLOW history. Requires a logged-in Bloomberg Terminal."""
import argparse
import logging
import os
from pathlib import Path
import tempfile
import time

import pandas as pd

TICKERS = [
    f"{symbol} US Equity" for symbol in
    "GBTC IBIT FBTC ARKB BITB BTCO HODL BRRR EZBC BTCW BTC DEFI MSBT".split()
]
BASE_DIR = Path(__file__).resolve().parent
LOG = logging.getLogger(__name__)


def normalize_flows(raw, tickers=TICKERS):
    """Accept both classic xbbg wide frames and newer Narwhals long frames."""
    if raw is None:
        raise ValueError("Bloomberg returned no data")
    df = raw.to_pandas() if hasattr(raw, "to_pandas") else pd.DataFrame(raw).copy()
    if df.empty:
        raise ValueError("Bloomberg returned no data; check Terminal login and API connection")
    names = {str(c).lower(): c for c in df.columns}
    if {"date", "ticker"}.issubset(names):
        if "field" in names:
            df = df[df[names["field"]].astype(str).str.upper() == "FUND_FLOW"]
        value_col = names.get("value", names.get("fund_flow"))
        if value_col is None:
            raise ValueError(f"Unrecognized Bloomberg columns: {list(df.columns)}")
        df = df.pivot(index=names["date"], columns=names["ticker"], values=value_col)
    elif isinstance(df.columns, pd.MultiIndex):
        if df.columns.nlevels != 2:
            raise ValueError("Unexpected Bloomberg column layout")
        fields = df.columns.get_level_values(1).astype(str).str.upper()
        df = df.loc[:, fields == "FUND_FLOW"]
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index, errors="raise")
    if df.index.has_duplicates or df.columns.has_duplicates:
        raise ValueError("Duplicate dates or tickers in Bloomberg response")
    df = df.reindex(columns=tickers).apply(pd.to_numeric, errors="raise")
    if df.empty or not df.notna().any().any():
        raise ValueError("No usable FUND_FLOW observations returned")
    missing = df.columns[df.isna().all()].tolist()
    if missing:
        raise ValueError(f"No observations for requested ETFs: {missing}; exports left unchanged")
    df.index.name = "Date"
    df.columns.name = None
    return df.sort_index(ascending=False)


def atomic_csv(df, path):
    """Stage in the destination directory so replacement is atomic per file."""
    path = Path(path)
    fd, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    os.close(fd)
    try:
        df.to_csv(temporary)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def fetch_etf_flows(start_date="2024-01-11", end_date=None, output_dir=BASE_DIR,
                   retries=3):
    from xbbg import blp

    start = pd.Timestamp(start_date).normalize()
    end = pd.Timestamp(end_date or pd.Timestamp.today()).normalize()
    if pd.isna(start) or pd.isna(end) or start > end:
        raise ValueError("Start and end dates must be valid, with start <= end")
    LOG.info("Fetching FUND_FLOW from %s to %s", start.date(), end.date())
    # Full refresh deliberately captures Bloomberg revisions to older observations.
    for attempt in range(1, retries + 1):
        try:
            raw = blp.bdh(tickers=TICKERS, flds=["FUND_FLOW"],
                          start_date=start.strftime("%Y-%m-%d"),
                          end_date=end.strftime("%Y-%m-%d"))
            df = normalize_flows(raw)
            break
        except Exception:
            if attempt == retries:
                raise
            LOG.warning("Pull failed (attempt %d/%d); retrying", attempt, retries,
                        exc_info=True)
            time.sleep(2 * attempt)
    df = df.loc[(df.index >= start) & (df.index <= end)].copy()
    if df.empty:
        raise ValueError("No observations in requested date range")
    # Keep missing values blank, not zero: unavailable is not a reported zero flow.
    df["Total"] = df[TICKERS].sum(axis=1, min_count=1)
    weekly = df["Total"].resample("W-FRI").sum(min_count=1).sort_index(ascending=False)
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    atomic_csv(df, output / "etf_fund_flows.csv")
    atomic_csv(weekly, output / "weekly_etf_fund_flows.csv")
    LOG.info("Saved %d daily rows through %s and %d weekly rows to %s",
             len(df), df.index.max().date(), len(weekly), output)
    LOG.info("Totals sum available observations; missing values remain blank. "
             "Latest week may be incomplete and recent flows may be revised.")
    print(df.head().to_string())
    return df


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", default="2024-01-11")
    parser.add_argument("--end-date", help="Default: today")
    parser.add_argument("--output-dir", type=Path, default=BASE_DIR)
    parser.add_argument("--retries", type=int, default=3)
    args = parser.parse_args()
    if args.retries < 1:
        parser.error("--retries must be at least 1")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        fetch_etf_flows(args.start_date, args.end_date, args.output_dir, args.retries)
    except Exception as exc:
        LOG.error("ETF export failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
