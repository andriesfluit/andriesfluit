#!/usr/bin/env python3
import json
import logging
import statistics
from datetime import date, datetime
from pathlib import Path
try:
    from zoneinfo import ZoneInfo          # Python 3.9+
except ImportError:                         # pragma: no cover - fallback
    ZoneInfo = None  # type: ignore

from assessor import assess_composite, assess_rank_based
from comparators import count_matches as count_comparators
from detector import contains_trump
from fetcher import CORE_FEED_KEYS, fetch_all
from image_gen import generate_image
from site_gen import render as render_site
from themes import count_matches as count_themes

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
# Write the generated site into the repo-root sibling folder so GitHub Pages
# serves it directly at andriesfluit.be/trumpflood/.
OUTPUT_DIR = ROOT.parent / "trumpflood"
LOG_FILE = DATA_DIR / "log.json"

# NOTE: pct-based labels are now assigned in assessor.py (see assess_pct_based).
# main.py uses assess_rank_based which combines rank and share for sharper
# zone classification.


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    today = date.today()
    DATA_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    results = fetch_all(today)

    seen = set()
    kept = []  # list of (url, title, source)
    source_summary = {}
    for src, payload in results.items():
        n_today = len(payload["articles"])
        # Per-outlet Trump count (BEFORE dedup, so each outlet's own rate
        # is independent of overlap with others).
        outlet_trump = sum(
            1 for _, t in payload["articles"] if contains_trump(t)
        )
        for url, title in payload["articles"]:
            if url in seen:
                continue
            seen.add(url)
            kept.append((url, title, src))
        source_summary[src] = {
            "fetched": payload["fetched"],
            "today": n_today,
            "trump": outlet_trump,
            "share": round(outlet_trump / n_today * 100, 2) if n_today else 0,
        }

    # ------ Full "wide" corpus (every feed, deduped by URL) -----------------
    wide_total = len(kept)
    wide_matched = [
        {"title": t, "url": u, "source": s}
        for u, t, s in kept
        if contains_trump(t)
    ]
    wide_trump = len(wide_matched)
    wide_pct = round((wide_trump / wide_total * 100), 1) if wide_total else 0.0

    wide_titles = [t for _, t, _ in kept]
    wide_comparisons = count_comparators(wide_titles)
    wide_themes = count_themes(wide_titles)

    # ------ "Core" corpus: national + regional-generalist outlets only ------
    core_kept = [(u, t, s) for u, t, s in kept if s in CORE_FEED_KEYS]
    core_total = len(core_kept)
    core_matched = [
        {"title": t, "url": u, "source": s}
        for u, t, s in core_kept
        if contains_trump(t)
    ]
    core_trump = len(core_matched)
    core_pct = round((core_trump / core_total * 100), 1) if core_total else 0.0

    core_titles = [t for _, t, _ in core_kept]
    core_comparisons = count_comparators(core_titles)
    core_themes = count_themes(core_titles)

    # ------ 7-day rolling average of core percentage (smoothing) ------------
    # Read existing log to compute trailing window. Only use records that
    # carry a core percentage (live days, not GDELT backfills).
    existing_log = []
    if LOG_FILE.exists():
        try:
            data = json.loads(LOG_FILE.read_text())
            existing_log = data if isinstance(data, list) else [data]
        except json.JSONDecodeError:
            existing_log = []
    prior_core = [
        r.get("core_percentage")
        for r in existing_log
        if r.get("date") != today.isoformat()
        and r.get("core_percentage") is not None
    ]
    recent_core = prior_core[-6:]  # last 6 days (exclusive of today)
    window = recent_core + [core_pct]
    smoothed_pct = round(sum(window) / len(window), 2) if window else None

    # ------ Breadth: fraction of core outlets carrying any Trump story -----
    # Only outlets with a reasonable number of stories today count toward
    # the denominator (a feed that returned 2 articles should not drag
    # breadth either way).
    core_outlets = {
        s: info for s, info in source_summary.items() if s in CORE_FEED_KEYS
    }
    active_core = [info for info in core_outlets.values() if info["today"] >= 5]
    if active_core:
        outlets_with_trump = sum(1 for info in active_core if info["trump"] > 0)
        breadth = outlets_with_trump / len(active_core)
    else:
        breadth = None

    # ------ Deviation: today's core share vs 14-day median of prior days ---
    prior14 = [p for p in prior_core[-14:] if p is not None]
    if len(prior14) >= 7:
        med = statistics.median(prior14)
        deviation = (core_pct / med) if med > 0 else None
    else:
        deviation = None

    assessment = assess_composite(
        core_trump, core_total, core_comparisons,
        breadth=breadth, deviation=deviation, smoothed_pct=smoothed_pct,
    )
    # Keep the old theme rank as context (not used for the zone anymore).
    theme_rank_ctx = assess_rank_based(core_trump, core_total, core_themes)

    # Macro-average (each outlet weighed equally). Kept as a background
    # cross-check, computed on the full per-outlet summary.
    qualifying = [s for s in source_summary.values() if s["today"] >= 10]
    macro_share = (
        round(sum(s["share"] for s in qualifying) / len(qualifying), 1)
        if qualifying else 0.0
    )

    # Capture when this analysis ran. Stored in the record so the site can
    # display the last-run timestamp unambiguously.
    if ZoneInfo is not None:
        generated_at = datetime.now(ZoneInfo("Europe/Brussels")).isoformat(timespec="seconds")
    else:
        generated_at = datetime.now().astimezone().isoformat(timespec="seconds")

    record = {
        "date": today.isoformat(),
        "generated_at": generated_at,
        # Headline numbers = CORE tier.
        "total_articles": core_total,
        "trump_articles": core_trump,
        "percentage": core_pct,
        "core_percentage": core_pct,
        # Wide tier kept as cross-check.
        "wide_total_articles": wide_total,
        "wide_trump_articles": wide_trump,
        "wide_percentage": wide_pct,
        # Outlet-equal sanity check.
        "macro_percentage": macro_share,
        "qualifying_outlets": len(qualifying),
        # Zone comes from people-rank classifier on the core corpus.
        "zone": assessment["zone"],
        "label": assessment["label"],
        "narrative": assessment["narrative"],
        "rank": assessment["rank"],              # rank AMONG PEOPLE (1..10)
        "n_people": assessment["n_people"],
        "dominance": assessment["dominance"],     # trump / sum(others)
        "breadth": assessment["breadth"],         # core outlets carrying Trump
        "deviation": assessment["deviation"],     # today / 14d-median
        "smoothed_pct": smoothed_pct,
        "assessment_method": assessment["method"],
        # Legacy theme rank kept as secondary context (not driving zone).
        "theme_rank": theme_rank_ctx["rank"],
        "n_themes": theme_rank_ctx["n_themes"],
        # Corpus artefacts.
        "sources": source_summary,
        "core_sources": sorted(CORE_FEED_KEYS),
        "matches": core_matched,
        "wide_matches": wide_matched,
        "comparisons": core_comparisons,
        "wide_comparisons": wide_comparisons,
        "themes": core_themes,
        "wide_themes": wide_themes,
    }

    log = [r for r in existing_log if r.get("date") != record["date"]]
    log.append(record)
    log.sort(key=lambda r: r.get("date", ""))
    LOG_FILE.write_text(json.dumps(log, indent=2, ensure_ascii=False))

    out_path = OUTPUT_DIR / f"{today.isoformat()}.png"
    generate_image(out_path, assessment["label"], today, core_pct, core_total)
    render_site()

    print(f"\nDate:  {today.isoformat()}")
    print(
        f"Core:  {core_trump}/{core_total} = {core_pct}%    "
        f"Wide: {wide_trump}/{wide_total} = {wide_pct}%"
    )
    print(
        f"Label: {assessment['label']}  (rank #{assessment['rank']} of "
        f"{assessment['n_people']} people, dominance "
        f"{assessment['dominance']}, breadth {assessment['breadth']}, "
        f"deviation {assessment['deviation']}, 7d avg {smoothed_pct}%)\n"
    )
    print(f"{'Source':<18} {'Fetched':>8} {'Today':>6} {'Trump':>6} {'Core':>5}")
    print("-" * 46)
    for src, payload in results.items():
        src_trump = sum(1 for _, t, s in kept if s == src and contains_trump(t))
        tag = " yes" if src in CORE_FEED_KEYS else "  no"
        print(f"{src:<18} {payload['fetched']:>8} {len(payload['articles']):>6} {src_trump:>6} {tag:>5}")
    print(f"\nImage:  {out_path}")
    print(f"Log:    {LOG_FILE}")


if __name__ == "__main__":
    main()
