#!/usr/bin/env python3
"""
Edge B — abnormal short-sale volume (the darkpool feed's FINRA RegSHO source).

PRE-REGISTERED HYPOTHESIS (declared before results were seen; nothing swept):

    High abnormal short-sale volume predicts NEGATIVE near-term returns
    (Boehmer/Jones/Zhang-style). Signal per stock = 5-day mean short-volume
    ratio (ShortVolume / TotalVolume) minus that stock's own trailing 60-day
    mean SVR — "abnormal shorting", not level (levels differ structurally
    across stocks). Lagged one day (files publish after the close).

    Portfolio: each week, LONG the 10 least-shorted / SHORT the 10
    most-shorted of the terminal's ~60-name watchlist, equal weight, dollar
    neutral. Costs 5 bps per side on turnover.

Judge: L/S Sharpe over the full span and by year; the long and short legs
separately vs SPY (a short leg that just shorts the market in disguise is not
a signal); decile monotonicity as a sanity check.

    python research/fetch_regsho.py --years 3      # data (once)
    python research/shortvol_edge.py
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REGSHO = os.path.join(HERE, "data", "regsho.csv")
PRICES = os.path.join(HERE, "data", "watchlist_prices.csv")

BASELINE = 60          # trailing own-stock SVR baseline (days) — fixed up front
SIGNAL_D = 5           # smoothing of the recent SVR (days) — fixed up front
N_LEG = 10             # names per leg — fixed up front
COST_BPS = 5.0


def load_regsho():
    df = pd.read_csv(REGSHO)
    df["Date"] = pd.to_datetime(df["Date"], format="%Y%m%d")
    svr = (df.assign(svr=df["ShortVolume"] / df["TotalVolume"])
             .pivot_table(index="Date", columns="Symbol", values="svr"))
    return svr


def load_prices(symbols, start, end):
    if os.path.exists(PRICES):
        px = pd.read_csv(PRICES, index_col=0, parse_dates=True)
        if set(symbols) <= set(px.columns):
            return px
    import yfinance as yf
    raw = yf.download(sorted(set(symbols) | {"SPY"}), start=start, end=end,
                      auto_adjust=True, progress=False)["Close"]
    raw.to_csv(PRICES)
    return raw


def sharpe(r, ppy=252):
    r = np.asarray(r, dtype=float)
    r = r[~np.isnan(r)]
    return float(r.mean() / r.std() * np.sqrt(ppy)) if r.size > 20 and r.std() > 0 else 0.0


def maxdd(r):
    eq = np.cumprod(1 + np.nan_to_num(np.asarray(r, dtype=float)))
    return float((eq / np.maximum.accumulate(eq) - 1).min())


def main():
    svr = load_regsho()
    px = load_prices(list(svr.columns), svr.index.min() - pd.Timedelta(days=10),
                     svr.index.max() + pd.Timedelta(days=5))
    px = px.reindex(svr.index).ffill(limit=3)
    common = [c for c in svr.columns if c in px.columns]
    svr, stock_px = svr[common], px[common]
    print(f"universe {len(common)} names | {svr.index.min().date()} -> "
          f"{svr.index.max().date()} ({len(svr)} days)\n")

    # Abnormal shorting, lagged one day for publication.
    abn = (svr.rolling(SIGNAL_D).mean() - svr.rolling(BASELINE).mean()).shift(1)
    rets = stock_px.pct_change()

    # Weekly rebalance on Mondays (first trading day of each week).
    week = pd.Series(svr.index, index=svr.index).dt.to_period("W")
    is_rebal = week != week.shift(1)

    pos = pd.DataFrame(0.0, index=svr.index, columns=common)
    current = pd.Series(0.0, index=pd.Index(common))
    for t in range(len(svr)):
        if is_rebal.iloc[t]:
            row = abn.iloc[t].dropna()
            if len(row) >= 4 * N_LEG:
                lo = row.nsmallest(N_LEG).index     # least shorted -> long
                hi = row.nlargest(N_LEG).index      # most shorted -> short
                current = pd.Series(0.0, index=pd.Index(common))
                current[lo] = 1.0 / N_LEG
                current[hi] = -1.0 / N_LEG
        pos.iloc[t] = current.values

    pos_lag = pos.shift(1).fillna(0.0)              # earn tomorrow's return
    gross = (pos_lag * rets).sum(axis=1)
    turnover = pos.diff().abs().sum(axis=1).fillna(0.0)
    ls = (gross - turnover * COST_BPS / 1e4).dropna()

    long_leg = (pos_lag.clip(lower=0) * rets).sum(axis=1).reindex(ls.index)
    short_leg = (-pos_lag.clip(upper=0) * rets).sum(axis=1).reindex(ls.index)
    spy = px["SPY"].pct_change().reindex(ls.index)

    eq = np.cumprod(1 + ls.to_numpy())
    ann = eq[-1] ** (252 / len(ls)) - 1
    print(f"  L/S (net)      ann {ann:+7.2%} | Sharpe {sharpe(ls):5.2f} | "
          f"maxDD {maxdd(ls):7.2%} | avg gross 2.0x/{2 * N_LEG} names")
    print(f"  long leg       Sharpe {sharpe(long_leg):5.2f}   vs SPY {sharpe(spy):5.2f}")
    print(f"  short leg (as short) Sharpe {sharpe(-short_leg):5.2f}")

    print("\n  yearly L/S Sharpe:")
    for y, seg in ls.groupby(ls.index.year):
        if len(seg) > 60:
            print(f"    {y}: {sharpe(seg):+.2f}")

    # Decile monotonicity: rank abnormal shorting each rebalance, next-week
    # return per rank bucket. A real signal decays monotonically across ranks.
    print("\n  quintile check (avg next-week return, Q1=least shorted):")
    qrets = {q: [] for q in range(1, 6)}
    rebal_days = svr.index[is_rebal.values]
    for i, d in enumerate(rebal_days[:-1]):
        row = abn.loc[d].dropna()
        if len(row) < 25:
            continue
        nxt = rebal_days[i + 1]
        span = rets.loc[d:nxt].iloc[1:]
        wk = (1 + span).prod() - 1
        labels = pd.qcut(row.rank(method="first"), 5, labels=False)
        for q in range(5):
            names = row.index[labels == q]
            qrets[q + 1].append(wk[names].mean())
    for q in range(1, 6):
        print(f"    Q{q}: {np.nanmean(qrets[q]):+.3%}")

    print("\nVerdict guide: need positive L/S Sharpe, both legs contributing,"
          "\nroughly monotone quintiles, and no single year carrying the result.")


if __name__ == "__main__":
    main()
