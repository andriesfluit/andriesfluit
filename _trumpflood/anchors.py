#!/usr/bin/env python3
"""External anchors for the trumpflood zone thresholds.

Motivation. calibrate.py derives zone floors as percentiles of Trump's
OWN observed distribution. That is self-referential: if the premise of
the monitor is that Trump coverage is abnormally high, then calibrating
"flooding" as "top 5% of Trump days" quietly redefines the abnormal
level as the baseline. The zones would then only flag variation WITHIN
the anomaly, not the anomaly itself.

This tool computes reference points that are external to Trump's own
distribution, so floors keep meaning something in plain words:

  peers   (offline)  Distribution of daily shares of the 16 OTHER
                     tracked figures (comparators) in the live archive.
                     Anchor: "more attention than any other political
                     figure ever gets" is measurable without reference
                     to Trump's history.

  gdelt   (network)  Median daily share of the SITTING US PRESIDENT in
                     Belgian news during reference windows of ordinary
                     presidencies (Trump-I 2018/2019, Biden 2022/2023),
                     via the GDELT DOC API. Anchor: "N x the attention
                     a US president normally gets". Includes a scale
                     estimate between GDELT shares and our core-corpus
                     shares, derived from the overlap window where both
                     exist. NOTE: GDELT is unreachable from some managed
                     sandboxes; run this on the Actions runner or a
                     normal machine.

Both modes print a report and write validation/anchors_report.json.
This tool NEVER writes thresholds.json: converting anchors into zone
floors is an editorial decision, to be made by a human and recorded in
the thresholds.json notes.

Usage:
    python3 anchors.py peers
    python3 anchors.py gdelt
    python3 anchors.py gdelt --skip-scale     # skip the overlap fetch
"""
import argparse
import json
import statistics
import sys
import time
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
LOG_FILE = ROOT / "data" / "log.json"
REPORT_FILE = ROOT / "validation" / "anchors_report.json"

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
SLEEP_BETWEEN = 8.0  # GDELT rate-limits hard, be nice

# Reference windows of "ordinary presidency" coverage. Spring windows,
# away from elections and inaugurations. The GDELT DOC API reaches back
# to January 2017, so Obama-era windows are not available.
REFERENCE_WINDOWS = [
    ("trump-I-2018",  "trump", "2018-03-01", "2018-05-30"),
    ("trump-I-2019",  "trump", "2019-03-01", "2019-05-30"),
    ("biden-2022",    "biden", "2022-03-01", "2022-05-30"),
    ("biden-2023",    "biden", "2023-03-01", "2023-05-30"),
]


def _load_live_records():
    log = json.loads(LOG_FILE.read_text())
    return [
        r for r in log
        if r.get("core_percentage_name") is not None
        and not r.get("backfilled")
        and r.get("comparisons")
        and r.get("total_articles")
    ]


def _percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    k = max(0, min(len(values) - 1, int(round((p / 100) * (len(values) - 1)))))
    return values[k]


def _summ(values):
    return {
        "n": len(values),
        "median": round(statistics.median(values), 2),
        "mean": round(statistics.mean(values), 2),
        "p95": round(_percentile(values, 95), 2),
        "max": round(max(values), 2),
    }


def _write_report(section, payload):
    REPORT_FILE.parent.mkdir(exist_ok=True)
    report = {}
    if REPORT_FILE.exists():
        try:
            report = json.loads(REPORT_FILE.read_text())
        except json.JSONDecodeError:
            report = {}
    report[section] = payload
    REPORT_FILE.write_text(json.dumps(report, indent=2) + "\n")
    print(f"\nWrote {REPORT_FILE} (section: {section})")


# ---------------------------------------------------------------- peers ---

