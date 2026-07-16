# research/ — edge-hunting on Delta Terminal's feeds

Turning the terminal's free data feeds into *tested* trading hypotheses. The
protocol (learned the hard way in the quant-lab siblings, where it falsified a
crypto stat-arb strategy and validated funding carry):

1. **Pre-register** the hypothesis — rule signs, windows, universe — *before*
   looking at any result. No sweeping, no picking the best of N variants.
2. **Causality audit** — every input lagged by its real publication delay
   plus a safety day.
3. **Real costs** on every position change.
4. **Regime check** — yearly breakdown; one lucky year is not an edge.
5. **Report the result either way.** A dead hypothesis stays documented so it
   isn't quietly re-run until it "works".

## Results so far

| edge | feed source | hypothesis | verdict |
| --- | --- | --- | --- |
| A: macro-liquidity BTC timing (`macro_btc_edge.py`) | `fred.py` | long BTC only when HY spreads tighten / dollar falls / real yields fall (20d, fixed) | **DEAD.** No rule beats buy-and-hold after costs (hold Sharpe 0.78; best rule 0.74). Credit rule shows mild day-selection skill (long-day Sharpe 1.06) but flips sign across years. |
| B: abnormal short-sale volume (`shortvol_edge.py`) | `darkpool.py` (FINRA RegSHO) | long least- / short most-shorted of the 60-name watchlist, weekly | **DEAD.** L/S Sharpe −0.20, quintiles non-monotone, long leg = SPY beta in disguise. The published anomaly is small-cap/daily; it does not survive on mega-caps weekly. |

Data fetchers: `fetch_regsho.py` (FINRA daily short volume → `data/regsho.csv`);
FRED pulled keylessly via `fredgraph.csv` (note: clips to ~3y for some series);
BTC from Coinbase public candles. `data/` is disposable cache.

## In flight

- **Edge C — insider-buy clusters** (`fetch_form4.py` + `insider_edge.py`):
  hypothesis and thresholds pre-registered in `insider_edge.py` and committed
  BEFORE the Form 4 download finished (verifiable in git history). Event:
  officer/director open-market purchases (code P) >= $100k per stock-week;
  measure abnormal (vs SPY) returns at 5/21/63 days with a random-baseline
  sanity check.
- **Options-chain snapshotter** (`snapshot_options.py` + LaunchAgent at
  `~/Library/LaunchAgents/com.conradgarnett.options-snapshot.plist`): free
  chains have no history, so this builds it forward — 20 liquid names, ~6
  expiries, daily at 15:45 ET (~1-3 MB/day). After ~6 months the
  options_mispricing scanner becomes event-testable. Activate with
  `launchctl load ~/Library/LaunchAgents/com.conradgarnett.options-snapshot.plist`.

## Untested candidates (ranked)

1. **SEC EDGAR Form 4 insider-buying clusters** (`sec_edgar.py`) — the
   strongest documented free-data anomaly still standing; needs a
   point-in-time Form 4 parse (real work, ~a day).
2. **GDELT conflict-intensity shocks → oil/gold** (`gdelt.py`) — deep free
   history, but noisy and heavy to download.
3. **Options-mispricing scanner** (`options_mispricing.py`) — live-only chains;
   would need months of forward snapshots before it is backtestable. Start the
   snapshot cron now if this is ever wanted.

## Meta-lesson

The terminal is a superb *data* platform, but edges in free **daily** public
data are mostly arbitraged away — two textbook candidates died on contact with
honest testing. The one live edge found with this protocol so far is the
funding-carry hurdle rule (quant-lab/crypto-funding-carry), which is structural
rather than statistical.
