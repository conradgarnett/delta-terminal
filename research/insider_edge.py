#!/usr/bin/env python3
"""
Edge C — insider-buying clusters (the sec_edgar feed's source).

PRE-REGISTERED HYPOTHESIS — this file is committed BEFORE the Form 4 data
finished downloading (check the git history), so nothing here was tuned to
results:

    EVENT   a stock-week where officers/directors made open-market purchases
            (Form 4 transaction code P, acquired) totaling >= $100k.
            Open-market buys are the informative rarity at mega-caps —
            insiders only reach into their own pocket when they mean it.
            (Sales are mostly liquidity/diversification -> ignored.)
    ENTRY   close of the first trading day AFTER the filing date (Form 4s
            file within 2 business days of the trade; using the filing date
            keeps the signal causal).
    MEASURE abnormal return = stock return - SPY return over the next
            5 / 21 / 63 trading days.
    JUDGE   mean abnormal return per horizon with a t-stat, hit rate,
            year-by-year breakdown, and the same stats for a RANDOM baseline
            (same stocks, random weeks) to confirm the machinery is unbiased.

Thresholds ($100k, horizons 5/21/63) were fixed up front and are not swept.

    python research/fetch_form4.py --years 3     # data (once, ~1h)
    python research/insider_edge.py
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FORM4 = os.path.join(HERE, "data", "form4_transactions.csv")
PRICES = os.path.join(HERE, "data", "watchlist_prices.csv")

MIN_DOLLARS = 100_000
HORIZONS = (5, 21, 63)


def load():
    tx = pd.read_csv(FORM4, parse_dates=["filing_date"])
    px = pd.read_csv(PRICES, index_col=0, parse_dates=True)
    return tx, px


def build_events(tx):
    """Stock-weeks with >= $100k of open-market insider buying."""
    buys = tx[(tx["code"] == "P")
              & (tx["acq_disp"].fillna("A") == "A")
              & (tx["is_officer"] | tx["is_director"])].copy()
    buys["dollars"] = buys["shares"] * buys["price"].fillna(0.0)
    buys["week"] = buys["filing_date"].dt.to_period("W")
    grp = (buys.groupby(["ticker", "week"])
               .agg(dollars=("dollars", "sum"),
                    last_filing=("filing_date", "max"),
                    n_insiders=("filing_date", "count"))
               .reset_index())
    return grp[grp["dollars"] >= MIN_DOLLARS]


def abnormal_returns(events, px, horizons):
    spy = px["SPY"]
    rows = []
    for _, ev in events.iterrows():
        t = ev["ticker"].replace("-", ".")
        col = t if t in px.columns else ev["ticker"]
        if col not in px.columns:
            continue
        s = px[col].dropna()
        after = s.index[s.index > ev["last_filing"]]
        if not len(after):
            continue
        d0 = after[0]                              # entry: next close
        i0 = s.index.get_loc(d0)
        row = {"ticker": ev["ticker"], "date": d0, "dollars": ev["dollars"],
               "n_insiders": ev["n_insiders"], "year": d0.year}
        ok = False
        for h in horizons:
            if i0 + h < len(s):
                r_stock = s.iloc[i0 + h] / s.iloc[i0] - 1
                r_spy = (spy.reindex(s.index).iloc[i0 + h]
                         / spy.reindex(s.index).iloc[i0] - 1)
                row[f"abn_{h}d"] = r_stock - r_spy
                ok = True
        if ok:
            rows.append(row)
    return pd.DataFrame(rows)


def report(df, horizons, label):
    print(f"\n— {label} ({len(df)} events) —")
    for h in horizons:
        col = f"abn_{h}d"
        r = df[col].dropna()
        if len(r) < 5:
            print(f"  {h:3d}d: too few events")
            continue
        t = r.mean() / r.std() * np.sqrt(len(r)) if r.std() > 0 else 0.0
        print(f"  {h:3d}d: mean abn {r.mean():+7.3%} | t {t:5.2f} | "
              f"hit {(r > 0).mean():5.1%} | n {len(r)}")


def main():
    tx, px = load()
    events = build_events(tx)
    print(f"Form 4 rows: {len(tx)} | qualifying buy events (>=${MIN_DOLLARS:,}): "
          f"{len(events)} across {events['ticker'].nunique()} tickers")

    df = abnormal_returns(events, px, HORIZONS)
    report(df, HORIZONS, "insider-buy events")

    # Random baseline: same machinery, random stock-weeks. Should be ~0;
    # if it isn't, the pipeline itself is biased and the event numbers lie.
    rng = np.random.default_rng(0)
    fake = events.copy()
    span = px.index[70:-70]
    fake["last_filing"] = pd.Series(rng.choice(span, size=len(fake)),
                                    index=fake.index)
    report(abnormal_returns(fake, px, HORIZONS), HORIZONS,
           "random baseline (must be ~0)")

    if len(df):
        print("\n— by year (21d horizon) —")
        for y, seg in df.groupby("year"):
            r = seg["abn_21d"].dropna()
            if len(r) >= 5:
                print(f"  {y}: mean {r.mean():+7.3%} | hit {(r > 0).mean():5.1%} | n {len(r)}")

    print("\nVerdict guide: edge requires positive mean abnormal return with"
          "\n|t| >= 2 at some horizon, a ~0 random baseline, and no single year"
          "\ncarrying it. Anything less is noise, and gets reported as noise.")


if __name__ == "__main__":
    main()
