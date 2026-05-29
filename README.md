# swim-checker

Check lane swimming (baanzwemmen) schedules for Amsterdam-area pools — from the terminal or a browser.

**Live app:** https://swim-checker-amsterdam.streamlit.app/

## Pools covered

- De Mirandabad
- Sportplaza Mercator
- De Meerkamp
- Zuiderbad

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

### Web UI (Streamlit)

```bash
streamlit run streamlit_app.py
```

Then open [http://localhost:8501](http://localhost:8501). Use the ← Prev / Today / Next → buttons to browse days.

## How it works

Each pool has a scraper that tries to fetch the live schedule first. If that fails, it falls back to a hardcoded weekly schedule (where available). The web UI fetches all pools in parallel and shows a green/amber/red badge indicating whether the data is live, from the fallback schedule, or unavailable.

## Adding a pool

See [CLAUDE.md](CLAUDE.md).
