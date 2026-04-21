#!/usr/bin/env python3
"""Derive zone thresholds from the live archive and write thresholds.json.

The current thresholds (4.0 / 2.5 / 1.5 / 0.8 on share) are round numbers
picked by eye. Once the archive has enough clean name-only history, a
more defensible calibration is to set each zone's floor at a percentile
of the observed distribution, so the name of the zone corresponds to a
stated frequency (for example: Flooding = top 5% of days).

This script reads data/log.json, keeps only records with a valid
`core_percentage_name` (name-only era, live runs), and prints the
implied percentile cutoffs. When --write is passed and enough history
exists, it also writes thresholds.json with the new values and a
metadata block noting the window and generation date.

Usage:
    python3 calibrate.py                    # dry run, print percentiles
    python3 calibrate.py --days 90          # restrict to a window
    python3 calibrate.py --write            # persist to thresholds.json

Percentile choices are configurable via --pcts (default: 95,85,65,35
for flooding/soaked/wet/puddles respectively). Dominance, breadth and
rank floors are retained from the current thresholds.json because they
are corpus-independent and don't benefit from distributional calibration.
"""
import argparse
import json
import statistics
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
LOG_FILE = ROOT / "data" / "log.json"
THRESHOLDS_FILE = ROOT / "thresholds.json"

MIN_DAYS_FOR_WRITE = 30


def _load_records():
    log = json.loads(LOG_FILE.read_text())
    return [
        r for r in log
        if r.get("core_percentage_name") is not None
        and not r.get("backfilled")
    ]


def _percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    k = max(0, min(len(values) - 1, int(round((p / 100) * (len(values) - 1)))))
    return values[k]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=None,
                    help="Restrict the window to the last N days.")
    ap.add_argument("--pcts", type=str, default="95,85,65,35",
                    help="Percentiles for flooding,soaked,wet,puddles.")
    ap.add_argument("--write", action="store_true",
                    help="Persist new values to thresholds.json.")
    args = ap.parse_args()

    records = _load_records()
    if args.days is not None:
        cutoff = (date.today() - timedelta(days=args.days)).isoformat()
        records = [r for r in records if r.get("date", "") >= cutoff]

    if not records:
        sys.exit("No name-only live records available. Run main.py for a while first.")

    pcts = [float(x) for x in args.pcts.split(",")]
    if len(pcts) != 4:
        sys.exit("Expected four percentiles (flooding,soaked,wet,puddles).")

    vals = sorted(r["core_percentage_name"] for r in records)
    n = len(vals)
    window = f"{records[0]['date']} .. {records[-1]['date']}"
    print(f"Records in window: {n}  ({window})")
    print(f"  min={vals[0]}  median={statistics.median(vals)}  max={vals[-1]}")
    print()

    zone_keys = ["flooding", "soaked", "wet", "puddles"]
    new_pct = {k: _percentile(vals, p) for k, p in zip(zone_keys, pcts)}
    for k, p in zip(zone_keys, pcts):
        print(f"  {k:8s}  p{int(p):<2}  floor={new_pct[k]}%")

    if not args.write:
        print()
        print("Dry run. Re-run with --write to persist.")
        return

    if n < MIN_DAYS_FOR_WRITE:
        sys.exit(
            f"Refusing to write thresholds with only {n} days in window; "
            f"need >= {MIN_DAYS_FOR_WRITE}."
        )

    # Retain non-share floors from the existing thresholds.json rather than
    # re-deriving them. Rank and dominance are corpus-independent ratios;
    # breadth is a fraction whose meaning does not drift with the share
    # distribution. Only the `pct` floor is recalibrated here.
    existing = json.loads(THRESHOLDS_FILE.read_text())
    existing_by_key = {z["key"]: z for z in existing.get("zones", [])}
    new_zones = []
    for k in zone_keys:
        base = dict(existing_by_key.get(k, {}))
        base["key"] = k
        base["pct"] = new_pct[k]
        new_zones.append(base)

    payload = {
        "version": f"percentile-{args.pcts.replace(',', '-')}-{date.today().isoformat()}",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": "percentiles of core_percentage_name in live archive",
        "source_window": window,
        "source_days": n,
        "notes": [
            f"Share floors recalibrated as percentiles "
            f"({args.pcts}) of {n} live name-only days.",
            "Rank, dominance and breadth floors retained from the "
            "previous thresholds.json; they are corpus-independent.",
        ],
        "zones": new_zones,
    }
    THRESHOLDS_FILE.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"\nWrote {THRESHOLDS_FILE} ({payload['version']})")


if __name__ == "__main__":
    main()
