# Delta Terminal

**An open-source markets & world-data terminal — built entirely from free, public APIs.**

A professional-style data terminal you can actually run for free: a FastAPI
backend aggregates **~48 live data feeds** — markets, crypto, macro, plus
real-world data like aircraft, ships, weather, earthquakes, and conflicts — and
serves them as REST + WebSocket. A panel-based web UI (and an Electron desktop
app) render it all as a live terminal. No paid subscriptions, no data vendor.

<!-- Add a screenshot/GIF here — it's the most important part of this README:
![Delta Terminal](docs/screenshot.png)
-->
> 📸 **Add a screenshot or GIF of the terminal running at the top of this README** —
> it's the first thing visitors see and the biggest driver of interest.

## Why

Professional data terminals cost tens of thousands a year. Almost everything they
show is available through free public APIs if you aggregate and normalize it
yourself. Delta Terminal does exactly that, in one screen.

## Features

- **~48 data feeds** across markets and the wider world (all free/public).
- **FastAPI backend** — every feed exposed at `/api/...` as JSON, plus a live
  **WebSocket** stream.
- **Panel UI** — a terminal-style React/JSX frontend (shell, panels, maps,
  options, 3-D order flow).
- **Electron desktop app** — launches the backend and wraps the UI as a native app.
- **Graceful degradation** — a rate-limited or down feed is skipped, not fatal.

### Data feeds (a sample of the ~48)

- **Markets & finance** — equities, crypto, bonds, forex, FRED macro, options
  flow, dark pool, earnings, economic calendar, SEC EDGAR filings, energy (EIA).
- **Geospatial & physical** — live aircraft, ships, satellites, space weather,
  weather, earthquakes, wildfires, ocean/climate data, public cameras.
- **Geopolitics & society** — conflicts, sanctions, elections, refugee (UNHCR)
  and health (WHO) data, population, trade.
- **Tech & information** — CVEs, Cloudflare/outage status, arXiv, Hacker News,
  clinical trials, news.

## Quick start

```bash
# backend — serves http://localhost:8000
pip install -r requirements.txt
python server.py

# desktop app (spawns the backend automatically)
cd delta-terminal-app
npm install
npm start
```

Then open <http://localhost:8000> in a browser, or use the Electron app.

## Tech stack

FastAPI + WebSockets (backend) · React/JSX panels (frontend) · Electron (desktop)
· ~48 self-contained feed modules in `feeds/`.

## Notes

- **API keys are optional** — most feeds are fully key-less. Any keys go in a
  local `.env` (never committed).
- **Free APIs are fragile** — sources change and rate-limit; feeds degrade
  gracefully, but expect to occasionally update a feed module.
- `prototyping/` holds earlier iterations (Textual TUI, pywebview) kept for
  reference; the current app is `server.py` + `static/delta/` + `delta-terminal-app/`.

## License

MIT — see [LICENSE](LICENSE).
