"""
Scrapes Noorderparkbad's lane swimming schedule from the official
Amsterdam zwembaden API: https://zwembaden.api-amsterdam.nl/

Same API pattern as Zuiderbad and De Mirandabad; different pool slug.

API endpoint: GET /nl/api/noorderparkbad/date/{YYYY-MM-DD}/
Returns JSON: {"pool": "...", "schedule": [{"activity", "start", "end", "extra", "dow"}, ...]}
Times are in Dutch decimal format: "7.00", "12.00", "21.45" (dot separator, not colon).

Fallback: none — schedule changes by calendar date (outdoor "Buiten" slots vary
seasonally), no reliable static fallback.
"""
from datetime import date, time
from typing import List, Optional

import primp

from .base import PoolChecker, Slot

_API_BASE: str = "https://zwembaden.api-amsterdam.nl/nl/api/noorderparkbad"


def _parse_dutch_time(s: str) -> time:
    """Parse Dutch decimal time like '7.00' or '21.45' into a time object."""
    h, m = s.strip().split(".")
    return time(int(h), int(m))


class NoorderparkbadChecker(PoolChecker):
    name = "Noorderparkbad"
    url = "https://www.amsterdam.nl/noorderparkbad/activiteiten/banenzwemmen/"

    # Schedule changes by date (indoor + outdoor slots vary) — no static fallback
    FALLBACK = {}

    def fetch_live(self, d: date) -> Optional[List[Slot]]:
        """Fetch the lane swimming schedule from the Amsterdam zwembaden API."""
        client = primp.Client(impersonate="chrome_120")
        resp = client.get(f"{_API_BASE}/date/{d.isoformat()}/")
        if resp.status_code != 200:
            raise RuntimeError(f"API returned {resp.status_code}")
        data = resp.json()
        slots = []
        for entry in data.get("schedule", []):
            if "banen" not in entry.get("activity", "").lower():
                continue
            try:
                slots.append(Slot(
                    start=_parse_dutch_time(entry["start"]),
                    end=_parse_dutch_time(entry["end"]),
                ))
            except (KeyError, ValueError):
                pass
        return slots
