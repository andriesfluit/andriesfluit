#!/usr/bin/env python3
"""
Sanity-check by re-fetching today's RSS headlines and counting matches for
many names/topics on EXACTLY the same corpus we use for Trump. Tells us
whether Trump is unusually high/low compared to other actors today.
"""
import re
from datetime import date

from fetcher import fetch_all

TERMS = [
    # Politicians (international)
    ("trump",       r"\btrump\b"),
    ("biden",       r"\bbiden\b"),
    ("putin",       r"\b(putin|poetin|poutine)\b"),
    ("zelensky",    r"\bzelensk(y|yi|i)\b"),
    ("macron",      r"\bmacron\b"),
    ("meloni",      r"\bmeloni\b"),
    ("netanyahu",   r"\bnetanyahu\b"),
    ("orban",       r"\borb[aá]n\b"),
    ("xi",          r"\bxi (jinping|jin-ping)\b"),
    # Belgian
    ("de wever",    r"\bde wever\b"),
    ("vooruit",     r"\bvooruit\b"),
    # Tech / culture
    ("musk",        r"\bmusk\b"),
    # Topics (Dutch + French keywords because we search the raw headlines)
    ("klimaat/climat", r"\b(klimaat|climat)\b"),
    ("oekraïne/ukraine", r"\b(oekra[iï]ne|ukraine)\b"),
    ("israël/israel",   r"\b(isra[eë]l)\b"),
    ("gaza",        r"\bgaza\b"),
    ("voetbal/football", r"\b(voetbal|football)\b"),
    # Baselines
    ("belgië/belgique", r"\b(belgi[eë]|belgique)\b"),
    ("brussel/bruxelles", r"\b(brussel|bruxelles)\b"),
    ("europa/europe", r"\beuropa?\b"),
]

PATTERNS = [(label, re.compile(pat, re.IGNORECASE)) for label, pat in TERMS]


def main():
    today = date.today()
    print(f"Fetching today's RSS headlines ({today})...")
    results = fetch_all(today)

    # Same dedupe logic as main.py
    seen = set()
    titles = []
    for src, payload in results.items():
        for url, title in payload["articles"]:
            if url in seen:
                continue
            seen.add(url)
            titles.append(title)

    n = len(titles)
    print(f"\n{n} unique headlines from today.\n")

    rows = []
    for label, pat in PATTERNS:
        matches = [t for t in titles if pat.search(t)]
        pct = round(len(matches) / n * 100, 1) if n else 0
        rows.append((label, len(matches), pct, matches[:2]))

    rows.sort(key=lambda r: r[1], reverse=True)

    print(f"{'Term':<22} {'count':>6} {'share':>7}")
    print("-" * 38)
    for label, c, pct, _ in rows:
        bar = "\u2588" * int(pct)
        print(f"{label:<22} {c:>6} {pct:>6.1f}%  {bar}")

    print(f"\nTop terms with sample headlines:")
    for label, c, pct, samples in rows[:6]:
        if c == 0:
            continue
        print(f"\n  {label} ({c} = {pct}%)")
        for s in samples:
            print(f"    \u2022 {s[:100]}")


if __name__ == "__main__":
    main()
