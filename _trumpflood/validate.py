#!/usr/bin/env python3
"""
Sanity-check the trumpflood metric by running the same GDELT query for
several other names/topics over the same window and comparing.

For each term, computes:
  - average daily share of Belgian news mentioning the term
  - peak day + peak share
  - number of "active" days (>1% share)
"""
import json
import time
from datetime import date, timedelta
from statistics import mean

import requests

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
SLEEP_BETWEEN = 8.0  # GDELT rate-limits hard, be nice

# NOTE: GDELT translates non-English articles to English before indexing,
# so Dutch/French concept words (klimaat, voetbal, de wever) don't match.
# Use English nouns and proper names (which pass through untranslated).
TERMS = [
    ("trump",            "Trump"),
    ("putin",            "Putin"),
    ("zelensky",         "Zelensky"),
    ("macron",           "Macron"),
    ("netanyahu",        "Netanyahu"),
    ('"de wever"',       "De Wever (Belgian PM)"),
    ("musk",             "Musk"),
    ("climate",          "Climate"),
    ("ukraine",          "Ukraine"),
    ("israel",           "Israel"),
    ("brussels",         "Brussels"),
    ("europe",           "Europe"),
]


def fetch_timeline(query, start, end, retries=4):
    params = {
        "query": query,
        "mode": "TimelineVolRaw",
        "format": "json",
        "startdatetime": start.strftime("%Y%m%d000000"),
        "enddatetime": end.strftime("%Y%m%d235959"),
    }
    for attempt in range(retries):
        try:
            r = requests.get(GDELT_URL, params=params, timeout=60)
            if r.status_code == 429:
                wait = 30 * (attempt + 1)
                print(f"    429, waiting {wait}s...", flush=True)
                time.sleep(wait)
                continue
            r.raise_for_status()
            payload = r.json()
            out = {}
            for entry in payload.get("timeline", [{}])[0].get("data", []):
                ts = entry["date"][:8]
                iso = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
                out[iso] = entry["value"]
            return out
        except requests.exceptions.HTTPError as e:
            if attempt < retries - 1:
                wait = 15 * (attempt + 1)
                print(f"    {e.__class__.__name__}, waiting {wait}s...", flush=True)
                time.sleep(wait)
            else:
                raise
        except Exception as e:
            if attempt < retries - 1:
                wait = 15 * (attempt + 1)
                print(f"    {e.__class__.__name__}: {e}, waiting {wait}s...", flush=True)
                time.sleep(wait)
            else:
                raise
    return {}


def main():
    today = date.today()
    end = today - timedelta(days=1)
    start = end - timedelta(days=29)

    print(f"Comparing {len(TERMS)} terms across Belgian news, {start} \u2192 {end}\n")
    print("Fetching denominator (all BE articles per day)...")
    totals = fetch_timeline("sourcecountry:BE", start, end)

    rows = []
    for query, label in TERMS:
        full_query = f"{query} sourcecountry:BE"
        for attempt in range(3):
            try:
                counts = fetch_timeline(full_query, start, end)
                break
            except Exception as e:
                wait = (attempt + 1) * 8
                if attempt < 2:
                    print(f"  {label}: retry after {wait}s ({e.__class__.__name__})")
                    time.sleep(wait)
                else:
                    print(f"  {label}: GIVE UP ({e})")
                    counts = None
        if counts is None:
            continue
        shares = []
        peak_day = None
        peak_share = 0.0
        active_days = 0
        for iso, total in totals.items():
            if total == 0:
                continue
            num = counts.get(iso, 0)
            share = num / total * 100
            shares.append(share)
            if share > peak_share:
                peak_share = share
                peak_day = iso
            if share > 1.0:
                active_days += 1
        avg = mean(shares) if shares else 0
        rows.append((label, avg, peak_share, peak_day or "-", active_days, sum(counts.values())))
        print(f"  {label:<24} avg={avg:>5.2f}%  peak={peak_share:>5.2f}% on {peak_day}  active={active_days}/{len(shares)}d  total={sum(counts.values())}")
        time.sleep(SLEEP_BETWEEN)

    rows.sort(key=lambda r: r[1], reverse=True)
    print("\n=== Sorted by average daily share ===\n")
    print(f"{'Term':<24} {'avg':>6} {'peak':>6}  {'peak day':<12} {'active':>7} {'total arts':>10}")
    print("-" * 78)
    for label, avg, peak, peak_day, active, total in rows:
        print(f"{label:<24} {avg:>5.2f}% {peak:>5.2f}%  {peak_day:<12} {active:>4}d   {total:>10}")


if __name__ == "__main__":
    main()
