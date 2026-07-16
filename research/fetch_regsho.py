#!/usr/bin/env python3
"""
Fetch FINRA RegSHO daily short-sale volume files (the darkpool feed's source)
for the last N years, into research/data/regsho.csv.

One pipe-delimited file per trading day at
https://cdn.finra.org/equity/regsho/daily/CNMSshvol{YYYYMMDD}.txt — free, no
key. Non-trading days 404 and are skipped.

    python research/fetch_regsho.py --years 3
"""

from __future__ import annotations

import argparse
import io
import os
import time

import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
URL = "https://cdn.finra.org/equity/regsho/daily/CNMSshvol{d}.txt"

# The delta-terminal equity watchlist (feeds/equity_alpha.py) + its ETFs.
WATCHLIST = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA", "AMD", "AVGO", "ORCL",
    "CRM", "ADBE", "INTC", "QCOM", "NFLX", "UBER", "ABNB", "SNAP", "PINS", "RBLX",
    "JPM", "GS", "BAC", "MS", "V", "MA", "BRK.B", "AXP", "BLK", "SCHW",
    "UNH", "LLY", "JNJ", "PFE", "MRK", "ABBV", "BMY", "AMGN", "GILD", "CVS",
    "XOM", "CVX", "COP", "NEE", "GE", "CAT", "BA", "LMT", "RTX", "HON",
    "COST", "WMT", "HD", "TGT", "NKE", "MCD", "SBUX", "DIS", "CMCSA", "T",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=float, default=3.0)
    args = ap.parse_args()

    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    sess = requests.Session()
    sess.headers.update({"User-Agent": "delta-terminal-research/0.1"})

    end = pd.Timestamp.utcnow().normalize().tz_localize(None)
    days = pd.bdate_range(end - pd.Timedelta(days=int(args.years * 365.25)), end)
    keep = set(WATCHLIST)
    frames, misses = [], 0
    for i, d in enumerate(days):
        try:
            r = sess.get(URL.format(d=d.strftime("%Y%m%d")), timeout=15)
            if r.status_code != 200 or not r.text.startswith("Date"):
                misses += 1
                continue
            df = pd.read_csv(io.StringIO(r.text), sep="|")
            df = df[df["Symbol"].isin(keep)]
            if len(df):
                frames.append(df[["Date", "Symbol", "ShortVolume", "TotalVolume"]])
        except Exception:
            misses += 1
        if i % 100 == 0:
            print(f"  {d.date()}  ({len(frames)} days kept, {misses} misses)", flush=True)
        time.sleep(0.05)

    out = pd.concat(frames, ignore_index=True)
    path = os.path.join(HERE, "data", "regsho.csv")
    out.to_csv(path, index=False)
    print(f"wrote {path}: {len(out)} rows, "
          f"{out['Date'].nunique()} days, {out['Symbol'].nunique()} symbols")


if __name__ == "__main__":
    main()