def run_peers():
    records = _load_live_records()
    if not records:
        sys.exit("No live records with comparator data in data/log.json.")

    per_figure = {}
    best_other_daily = []
    trump_daily = []
    for r in records:
        tot = r["total_articles"]
        for k, v in r["comparisons"].items():
            per_figure.setdefault(k, []).append(v / tot * 100)
        best_other_daily.append(
            max(v / tot * 100 for k, v in r["comparisons"].items() if k != "trump"))
        trump_daily.append(r["comparisons"]["trump"] / tot * 100)

    window = f"{records[0]['date']} .. {records[-1]['date']}"
    print(f"Peer anchor from {len(records)} live days ({window})\n")
    print(f"{'figure':<15}{'median':>9}{'p95':>8}{'max':>8}")
    for k, vals in sorted(per_figure.items(),
                          key=lambda kv: -statistics.median(kv[1])):
        print(f"{k:<15}{statistics.median(vals):>8.2f}%"
              f"{_percentile(vals, 95):>7.2f}%{max(vals):>7.2f}%")

    bo = _summ(best_other_daily)
    tr = _summ(trump_daily)
    days_above_peer_max = sum(1 for t in trump_daily if t > max(best_other_daily))

    print("\nBest NON-Trump figure per day (whoever it is that day):")
    print(f"  median={bo['median']}%  p95={bo['p95']}%  max={bo['max']}%")
    print(f"Trump per day: median={tr['median']}%  p95={tr['p95']}%  max={tr['max']}%")
    print(f"Days Trump exceeded the ALL-TIME max of every other figure: "
          f"{days_above_peer_max}/{len(records)}")

    anchors = {
        "typical_best_peer_day": bo["median"],
        "strong_best_peer_day_p95": bo["p95"],
        "any_peer_ever_max": bo["max"],
    }
    print("\nCandidate externally-anchored pct floors (core-corpus units):")
    print(f"  puddles  >= {anchors['typical_best_peer_day']:.1f}%   "
          f"(matches a typical day's most-covered other politician)")
    print(f"  wet      >= {2 * anchors['typical_best_peer_day']:.1f}%   "
          f"(double a typical top-politician day)")
    print(f"  soaked   >= {anchors['strong_best_peer_day_p95']:.1f}%   "
          f"(matches the p95 best peer day)")
    print(f"  flooding >= {anchors['any_peer_ever_max']:.1f}%   "
          f"(more than ANY other figure got on ANY archived day)")
    print("\nNot written to thresholds.json; adopting these is an editorial call.")

    _write_report("peers", {
        "generated_from": window,
        "days": len(records),
        "best_other_daily": bo,
        "trump_daily": tr,
        "days_trump_above_alltime_peer_max": days_above_peer_max,
        "anchors_pct": anchors,
        "per_figure": {k: _summ(v) for k, v in per_figure.items()},
    })


# ---------------------------------------------------------------- gdelt ---

# GDELT throttles per IP and shared egress IPs (GitHub Actions runners)
# burn through the quota fast: expect 429s and dropped connections from
# the very first request. Long waits are the only thing that helps.
_RETRY_WAITS = [45, 90, 180, 300, 300, 300]


