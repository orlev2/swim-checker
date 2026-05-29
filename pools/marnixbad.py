"""
Scrapes Het Marnixbad's lane swimming schedule from the Zwem Apps
WordPress AJAX endpoint used by the FullCalendar widget at /schedule/tijden/.

Discovered by reverse-engineering the FullCalendar JS widget:
  - HTML: <div id="rosterHolder" data-sectionid="8281996b-b3d0-4178-83a7-5586566b24ac">
  - JS makes unauthenticated GET to /wp-admin/admin-ajax.php?action=getlessons

API endpoint:
  GET https://hetmarnix.nl/wp-admin/admin-ajax.php
      ?action=getlessons
      &start=YYYY-MM-DDT00:00:00.000Z   (UTC window start)
      &end=YYYY-MM-DDT00:00:00.000Z     (UTC window end)
      &sectionId=8281996b-b3d0-4178-83a7-5586566b24ac

Returns a JSON array of event objects. Event times are Amsterdam local time
without timezone suffix (e.g. "2026-05-29T12:00:00"). No authentication needed.

Lane swimming: filter by category == "Banen zwemmen".

Fallback: none — schedule changes dynamically.
"""
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import requests

from .base import PoolChecker, Slot

_AJAX_URL: str = "https://hetmarnix.nl/wp-admin/admin-ajax.php"
_SECTION_ID: str = "8281996b-b3d0-4178-83a7-5586566b24ac"
_HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://hetmarnix.nl/schedule/tijden/",
}


class MarnixbadChecker(PoolChecker):
    name = "Het Marnixbad"
    url = "https://hetmarnix.nl/schedule/tijden/"

    # Schedule changes dynamically — no reliable static fallback
    FALLBACK = {}

    def fetch_live(self, d: date) -> Optional[List[Slot]]:
        """Fetch lane swimming slots from the Marnixbad AJAX API for date d.

        The UTC window [d T00:00Z, d+1 T00:00Z] safely covers all Amsterdam
        daytime slots (07:00–22:00 AMS = 05:00–20:00 UTC in summer).
        Event times in the response are Amsterdam local time, so we verify
        the date after parsing to avoid off-by-one issues near midnight.
        """
        params = {
            "action":    "getlessons",
            "start":     f"{d.isoformat()}T00:00:00.000Z",
            "end":       f"{(d + timedelta(days=1)).isoformat()}T00:00:00.000Z",
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
                start_dt = datetime.fromisoformat(ev["start"])
                end_dt   = datetime.fromisoformat(ev["end"])
                if start_dt.date() != d:
                    continue
                slots.append(Slot(start=start_dt.time(), end=end_dt.time()))
            except (KeyError, ValueError):
                pass
        return slots
