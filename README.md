# swim-checker

Check lane swimming (baanzwemmen) schedules for Amsterdam-area pools — from the terminal or a browser.

**Live app:** https://swim-checker-amsterdam.streamlit.app/

## Pools covered

| Pool | Location | Data source |
|---|---|---|
| De Mirandabad | Amsterdam Zuid-Oost | Amsterdam zwembaden API |
| Noorderparkbad | Amsterdam Noord | Amsterdam zwembaden API |
| Sportplaza Mercator | Amsterdam West | Sportfondsen Next.js page |
| De Meerkamp | Amstelveen | WordPress REST API / HTML |
| Zuiderbad | Amsterdam Oud-Zuid | Amsterdam zwembaden API |
| Het Marnixbad | Amsterdam Centrum | Zwem Apps WordPress AJAX |

## Setup

```bash
pip install -r requirements.txt
```

## Usage

### CLI

```bash
python check.py              # today
python check.py tomorrow
python check.py 2026-03-01   # YYYY-MM-DD
```

### Web UI

```bash
streamlit run streamlit_app.py   # → http://localhost:8501
```

The web UI offers three views (toggle in the top-right):

| View | Description |
|---|---|
| **Cards** | Pool cards with live/fallback/unavailable badge and time-slot chips |
| **Timeline** | Gantt-style hourly bar chart — one coloured bar per slot per pool |
| **Map** | Interactive map with pool markers; hover for slot summary |

Use the **← Prev / Today / Next →** buttons or date picker to browse days.
Use the **pool filter** (multi-select) to show/hide individual pools across all views.

## How it works

Each pool has a dedicated scraper in `pools/` that tries to fetch the live schedule first. On failure it falls back to a hardcoded weekly schedule (where available). All pools are fetched in parallel and results are cached for 5 minutes.

Source badges indicate data freshness:
- 🟢 **Live** — fetched from the pool's live API/website
- 🟡 **Fallback** — live fetch failed; showing hardcoded weekly schedule
- 🔴 **Unavailable** — no live data and no fallback

## Adding a pool

See [CLAUDE.md](CLAUDE.md) for architecture details, or use the **add-swim-pool** Copilot skill which provides step-by-step guidance and code templates for all common scraping patterns.