def _fetch_timeline(query, start_iso, end_iso):
    import requests
    params = {
        "query": query,
        "mode": "TimelineVolRaw",
        "format": "json",
        "startdatetime": start_iso.replace("-", "") + "000000",
        "enddatetime": end_iso.replace("-", "") + "235959",
    }
    for attempt, wait in enumerate(_RETRY_WAITS + [None]):
        try:
            r = requests.get(GDELT_URL, params=params, timeout=60)
            if r.status_code == 429:
                if wait is None:
                    r.raise_for_status()
                print(f"    429, waiting {wait}s...", flush=True)
                time.sleep(wait)
                continue
            r.raise_for_status()
            payload = r.json()
            out = {}
            for entry in payload.get("timeline", [{}])[0].get("data", []):
                ts = entry["date"][:8]
                out[f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"] = entry["value"]
            return out
        except Exception as e:
            if wait is None:
                raise
            print(f"    {e.__class__.__name__}: {e}, waiting {wait}s...",
                  flush=True)
            time.sleep(wait)
    return {}


def _window_shares(query, start_iso, end_iso):
    totals = _fetch_timeline("sourcecountry:BE", start_iso, end_iso)
    time.sleep(SLEEP_BETWEEN)
    counts = _fetch_timeline(f"{query} sourcecountry:BE", start_iso, end_iso)
    time.sleep(SLEEP_BETWEEN)
    return {d: counts.get(d, 0) / t * 100 for d, t in totals.items() if t > 0}


def _load_report_section(section):
    if REPORT_FILE.exists():
        try:
            return json.loads(REPORT_FILE.read_text()).get(section) or {}
        except json.JSONDecodeError:
            pass
    return {}


def run_gdelt(skip_scale=False):
    """Resumable: each window is persisted to the report as soon as it is
    fetched, and windows already present in the report are skipped, so a
    rate-limited run can simply be re-run until the report is complete."""
    prior = _load_report_section("gdelt")
    windows = dict(prior.get("reference_windows") or {})
    payload = {"reference_windows": windows}
    payload["gdelt_to_core_scale"] = prior.get("gdelt_to_core_scale")
    payload["scale_window"] = prior.get("scale_window")
    incomplete = []

    print("Reference windows (GDELT, share of Belgian articles mentioning "
          "the sitting US president):\n")
    for label, query, start, end in REFERENCE_WINDOWS:
        if label in windows:
            print(f"  {label}: already in report, skipping")
            continue
        try:
            shares = _window_shares(query, start, end)
        except Exception as e:
            print(f"  {label}: FAILED ({e.__class__.__name__}), "
                  f"re-run later to resume")
            incomplete.append(label)
            continue
        if not shares:
            print(f"  {label}: NO DATA")
            incomplete.append(label)
            continue
        windows[label] = _summ(list(shares.values()))
        w = windows[label]
        print(f"  {label:<14} median={w['median']}%  mean={w['mean']}%  "
              f"p95={w['p95']}%  max={w['max']}%  ({w['n']}d)")
        _write_report("gdelt", payload)

    if not windows:
        _write_report("gdelt", payload)
        sys.exit("No GDELT data retrieved; re-run to try again.")

    normal_median = statistics.median(w["median"] for w in windows.values())
    payload["normal_presidency_median_gdelt"] = round(normal_median, 2)
    print(f"\nNormal-presidency median share (GDELT units, "
          f"{len(windows)}/{len(REFERENCE_WINDOWS)} windows): "
          f"{normal_median:.2f}%")

    scale = payload.get("gdelt_to_core_scale")
    if not skip_scale and scale is None:
        # Estimate the GDELT -> core-corpus conversion on the live window:
        # fetch GDELT's trump share for the same days we have live core
        # shares, and take the median day-by-day ratio.
        records = _load_live_records()
        if records:
            start, end = records[0]["date"], records[-1]["date"]
            print(f"\nEstimating GDELT->core scale on live overlap "
                  f"({start} .. {end})...")
            try:
                gdelt_shares = _window_shares("trump", start, end)
            except Exception as e:
                gdelt_shares = {}
                print(f"  scale estimate FAILED ({e.__class__.__name__}), "
                      f"re-run later to resume")
                incomplete.append("scale")
            ratios = []
            for r in records:
                g = gdelt_shares.get(r["date"])
                if g and g > 0:
                    ratios.append(r["core_percentage_name"] / g)
            if ratios:
                scale = round(statistics.median(ratios), 2)
                payload["gdelt_to_core_scale"] = scale
                payload["scale_window"] = f"{start} .. {end}"
                print(f"  core_share ~= {scale:.2f} x gdelt_share "
                      f"(median of {len(ratios)} daily ratios)")

    if scale:
        core_norm = normal_median * scale
        payload["normal_presidency_median_core_units"] = round(core_norm, 2)
        print(f"\nNormal-presidency median in core-corpus units: "
              f"~{core_norm:.2f}%")
        print("Candidate multiples-of-normal pct floors (core units):")
        for zone, mult in (("puddles", 1), ("wet", 2), ("soaked", 3),
                           ("flooding", 5)):
            print(f"  {zone:<8} >= {core_norm * mult:.1f}%   "
                  f"({mult} x normal presidency)")
    print("\nNot written to thresholds.json; adopting these is an editorial call.")
    _write_report("gdelt", payload)
    if incomplete:
        sys.exit(f"Incomplete ({', '.join(incomplete)}); "
                 f"re-run to resume from the saved report.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("peers", help="offline peer-figure anchor from data/log.json")
    g = sub.add_parser("gdelt", help="historical presidency anchor via GDELT")
    g.add_argument("--skip-scale", action="store_true",
                   help="skip the GDELT->core scale estimation fetch")
    args = ap.parse_args()
    if args.cmd == "peers":
        run_peers()
    else:
        run_gdelt(skip_scale=args.skip_scale)


if __name__ == "__main__":
    main()
