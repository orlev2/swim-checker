#!/usr/bin/env python3
"""
Check lane swimming (baanzwemmen) schedules for Amsterdam pools.

Usage:
  python check.py              # today
  python check.py tomorrow     # tomorrow
  python check.py 2026-02-21   # specific date (YYYY-MM-DD)
"""
import argparse
import sys
from datetime import date, timedelta
from typing import List

from pools.base import PoolChecker, Slot
from pools.mirandabad import MirandabadChecker
from pools.mercator import MercatorChecker
from pools.meerkamp import MeerkampChecker
from pools.zuiderbad import ZuiderbadChecker
from pools.noorderparkbad import NoorderparkbadChecker
from pools.marnixbad import MarnixbadChecker

POOLS = [
    MirandabadChecker(), MercatorChecker(), MeerkampChecker(),
    ZuiderbadChecker(), NoorderparkbadChecker(), MarnixbadChecker(),
]
BAR = "─" * 50


def parse_date(s: str) -> date:
    """Parse 'today', 'tomorrow' (or Dutch equivalents), or an ISO date string into a date."""
    if s in ("today", "vandaag"):
        return date.today()
    if s in ("tomorrow", "morgen"):
        return date.today() + timedelta(days=1)
    return date.fromisoformat(s)


def print_result(pool: PoolChecker, d: date, slots: List[Slot], live: bool) -> None:
    """Print a formatted block for one pool's slots to stdout."""
    if live:
        source = "live"
    elif pool.has_fallback:
        source = "fallback schedule — verify at site"
    else:
        source = "could not fetch — check site"

    print(f"\n{BAR}")
    print(f"  {pool.name}")
    print(f"  {d.strftime('%A, %-d %B %Y')}  [{source}]")
    print(f"  {pool.url}")
    print(BAR)

    if slots:
        for s in slots:
            print(f"  ✓  {s}")
    elif live or pool.has_fallback:
        print("  — No lane swimming today")
    else:
        print("  — Schedule unavailable; please check the website above")


def main() -> None:
    """Entry point: parse CLI arguments, fetch slots, and print results."""
    parser = argparse.ArgumentParser(
        description="Check lane swimming schedules for Amsterdam pools.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  python check.py\n  python check.py tomorrow\n  python check.py 2026-03-01",
    )
    parser.add_argument(
        "date",
        nargs="?",
        default="today",
        help="today, tomorrow, or YYYY-MM-DD (default: today)",
    )
    args = parser.parse_args()

    try:
        d = parse_date(args.date)
    except ValueError:
        print(
            f"Error: invalid date '{args.date}'. Use today, tomorrow, or YYYY-MM-DD.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"\nLane swimming — {d.strftime('%A, %-d %B %Y')}")

    for pool in POOLS:
        slots, live = pool.get_slots(d)
        print_result(pool, d, slots, live)

    print()


if __name__ == "__main__":
    main()
