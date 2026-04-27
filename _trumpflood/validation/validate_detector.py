#!/usr/bin/env python3
"""Compute precision and recall of the Trump detectors against labels.jsonl.

Reads hand-labelled rows from validation/labels.jsonl (each line has a
`trump_relevant` bool) and runs both detectors (name-only and expanded)
against the title. Prints a confusion matrix and precision/recall for
each, plus a list of disagreements between detector and label.

Recall is only meaningful once labels.jsonl contains detector-negative
headlines in addition to detector-positive ones. Until sample_headlines.py
persists detector-negatives (see TODO in that file), the recall number
printed here is precision-biased.

Usage:
    python3 validate_detector.py
    python3 validate_detector.py --show-disagreements
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from comparators import TRUMP_NAME_PATTERN, contains_donald_trump  # noqa: E402
from detector import contains_trump  # noqa: E402

LABELS_FILE = Path(__file__).parent / "labels.jsonl"


def _rate(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    return precision, recall


def _score(rows, predicate):
    tp = fp = fn = tn = 0
    for r in rows:
        label = r.get("trump_relevant")
        if label is None:
            continue
        predicted = bool(predicate(r["title"]))
        if predicted and label:
            tp += 1
        elif predicted and not label:
            fp += 1
        elif not predicted and label:
            fn += 1
        else:
            tn += 1
    return tp, fp, fn, tn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--show-disagreements",
        action="store_true",
        help="Print every headline where detector and label disagree.",
    )
    args = ap.parse_args()

    if not LABELS_FILE.exists():
        sys.exit(f"No labels found at {LABELS_FILE}. Label unlabeled.jsonl first.")

    rows = []
    for line in LABELS_FILE.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    labelled = [r for r in rows if r.get("trump_relevant") is not None]
    print(f"Labelled rows: {len(labelled)} of {len(rows)} total in {LABELS_FILE.name}")
    print()

    for name, predicate in [
        ("name-raw    ", lambda t: TRUMP_NAME_PATTERN.search(t)),
        ("name-donald ", lambda t: contains_donald_trump(t)),
        ("expanded    ", lambda t: contains_trump(t)),
    ]:
        tp, fp, fn, tn = _score(labelled, predicate)
        precision, recall = _rate(tp, fp, fn)
        p_str = f"{precision:.1%}" if precision is not None else "n/a"
        r_str = f"{recall:.1%}" if recall is not None else "n/a"
        print(f"{name}: precision={p_str}  recall={r_str}  (TP={tp} FP={fp} FN={fn} TN={tn})")

    if args.show_disagreements:
        print()
        print("Disagreements (name-donald detector vs label):")
        for r in labelled:
            predicted = bool(contains_donald_trump(r["title"]))
            if predicted != r["trump_relevant"]:
                tag = "FP" if predicted else "FN"
                print(f"  [{tag}] {r.get('date')} {r.get('source')}: {r['title']}")


if __name__ == "__main__":
    main()
