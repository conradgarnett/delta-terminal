#!/usr/bin/env python3
"""
Edge A — macro-liquidity BTC timing, built on the terminal's FRED feed sources.

PRE-REGISTERED HYPOTHESES (declared before any results were seen; no parameter
was fitted or swept — the 20-day window and the rule signs were fixed up front
from the standard macro-liquidity story):

    A1  HY credit:  long BTC when the high-yield OAS (BAMLH0A0HYM2) has
                    TIGHTENED over the last 20 business days, else flat.
                    (Spreads widening = risk-off = bad for the most
                    liquidity-sensitive asset there is.)
    A2  Dollar:     long BTC when the broad dollar index (DTWEXBGS) has
                    FALLEN over the last 20 business days, else flat.
    A3  Real yield: long BTC when the 10y TIPS yield (DFII10) has FALLEN
                    over the last 20 business days, else flat.
    A4  Composite:  long BTC when at least 2 of A1-A3 agree, else flat.

Causality: every FRED series is shifted by its publication lag plus one extra
business day (HY OAS and TIPS publish next-day -> lag 2bd; the broad dollar
index publishes weekly with a lag -> lag 5bd). Signals are then forward-filled
onto BTC's 7-day calendar, and a position formed at close t earns the close
t -> t+1 return. Costs: 10 bps per position change.

Judge: full-period AND yearly Sharpe vs buy-and-hold, plus a risk-matched view
(rule return when in the market vs BTC's same-days return). A timing rule
earns its keep only if it beats holding through — after costs, out of sample,
and not just in one regime.

    python research/macro_btc_edge.py
"""

from __future__ import annotations

import io
import os
import sys
import time

import numpy as np
import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"
SERIES = {                       # id -> (name, publication lag in business days)
    "BAMLH0A0HYM2": ("hy_oas", 2),
    "DTWEXBGS": ("dollar", 5),
    "DFII10": ("real_10y", 2),
}
LOOKBACK = 20                    # fixed up front; deliberately not swept
COST_BPS = 10.0


def fred_series(sid, start="2015-01-01"):
    r = requests.get(FRED_CSV, params={"id": sid, "cosd": start}, timeout=30)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text), na_values=".")
    df.columns = ["date", sid]
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")[sid].dropna()


def btc_history(days=2600):
    """Coinbase daily BTC-USD closes (free, keyless), paged 300 candles/call."""
    url = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
    sess = requests.Session()
    sess.headers.update({"User-Agent": "delta-terminal-research/0.1"})
    end = pd.Timestamp.utcnow().floor("D")
    start = end - pd.Timedelta(days=days)
    rows, cur = [], end
    while cur > start:
        lo = max(start, cur - pd.Timedelta(days=300))
        r = sess.get(url, params={"granularity": 86400,
                                  "start": lo.isoformat(), "end": cur.isoformat()},
                     timeout=20)
        if r.ok:
            rows.extend(r.json())
        cur = lo
        time.sleep(0.15)
    idx = pd.to_datetime([int(x[0]) for x in rows], unit="s", utc=True)
    ser = pd.Series([float(x[4]) for x in rows], index=idx, name="btc")
    return ser[~ser.index.duplicated()].sort_index().tz_localize(None)


def stats(r, ppy=365):
    r = np.asarray(r, dtype=float)
    r = r[~np.isnan(r)]
    if r.size < 30:
        return 0.0, 0.0, 0.0
    eq = np.cumprod(1 + r)
    ann = eq[-1] ** (ppy / len(r)) - 1
    sh = r.mean() / r.std() * np.sqrt(ppy) if r.std() > 0 else 0.0
    peak = np.maximum.accumulate(eq)
    return float(ann), float(sh), float((eq / peak - 1).min())


def main():
    print("fetching FRED series + BTC history...")
    macro = {}
    for sid, (name, lag) in SERIES.items():
        s = fred_series(sid)
        macro[name] = s.shift(lag)          # publication lag + safety, in bdays
        print(f"  {name:9s} {sid:14s} {s.index.min().date()} -> {s.index.max().date()} "
              f"({len(s)} obs, lagged {lag}bd)")
    btc = btc_history()
    print(f"  btc       Coinbase       {btc.index.min().date()} -> {btc.index.max().date()} "
          f"({len(btc)} days)\n")

    # Signals on the business-day calendar, then ffill onto BTC's 7-day calendar.
    sig_bd = pd.DataFrame({
        "A1_credit": (macro["hy_oas"].diff(LOOKBACK) < 0).astype(float),
        "A2_dollar": (macro["dollar"].diff(LOOKBACK) < 0).astype(float),
        "A3_realyld": (macro["real_10y"].diff(LOOKBACK) < 0).astype(float),
    })
    sig = sig_bd.reindex(btc.index).ffill().dropna()
    sig["A4_majority"] = (sig.sum(axis=1) >= 2).astype(float)

    px = btc.reindex(sig.index)
    fwd = px.pct_change().shift(-1)          # position at close t earns t -> t+1

    print(f"test window: {sig.index.min().date()} -> {sig.index.max().date()} "
          f"({len(sig)} days)\n")
    hold_ann, hold_sh, hold_dd = stats(fwd)
    print(f"  {'buy & hold BTC':14s} ann {hold_ann:+8.1%} | Sharpe {hold_sh:5.2f} | "
          f"maxDD {hold_dd:7.1%} | exposure 100%")

    rows = []
    for col in sig.columns:
        pos = sig[col]
        ret = pos * fwd - pos.diff().abs().fillna(0) * COST_BPS / 1e4
        ann, sh, dd = stats(ret.dropna())
        expo = float(pos.mean())
        # Risk-matched: BTC's own Sharpe measured ONLY on the days the rule
        # was long — did the rule pick better-than-average days?
        in_days = fwd[pos == 1].dropna()
        _, sh_in, _ = stats(in_days)
        rows.append((col, ann, sh, dd, expo, sh_in))
        print(f"  {col:14s} ann {ann:+8.1%} | Sharpe {sh:5.2f} | maxDD {dd:7.1%} | "
              f"exposure {expo:4.0%} | BTC-Sharpe on long days {sh_in:5.2f}")

    print("\n  yearly Sharpe (rule vs hold):")
    years = sorted(set(sig.index.year))
    header = "    year   hold " + " ".join(f"{c[:9]:>10s}" for c in sig.columns)
    print(header)
    for y in years:
        m = sig.index.year == y
        if m.sum() < 90:
            continue
        _, hs, _ = stats(fwd[m].dropna())
        line = f"    {y}  {hs:5.2f} "
        for col in sig.columns:
            pos = sig[col][m]
            ret = (pos * fwd[m] - pos.diff().abs().fillna(0) * COST_BPS / 1e4).dropna()
            _, s_, _ = stats(ret)
            line += f" {s_:9.2f} "
        print(line)

    print("\nVerdict guide: a rule only matters if its Sharpe beats hold AND its"
          "\n'BTC-Sharpe on long days' beats the unconditional hold Sharpe AND the"
          "\nyearly rows don't show one lucky regime carrying everything.")


if __name__ == "__main__":
    main()
