# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

CLI + web UI that fetches lane swimming (baanzwemmen) schedules for Amsterdam-area pools.

**CLI:**
```bash
python check.py              # today
python check.py tomorrow
python check.py 2026-03-01   # YYYY-MM-DD
```

**Web UI:**
```bash
streamlit run streamlit_app.py   # serves on http://localhost:8501
```

## Setup

```bash
pip install -r requirements.txt
```

## Architecture

**`pools/base.py`** defines the base abstractions:
- `Slot` — a dataclass with `start`/`end` as `time` objects
- `PoolChecker` — base class with `fetch_live(d)` (override in subclasses), `FALLBACK` dict (weekday int → list of `("HH:MM", "HH:MM")` tuples), and `get_slots(d)` which tries live first and falls back to `FALLBACK`

**`pools/`** contains one checker per pool, each subclassing `PoolChecker`:
- `mirandabad.py` — hits the official Amsterdam zwembaden JSON API (`zwembaden.api-amsterdam.nl`), uses `primp` for browser impersonation; no static fallback (schedule changes weekly)
- `noorderparkbad.py` — same Amsterdam zwembaden API, different slug (`/noorderparkbad/`); no static fallback (indoor + outdoor slots vary seasonally)
- `mercator.py` — scrapes a Next.js app, parses `__NEXT_DATA__` JSON embedded in the page; has a hardcoded fallback schedule
- `meerkamp.py` — tries WordPress REST API endpoints first, then HTML scraping with BeautifulSoup; has a hardcoded fallback schedule
- `zuiderbad.py` — same Amsterdam zwembaden API, slug `/zuiderbad/`; no static fallback
- `marnixbad.py` — hits the Zwem Apps WordPress AJAX endpoint (`/wp-admin/admin-ajax.php?action=getlessons`) with a fixed `sectionId` UUID; event times are Amsterdam local ISO 8601 without TZ suffix; filters by `category == "Banen zwemmen"`; no static fallback

**`check.py`** imports all checkers, calls `pool.get_slots(d)` for each, and prints formatted results.

**`streamlit_app.py`** is the Streamlit web UI. Features:
- Fetches all 6 pools in parallel via `ThreadPoolExecutor(max_workers=6)`, caches 5 minutes with `@st.cache_data(ttl=300)`
- **Cards view**: 2-column grid of pool cards with source badge (live/fallback/unavailable) and time-slot chips
- **Timeline view**: Altair Gantt chart with hourly x-axis and one row per pool; hover tooltips show exact times
- **Pool filter**: multiselect to show/hide individual pools (persisted in session state)

## Adding a new pool

1. Create `pools/<poolname>.py` subclassing `PoolChecker`
2. Set `name`, `url`, and optionally `FALLBACK`
3. Implement `fetch_live(self, d: date) -> Optional[List[Slot]]` — return `None` on failure (don't raise; base class catches exceptions too)
4. Add an instance to the `POOLS` list in both `check.py` and `streamlit_app.py` (`_ALL_POOLS` and `fetch_all_pools`)

## Notes on scraping

- Mirandabad/Noorderparkbad/Zuiderbad times use Dutch decimal format (`"7.00"`, `"21.45"`) parsed by `_parse_dutch_time()`
- Mercator filters activities by checking if the title contains `"banen"` (Dutch for lane)
- Meerkamp fallback schedule changes seasonally — verify against the site before updating
- Marnixbad UTC window: `[d T00:00Z, d+1 T00:00Z]` safely covers AMS day (earliest slot 07:00 AMS = 05:00 UTC)
- Fallback schedules are keyed by `date.weekday()` (0=Monday, 6=Sunday)
