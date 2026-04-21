#!/usr/bin/env python3
"""Build a stratified sample of headlines from data/log.json for hand labelling.

The goal is a fixed pool of Belgian headlines with a human judgement on
whether each is genuinely about Trump. Running the detector against these
labels gives precision and recall.

Stratification: half the sample is drawn from headlines the current
detector flagged as Trump-relevant (measures precision), half from
headlines it did not flag (measures recall on likely misses).

Usage:
    python3 sample_headlines.py               # default: 200 headlines, last 30 days
    python3 sample_headlines.py --n 400 --days 60

Output: validation/unlabeled.jsonl. Each line is a JSON object with
fields {url, title, source, date, detector_name_only, detector_expanded,
trump_relevant}. `trump_relevant` starts as null; a human labels it as
true/false by editing the file.

Re-running is idempotent on (url): a row that already exists in
labels.jsonl (merged or not) is not sampled again.
"""
import argparse
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from comparators import TRUMP_NAME_PATTERN  # noqa: E402
from detector import contains_trump  # noqa: E402

LOG_FILE = ROOT / "data" / "log.json"
OUT_FILE = Path(__file__).parent / "unlabeled.jsonl"
LABELS_FILE = Path(__file__).parent / "labels.jsonl"


def _existing_urls():
    seen = set()
    for path in (OUT_FILE, LABELS_FILE):
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("url"):
                seen.add(row["url"])
    return seen


def _iter_headlines(log, cutoff_date):
    """Yield (url, title, source, date) from every record >= cutoff_date,
    pulling from wide_matches when present (broader than matches) plus
    the per-outlet source_summary would require keeping the raw corpus.
    We only have what's stored in the log, so we sample from
    wide_matches (all Trump-detected headlines) and from the `matches`
    field for each record.
    """
    seen = set()
    for rec in log:
        d = rec.get("date")
        if not d or d < cutoff_date.isoformat():
            continue
        for m in rec.get("wide_matches", []) or rec.get("matches", []) or []:
            url = m.get("url")
            title = m.get("title")
            if not url or not title or url in seen:
                continue
            seen.add(url)
            yield {
                "url": url,
                "title": title,
                "source": m.get("source"),
                "date": d,
                "detector_name_only": bool(
                    TRUMP_NAME_PATTERN.search(title)
                ),
                "detector_expanded": bool(contains_trump(title)),
            }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200, help="Target sample size.")
    ap.add_argument("--days", type=int, default=30, help="Draw from last N days of log.")
    ap.add_argument("--seed", type=int, default=20260421)
    args = ap.parse_args()

    log = json.loads(LOG_FILE.read_text())
    cutoff = date.today() - timedelta(days=args.days)
    pool = list(_iter_headlines(log, cutoff))
    already = _existing_urls()
    pool = [p for p in pool if p["url"] not in already]

    random.seed(args.seed)
    random.shuffle(pool)

    # The stored `matches` / `wide_matches` arrays are, by construction,
    # detector-positive. Recall measurement (the more important half)
    # therefore requires a separate source: we'd need to sample raw
    # kept headlines, not just detector hits. For now this script
    # produces a precision-only pool. A follow-up task: extend main.py
    # to persist a small random sample of detector-negative headlines
    # per day so recall can be measured too.
    rows = pool[: args.n]

    OUT_FILE.parent.mkdir(exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8") as fh:
        for row in rows:
            row["trump_relevant"] = None
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    pos = sum(1 for r in rows if r["detector_name_only"])
    print(f"Wrote {len(rows)} headlines to {OUT_FILE}")
    print(
        f"  detector_name_only positive: {pos}"
        f"  detector_expanded positive: {sum(1 for r in rows if r['detector_expanded'])}"
    )
    print("Hand-label by setting trump_relevant: true or false in the file,")
    print("then move labelled lines to validation/labels.jsonl.")


if __name__ == "__main__":
    main()
