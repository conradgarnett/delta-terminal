#!/usr/bin/env python3
"""
Daily options-chain snapshotter — building the proprietary dataset that makes
the terminal's mispricing scanner (feeds/options_mispricing.py) backtestable.

Free options chains have NO history: you can only see today. Whoever snapshots
them forward owns a dataset nobody can download later. This script appends one
compressed per-day snapshot of full chains (all strikes, ~6 near expiries,
bid/ask/IV/volume/OI) for a fixed 20-name universe. After ~6 months there is
enough to event-study the scanner's "mispriced" flags against what the options
actually did — until then, DO NOT trade the scanner's flags on faith.

Universe (fixed up front — index ETFs + the most liquid watchlist names):
    SPY QQQ IWM TLT GLD  AAPL MSFT NVDA GOOGL META
    AMZN TSLA AMD AVGO NFLX  JPM XOM UNH LLY COST

Scheduled by ~/Library/LaunchAgents/com.conradgarnett.options-snapshot.plist
(weekdays 15:45 ET; launchd runs it on next wake if the Mac was asleep).
Manual run:  python research/snapshot_options.py
Output:      research/data/options_snapshots/YYYY-MM-DD.csv.gz  (~1-3 MB/day)
"""

from __future__ import annotations

import datetime as dt
import os
import sys
import time

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "options_snapshots")
LOG = os.path.join(OUT, "snapshot.log")

UNIVERSE = ["SPY", "QQQ", "IWM", "TLT", "GLD",
            "AAPL", "MSFT", "NVDA", "GOOGL", "META",
            "AMZN", "TSLA", "AMD", "AVGO", "NFLX",
            "JPM", "XOM", "UNH", "LLY", "COST"]
MAX_EXPIRIES = 6


def log(msg):
    line = f"{dt.datetime.now().isoformat(timespec='seconds')} {msg}"
    print(line)
    os.makedirs(OUT, exist_ok=True)
    with open(LOG, "a") as fh:
        fh.write(line + "\n")


def snapshot():
    import yfinance as yf

    os.makedirs(OUT, exist_ok=True)
    today = dt.date.today()
    if today.weekday() >= 5:
        log("weekend — skipping")
        return 0
    path = os.path.join(OUT, f"{today}.csv.gz")
    if os.path.exists(path):
        log(f"{today} already snapshotted — skipping")
        return 0

    frames = []
    for sym in UNIVERSE:
        try:
            tk = yf.Ticker(sym)
            spot = tk.fast_info.get("lastPrice")
            for exp in (tk.options or [])[:MAX_EXPIRIES]:
                ch = tk.option_chain(exp)
                for kind, df in (("C", ch.calls), ("P", ch.puts)):
                    if df is None or df.empty:
                        continue
                    df = df[["strike", "bid", "ask", "lastPrice", "volume",
                             "openInterest", "impliedVolatility"]].copy()
                    df["type"] = kind
                    df["expiry"] = exp
                    df["symbol"] = sym
                    df["spot"] = spot
                    frames.append(df)
            time.sleep(1.0)                      # be gentle with the source
        except Exception as e:  # noqa: BLE001 — one bad name shouldn't kill the day
            log(f"  {sym}: FAILED {type(e).__name__}: {e}")

    if not frames:
        log("no data fetched — nothing written")
        return 1
    out = pd.concat(frames, ignore_index=True)
    out["snapshot_date"] = str(today)
    out.to_csv(path, index=False, compression="gzip")
    log(f"wrote {os.path.basename(path)}: {len(out)} contracts, "
        f"{out['symbol'].nunique()} symbols")
    return 0


if __name__ == "__main__":
    sys.exit(snapshot())
