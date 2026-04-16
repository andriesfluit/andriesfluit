#!/usr/bin/env python3
"""
Retroactive backfill of trumpflood data using GDELT 2.0.

GDELT 2.0 indexes the world's news every 15 minutes since 2015, with country
and language tags. We use its DOC API in TimelineVolRaw mode to get, for each
day in a range:

  - the number of articles from Belgian sources mentioning "trump"
  - the number of articles from Belgian sources total

The ratio is the daily Trump-mention rate. Free, no auth, no rate limits beyond
courtesy. Two HTTP calls cover any date range (one per query).

Caveat: GDELT samples a much broader universe of Belgian news outlets than our
five RSS feeds, so historical GDELT-derived percentages are NOT directly
comparable to the RSS-based "today" number. Backfilled records are tagged
source="gdelt" so the site can style them differently.

Usage:
  python3 backfill.py --days 30
  python3 backfill.py --from 2026-01-01 --to 2026-04-14
  python3 backfill.py --days 90 --skip-existing
"""
import argparse
import json
from datetime import date, timedelta
from pathlib import Path

import requests

from assessor import assess_pct_based
from site_gen import render as render_site

ROOT = Path(__file__).parent
LOG_FILE = ROOT / "data" / "log.json"

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

# Backfilled records use pct-based assessment (no theme data available
# from GDELT). Live records in main.py use rank-based assessment.


def fetch_timeline(query, start, end):
    """Return {date_iso: count} for the given GDELT query and date range."""
    params = {
        "query": query,
        "mode": "TimelineVolRaw",
        "format": "json",
        "startdatetime": start.strftime("%Y%m%d000000"),
        "enddatetime": end.strftime("%Y%m%d235959"),
    }
    r = requests.get(GDELT_URL, params=params, timeout=60)
    r.raise_for_status()
    payload = r.json()
    out = {}
    for entry in payload.get("timeline", [{}])[0].get("data", []):
        ts = entry["date"][:8]
        iso = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
        out[iso] = entry["value"]
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--days", type=int, default=30,
                   help="Backfill the last N days (excluding today). Default: 30.")
    p.add_argument("--from", dest="frm", help="Inclusive start date YYYY-MM-DD.")
    p.add_argument("--to", dest="to", help="Inclusive end date YYYY-MM-DD.")
    p.add_argument("--skip-existing", action="store_true",
                   help="Skip dates already in log.json.")
    p.add_argument("--no-render", action="store_true",
                   help="Skip regenerating the HTML site.")
    args = p.parse_args()

    today = date.today()
    if args.frm and args.to:
        start = date.fromisoformat(args.frm)
        end = date.fromisoformat(args.to)
    else:
        end = today - timedelta(days=1)
        start = end - timedelta(days=args.days - 1)

    if start > end:
        print("Empty range, nothing to do.")
        return

    print(f"Querying GDELT: {start} \u2192 {end}")
    print("  trump articles in BE...", end=" ", flush=True)
    trump_counts = fetch_timeline("trump sourcecountry:BE", start, end)
    print(f"({len(trump_counts)} days)")
    print("  total BE articles...", end=" ", flush=True)
    total_counts = fetch_timeline("sourcecountry:BE", start, end)
    print(f"({len(total_counts)} days)")

    # Load existing log.
    log = []
    if LOG_FILE.exists():
        try:
            data = json.loads(LOG_FILE.read_text())
            log = data if isinstance(data, list) else [data]
        except json.JSONDecodeError:
            log = []
    existing_dates = {r["date"] for r in log if not r.get("backfilled")}

    # Build backfill records.
    print()
    new_records = []
    d = start
    while d <= end:
        iso = d.isoformat()
        if args.skip_existing and iso in {r["date"] for r in log}:
            print(f"  {iso}  (skip, already in log)")
            d += timedelta(days=1)
            continue

        # Don't overwrite live RSS records, only backfill missing dates.
        if iso in existing_dates:
            print(f"  {iso}  (skip, live RSS record exists)")
            d += timedelta(days=1)
            continue

        total = total_counts.get(iso, 0)
        trump = trump_counts.get(iso, 0)
        if total == 0:
            print(f"  {iso}  no GDELT data")
            d += timedelta(days=1)
            continue

        pct = round(trump / total * 100, 1)
        a = assess_pct_based(trump, total)
        record = {
            "date": iso,
            "total_articles": total,
            "trump_articles": trump,
            "percentage": pct,
            "zone": a["zone"],
            "label": a["label"],
            "narrative": a["narrative"],
            "rank": None,
            "n_themes": None,
            "assessment_method": a["method"],
            "sources": {"gdelt": {"fetched": total, "today": total}},
            "matches": [],
            "backfilled": True,
            "source": "gdelt",
        }
        new_records.append(record)
        print(f"  {iso}  {trump:>3}/{total:<4} = {pct:>5.1f}%  {record['label']}")
        d += timedelta(days=1)

    # Upsert.
    keep = {r["date"] for r in new_records}
    log = [r for r in log if r["date"] not in keep]
    log.extend(new_records)
    log.sort(key=lambda r: r["date"])
    LOG_FILE.write_text(json.dumps(log, indent=2, ensure_ascii=False))

    print(f"\nWrote {len(new_records)} backfilled records to {LOG_FILE}")

    if not args.no_render:
        render_site()
        print("Site regenerated.")


if __name__ == "__main__":
    main()
