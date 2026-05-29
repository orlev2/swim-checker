---
name: add-swim-pool
description: 'Add a new Amsterdam lane-swimming pool to swim-checker. Use when the user wants to track a new pool, asks to add a scraper, or wants to extend the pool list in check.py / streamlit_app.py.'
argument-hint: 'Name of the pool and its schedule URL, e.g. "Flevoparkbad https://www.amsterdam.nl/flevoparkbad/"'
---

# Adding a New Pool to swim-checker

All pool logic lives in `pools/`. The Streamlit UI is `streamlit_app.py`.

---

## Quick checklist

1. **Research** the schedule page → identify the API/scraping approach
2. **Create** `pools/<slug>.py` subclassing `PoolChecker`
3. **Register** the checker in `check.py` and `streamlit_app.py`
4. **Add coordinates** to `_POOL_LOCATIONS` in `streamlit_app.py`
5. **Smoke-test** with `python check.py today`

---

## Step 1 — Research the schedule page

Before writing any code, fetch the target URL and look for:

| Signal | Where to look |
|---|---|
| Amsterdam city pools | Try `https://zwembaden.api-amsterdam.nl/nl/api/<slug>/date/YYYY-MM-DD/` first |
| `__NEXT_DATA__` in `<script>` tag | Next.js SPA — parse embedded JSON |
| WordPress AJAX (`/wp-admin/admin-ajax.php`) | Check page HTML for `data-sectionid` UUID on `#rosterHolder` |
| WordPress REST API | Try `/wp-json/tribe/events/v1/events` or `/wp-json/mec/v1/events` |
| Plain HTML | BeautifulSoup scraping |

**Known pool slugs on the Amsterdam API:**
`de-mirandabad`, `noorderparkbad`, `zuiderbad`, `brediusbad`, `flevoparkbad`

---

## Step 2 — Create the scraper

### Pattern A — Amsterdam zwembaden API (city pools)

```python
"""
Scrapes <PoolName>'s lane swimming schedule from the Amsterdam zwembaden API.
GET https://zwembaden.api-amsterdam.nl/nl/api/<slug>/date/{YYYY-MM-DD}/
Times in Dutch decimal format: "7.00" = 07:00, "21.45" = 21:45.
"""
from datetime import date, time
from typing import List, Optional
import primp
from .base import PoolChecker, Slot

_API_BASE = "https://zwembaden.api-amsterdam.nl/nl/api/<slug>"

def _parse_dutch_time(s: str) -> time:
    h, m = s.strip().split(".")
    return time(int(h), int(m))

class <Name>Checker(PoolChecker):
    name = "<Display Name>"
    url  = "https://www.amsterdam.nl/<slug>/activiteiten/banenzwemmen/"
    FALLBACK = {}   # schedule is date-dynamic; no reliable static fallback

    def fetch_live(self, d: date) -> Optional[List[Slot]]:
        client = primp.Client(impersonate="chrome_120")
        resp = client.get(f"{_API_BASE}/date/{d.isoformat()}/")
        if resp.status_code != 200:
            raise RuntimeError(f"API returned {resp.status_code}")
        slots = []
        for entry in resp.json().get("schedule", []):
            if "banen" not in entry.get("activity", "").lower():
                continue
            try:
                slots.append(Slot(start=_parse_dutch_time(entry["start"]),
                                  end=_parse_dutch_time(entry["end"])))
            except (KeyError, ValueError):
                pass
        return slots
```

### Pattern B — WordPress AJAX / Zwem Apps (e.g. Marnixbad)

```python
"""
Scrapes via Zwem Apps WordPress AJAX endpoint.
Find sectionId in HTML: <div id="rosterHolder" data-sectionid="<UUID>">
Event times are Amsterdam local ISO 8601 (e.g. "2026-06-01T12:00:00").
Filter: category == "Banen zwemmen"
"""
from datetime import date, datetime, timedelta
from typing import List, Optional
import requests
from .base import PoolChecker, Slot

_AJAX_URL   = "https://<domain>/wp-admin/admin-ajax.php"
_SECTION_ID = "<UUID>"
_HEADERS    = {"User-Agent": "Mozilla/5.0", "Referer": "https://<domain>/schedule/"}

class <Name>Checker(PoolChecker):
    name = "<Display Name>"
    url  = "https://<domain>/schedule/"
    FALLBACK = {}

    def fetch_live(self, d: date) -> Optional[List[Slot]]:
        params = {
            "action": "getlessons",
            "start":  f"{d.isoformat()}T00:00:00.000Z",
            "end":    f"{(d + timedelta(days=1)).isoformat()}T00:00:00.000Z",
            "sectionId": _SECTION_ID,
        }
        resp = requests.get(_AJAX_URL, params=params, headers=_HEADERS, timeout=12)
        resp.raise_for_status()
        events = resp.json()
        if not isinstance(events, list):
            return None
        slots = []
        for ev in events:
            if ev.get("category") != "Banen zwemmen":
                continue
            try:
                s = datetime.fromisoformat(ev["start"])
                e = datetime.fromisoformat(ev["end"])
                if s.date() != d:
                    continue
                slots.append(Slot(start=s.time(), end=e.time()))
            except (KeyError, ValueError):
                pass
        return slots
```

### Pattern C — Next.js `__NEXT_DATA__`

See `pools/mercator.py` for the full reference implementation.
Parse `<script id="__NEXT_DATA__">` JSON, recurse into `"timeSlots"` arrays,
filter by activity title containing `"banen"`.

### Fallback schedule (optional)

Add `FALLBACK: Dict[int, List[Tuple[str, str]]]` keyed by `date.weekday()` (0=Mon…6=Sun).
Only add if you have at least a full week of reliable data. Mark the verification date.

---

## Step 3 — Register the checker

**`check.py`:**
```python
from pools.<slug> import <Name>Checker
POOLS = [..., <Name>Checker()]
```

**`streamlit_app.py`** — three places:

```python
# 1. Import
from pools.<slug> import <Name>Checker

# 2. _ALL_POOLS list (order determines card layout and color assignment)
_ALL_POOLS: list[PoolChecker] = [..., <Name>Checker()]

# 3. _POOL_COLORS — add one hex color in the same position
_POOL_COLORS = [..., "#your_hex_color"]

# 4. fetch_all_pools() — add to the pools list inside the function
pools = [..., <Name>Checker()]
```

---

## Step 4 — Add map coordinates

In `streamlit_app.py`, add an entry to `_POOL_LOCATIONS`:

```python
_POOL_LOCATIONS: dict[str, tuple[float, float]] = {
    ...,
    "<Display Name>": (52.XXXX, 4.XXXX),   # (lat, lon)
}
```

Look up coordinates at https://nominatim.openstreetmap.org/search?format=json&q=<street+address>+Amsterdam

---

## Step 5 — Smoke test

```bash
python check.py today
streamlit run streamlit_app.py   # verify Cards, Timeline, and Map views
```

---

## Architecture notes

- `PoolChecker.get_slots(d)` returns `(List[Slot], is_live: bool)`. The base class calls `fetch_live()` and catches all exceptions; if `fetch_live()` returns `None` or raises, it falls back to `FALLBACK`.
- Return an **empty list** `[]` (not `None`) when the API succeeds but there are no slots today.
- Use `primp.Client(impersonate="chrome_120")` for sites with bot protection; use plain `requests` for open APIs.
- The Streamlit cache TTL is 5 minutes (`@st.cache_data(ttl=300)`).
