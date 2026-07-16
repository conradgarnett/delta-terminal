#!/usr/bin/env python3
"""
Fetch SEC EDGAR Form 4 (insider transaction) filings for the terminal's
watchlist — the sec_edgar feed's source, turned into a research dataset.

For each company: list Form 4 filings via the submissions API, download each
filing's XML, and extract every non-derivative transaction (code, date,
shares, price, insider role). The edge test (insider_edge.py) uses only
open-market purchases (code P), but all codes are stored for context.

SEC fair-use: descriptive User-Agent, <=8 req/s. ~60 mega-caps x ~3y of
filings ≈ tens of thousands of documents — expect roughly an hour.

    python research/fetch_form4.py --years 3
Output: research/data/form4_transactions.csv
"""

from __future__ import annotations

import argparse
import os
import time
import xml.etree.ElementTree as ET

import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "Conrad Garnett research conrad.j.garnett@gmail.com"}

WATCHLIST = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA", "AMD", "AVGO", "ORCL",
    "CRM", "ADBE", "INTC", "QCOM", "NFLX", "UBER", "ABNB", "SNAP", "PINS", "RBLX",
    "JPM", "GS", "BAC", "MS", "V", "MA", "BRK-B", "AXP", "BLK", "SCHW",
    "UNH", "LLY", "JNJ", "PFE", "MRK", "ABBV", "BMY", "AMGN", "GILD", "CVS",
    "XOM", "CVX", "COP", "NEE", "GE", "CAT", "BA", "LMT", "RTX", "HON",
    "COST", "WMT", "HD", "TGT", "NKE", "MCD", "SBUX", "DIS", "CMCSA", "T",
]

_S = requests.Session()
_S.headers.update(UA)


def _get(url, **kw):
    r = _S.get(url, timeout=30, **kw)
    time.sleep(0.13)                       # ~8 req/s, inside SEC fair-use
    r.raise_for_status()
    return r


def cik_map():
    d = _get("https://www.sec.gov/files/company_tickers.json").json()
    return {row["ticker"].upper(): int(row["cik_str"]) for row in d.values()}


def _txt(node, path):
    el = node.find(path)
    return el.text.strip() if el is not None and el.text else None


def parse_form4(xml_bytes):
    """Extract non-derivative transactions from one Form 4 XML."""
    root = ET.fromstring(xml_bytes)
    rel = root.find(".//reportingOwnerRelationship")
    is_officer = _txt(rel, "isOfficer") in ("1", "true") if rel is not None else False
    is_director = _txt(rel, "isDirector") in ("1", "true") if rel is not None else False
    rows = []
    for tx in root.findall(".//nonDerivativeTransaction"):
        code = _txt(tx, ".//transactionCoding/transactionCode")
        shares = _txt(tx, ".//transactionAmounts/transactionShares/value")
        price = _txt(tx, ".//transactionAmounts/transactionPricePerShare/value")
        ad = _txt(tx, ".//transactionAmounts/transactionAcquiredDisposedCode/value")
        tdate = _txt(tx, ".//transactionDate/value")
        if code and shares:
            rows.append({
                "code": code, "acq_disp": ad, "tx_date": tdate,
                "shares": float(shares), "price": float(price) if price else None,
                "is_officer": is_officer, "is_director": is_director,
            })
    return rows


def filings_for(cik, years):
    """(filing_date, accession, primary_doc) for Form 4s within the window.
    The submissions API's `recent` block covers ~1000 filings; older pages are
    fetched only if the window isn't yet covered."""
    cutoff = (pd.Timestamp.now() - pd.Timedelta(days=int(years * 365.25))).date()
    base = _get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json").json()
    out = []

    def harvest(block):
        forms = block["form"]
        for i in range(len(forms)):
            if forms[i] != "4":
                continue
            fdate = pd.Timestamp(block["filingDate"][i]).date()
            if fdate < cutoff:
                continue
            out.append((fdate, block["accessionNumber"][i],
                        block["primaryDocument"][i]))

    recent = base["filings"]["recent"]
    harvest(recent)
    oldest_recent = pd.Timestamp(recent["filingDate"][-1]).date() if recent["filingDate"] else cutoff
    if oldest_recent > cutoff:
        for extra in base["filings"].get("files", []):
            if pd.Timestamp(extra["filingTo"]).date() < cutoff:
                continue
            harvest(_get(f"https://data.sec.gov/submissions/{extra['name']}").json())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=float, default=3.0)
    args = ap.parse_args()

    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    ciks = cik_map()
    all_rows = []
    for ticker in WATCHLIST:
        cik = ciks.get(ticker.replace("-", "."))or ciks.get(ticker)
        if not cik:
            print(f"{ticker}: no CIK — skipped", flush=True)
            continue
        try:
            filings = filings_for(cik, args.years)
        except Exception as e:  # noqa: BLE001
            print(f"{ticker}: submissions FAILED {type(e).__name__}: {e}", flush=True)
            continue
        n_tx = 0
        for fdate, accession, doc in filings:
            doc = doc.split("/")[-1]           # strip any xsl viewer prefix
            url = (f"https://www.sec.gov/Archives/edgar/data/{cik}/"
                   f"{accession.replace('-', '')}/{doc}")
            try:
                for row in parse_form4(_get(url).content):
                    row.update({"ticker": ticker, "filing_date": str(fdate)})
                    all_rows.append(row)
                    n_tx += 1
            except Exception:                  # malformed/paper filings: skip
                continue
        print(f"{ticker}: {len(filings)} Form 4s -> {n_tx} transactions", flush=True)

    df = pd.DataFrame(all_rows)
    path = os.path.join(HERE, "data", "form4_transactions.csv")
    df.to_csv(path, index=False)
    n_p = int((df["code"] == "P").sum()) if len(df) else 0
    print(f"\nwrote {path}: {len(df)} transactions, {n_p} open-market purchases (code P)")


if __name__ == "__main__":
    main()
