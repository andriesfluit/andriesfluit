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
from comparators import contains_donald_trump, count_matches as count_comparators
from detector import contains_trump
from fetcher import CORE_FEED_KEYS, fetch_all
from image_gen import generate_image
from site_gen import render as render_site
from themes import count_matches as count_themes


def _contains_trump_name(text):
    """Name-only Trump match: '\\btrump\\b' minus family / building noise
    (Trump Tower, Trump Jr., Eric Trump, ...). Used for share / breadth /
    rank, so Trump is measured on the same yardstick as the other named
    figures and a slow Belgian news day with one 'Trump Tower' filler
    headline cannot lift the zone."""
    return contains_donald_trump(text)

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

    # "Today" means "today in Belgium". The runner may be on UTC (GitHub
    # Actions) or CEST / CET (local macOS launchd). Anchor explicitly to
    # Europe/Brussels so the calendar date matches what a Belgian reader
    # would call "today", even for runs that fire near midnight local.
    if ZoneInfo is not None:
        today = datetime.now(ZoneInfo("Europe/Brussels")).date()
    else:
        today = date.today()
    DATA_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    results = fetch_all(today)

    import re as _re
    import unicodedata as _u

    def _norm_title(t):
        """Normalize a title for dedup: lowercase, strip accents, collapse
        whitespace, strip editorial prefixes (VIDEO., LIVE., MULTILIVE., ...)
        and trailing ellipses. Two titles that normalize to the same string
        are considered the same article published by different outlets."""
        if not t:
            return ""
        s = _u.normalize("NFKD", t).encode("ASCII", "ignore").decode("ASCII")
        s = s.lower()
        # Drop editorial prefixes before the first substantive word.
        s = _re.sub(r"^(video|live|multilive|analyse|opinie|update|breaking|exclu|exclusief|reportage|interview|foto|photo|column)\W+", "", s)
        # Drop all quotes, punctuation, and trailing ellipsis dots.
        s = _re.sub(r"[\"'`\u2018\u2019\u201c\u201d\u2014\u2013\u2026]", "", s)
        s = _re.sub(r"[^\w\s]", " ", s)
        s = _re.sub(r"\s+", " ", s).strip()
        # Titles are often truncated with "..." at the feed cap; the first
        # 80 chars are enough to catch near-identical wire copy.
        return s[:80]

    # URL dedup is global: the same URL appearing in two feeds (e.g. a
    # Google News aggregator republishing an HLN link) is genuinely the
    # same story and we collapse it.
    #
    # Title dedup is PER OUTLET only. If HLN's feed accidentally lists
    # the same story twice (wire-copy duplication inside one publisher),
    # we collapse that. But if HLN, Nieuwsblad and GVA all decide to
    # run the same Reuters Trump story, those are three editorial
    # decisions and count as three headlines. This is important for
    # the breadth signal, which measures how many outlets picked up
    # a story regardless of whether it's wire copy.
    seen_urls = set()
    kept = []  # list of (url, title, source)
    source_summary = {}
    dup_counts = {"by_url": 0, "by_title_within_outlet": 0}

    kept_by_src = {}
    for src, payload in results.items():
        n_today = len(payload["articles"])
        seen_titles_this_outlet = set()
        kept_for_src = []
        for url, title in payload["articles"]:
            if url in seen_urls:
                dup_counts["by_url"] += 1
                continue
            tnorm = _norm_title(title)
            # Titles shorter than 12 chars after normalisation aren't deduped
            # because short strings like "update" or "video" can collide on
            # unrelated stories. Documented in the methodology caveat.
            if tnorm and len(tnorm) >= 12:
                if tnorm in seen_titles_this_outlet:
                    dup_counts["by_title_within_outlet"] += 1
                    continue
                seen_titles_this_outlet.add(tnorm)
            seen_urls.add(url)
            kept.append((url, title, src))
            kept_for_src.append((url, title))
        kept_by_src[src] = kept_for_src
        # Per-outlet stats:
        #   today            raw pre-dedup count (methodology's "From
        #                    today" column; what the feed offered).
        #   kept             post-dedup count (entered the denominator).
        #   trump            NAME-ONLY Trump matches in the kept corpus.
        #                    This is the figure breadth/rank/dominance use.
        #   trump_expanded   expanded detector matches (name + indirect
        #                    references like "White House"). Kept for the
        #                    secondary "indirect references" readout.
        outlet_kept = len(kept_for_src)
        outlet_trump_name = sum(
            1 for _, t in kept_for_src if _contains_trump_name(t)
        )
        outlet_trump_expanded = sum(
            1 for _, t in kept_for_src if contains_trump(t)
        )
        source_summary[src] = {
            "fetched": payload["fetched"],
            "today": n_today,
            "kept": outlet_kept,
            "trump": outlet_trump_name,
            "trump_expanded": outlet_trump_expanded,
            "share": round(outlet_trump_name / outlet_kept * 100, 2) if outlet_kept else 0,
        }
    logging.info(
        "Dedup: %d URL duplicates (cross-outlet), %d title duplicates within same outlet",
        dup_counts["by_url"], dup_counts["by_title_within_outlet"]
    )

    # ------ Full "wide" corpus (every feed, deduped by URL) -----------------
    # Two parallel numerators:
    #   *_name       NAME-ONLY Trump matches. Used for the zone share/rank/
    #                dominance/breadth so Trump is measured on the same
    #                yardstick as the nine other named figures.
    #   *_expanded   NAME + indirect references ("White House", "US
    #                president", etc.). Kept as a secondary editorial
    #                readout; does NOT drive the zone.
    wide_total = len(kept)
    wide_matched_expanded = [
        {"title": t, "url": u, "source": s,
         "name_only": bool(_contains_trump_name(t))}
        for u, t, s in kept
        if contains_trump(t)
    ]
    wide_matched_name = [m for m in wide_matched_expanded if m["name_only"]]
    wide_trump_name = len(wide_matched_name)
    wide_trump_expanded = len(wide_matched_expanded)
    wide_pct_name = round((wide_trump_name / wide_total * 100), 1) if wide_total else 0.0
    wide_pct_expanded = round((wide_trump_expanded / wide_total * 100), 1) if wide_total else 0.0

    wide_titles = [t for _, t, _ in kept]
    wide_comparisons = count_comparators(wide_titles)
    wide_themes = count_themes(wide_titles)

    # ------ "Core" corpus: national + regional-generalist outlets only ------
    core_kept = [(u, t, s) for u, t, s in kept if s in CORE_FEED_KEYS]
    core_total = len(core_kept)
    core_matched_expanded = [
        {"title": t, "url": u, "source": s,
         "name_only": bool(_contains_trump_name(t))}
        for u, t, s in core_kept
        if contains_trump(t)
    ]
    core_matched_name = [m for m in core_matched_expanded if m["name_only"]]
    core_trump_name = len(core_matched_name)
    core_trump_expanded = len(core_matched_expanded)
    core_pct_name = round((core_trump_name / core_total * 100), 1) if core_total else 0.0
    core_pct_expanded = round((core_trump_expanded / core_total * 100), 1) if core_total else 0.0

    # Zone signals all run on the NAME-ONLY detector now. Previously share
    # and breadth used the expanded detector (name + indirect references like
    # "White House" / "président américain") while rank and dominance used
    # name-only. That mixed yardstick made the zone hard to explain and gave
    # Trump a structural lift on share that the other fourteen comparators
    # didn't get. The expanded count is still logged as a secondary readout
    # ("indirect_references") but it does not drive the zone.
    core_trump = core_trump_name
    core_pct = core_pct_name
    wide_trump = wide_trump_name
    wide_pct = wide_pct_name

    core_titles = [t for _, t, _ in core_kept]
    core_comparisons = count_comparators(core_titles)
    core_themes = count_themes(core_titles)

    # ------ 7-day rolling average + deviation (name-only time series) ------
    # Both smoothed_pct and deviation read `core_percentage_name` off every
    # prior record, falling back to `core_percentage_expanded` for days
    # recorded before name-only was the canonical series. GDELT-backfilled
    # rows are excluded: they measured a different corpus with different
    # rules, so mixing them into the live-RSS rolling average would be a
    # denominator/methodology mismatch. Until we have >= 7 matching live
    # days in the archive, smoothed_pct is displayed as "baseline still
    # building".
    existing_log = []
    if LOG_FILE.exists():
        try:
            data = json.loads(LOG_FILE.read_text())
            existing_log = data if isinstance(data, list) else [data]
        except json.JSONDecodeError:
            existing_log = []

    def _prior_name_pct(r):
        if r.get("core_percentage_name") is not None:
            return r["core_percentage_name"]
        return r.get("core_percentage_expanded")

    prior_core_name = [
        _prior_name_pct(r)
        for r in existing_log
        if r.get("date") != today.isoformat()
        and not r.get("backfilled")
        and _prior_name_pct(r) is not None
    ]
    recent_core = prior_core_name[-6:]  # last 6 days (exclusive of today)
    window = recent_core + [core_pct_name]
    # Only publish a rolling average once we have 7 days of observations
    # (prior 6 + today). Earlier windows would silently include partial
    # data and misrepresent the baseline.
    smoothed_pct = (
        round(sum(window) / len(window), 2) if len(window) >= 7 else None
    )

    # ------ Breadth: fraction of core outlets carrying any Trump story -----
    # Gate uses KEPT (post-dedup) per-outlet count so an outlet that offered
    # 10 items but contributed only 2 after URL dedup doesn't count as
    # "active". Trump count here is also post-dedup: both sides of the
    # ratio match the share denominator.
    core_outlets = {
        s: info for s, info in source_summary.items() if s in CORE_FEED_KEYS
    }
    active_core = [info for info in core_outlets.values() if info["kept"] >= 5]
    if active_core:
        # Breadth uses the name-only count to stay on one yardstick with
        # share, rank and dominance. An outlet that only referenced Trump
        # via "the White House" does not count toward breadth.
        outlets_with_trump = sum(1 for info in active_core if info["trump"] > 0)
        breadth = outlets_with_trump / len(active_core)
    else:
        breadth = None

    # ------ Denominator control metrics ------------------------------------
    # Shifts in zone readings often come from the denominator moving, not
    # from any change in Trump coverage. Log the active-outlet fraction and
    # cross-outlet wire-copy rate so drift is visible in the archive.
    core_outlets_total = len(core_outlets)
    core_outlets_active = len(active_core)
    active_core_fraction = (
        round(core_outlets_active / core_outlets_total, 3)
        if core_outlets_total else None
    )

    # Cross-outlet title duplication. Dedup in the kept loop only collapses
    # within-outlet repeats; a wire story running verbatim in 5 outlets
    # stays as 5 kept items and inflates breadth. This metric quantifies
    # that inflation without changing the dedup behaviour.
    title_outlets = {}
    for u, t, s in core_kept:
        norm = _norm_title(t)
        if not norm or len(norm) < 12:
            continue
        entry = title_outlets.setdefault(norm, {"outlets": set(), "count": 0})
        entry["outlets"].add(s)
        entry["count"] += 1
    cross_outlet_dup_groups = sum(
        1 for v in title_outlets.values() if len(v["outlets"]) >= 2
    )
    cross_outlet_dup_headlines = sum(
        v["count"] for v in title_outlets.values() if len(v["outlets"]) >= 2
    )
    cross_outlet_dup_rate = (
        round(cross_outlet_dup_headlines / core_total * 100, 1)
        if core_total else 0.0
    )

    # ------ Deviation: today's name-only core share vs 14-day median ------
    # Reads the same name-only series (with expanded fallback for pre-
    # transition records) so numerator and denominator are on one
    # yardstick. Requires >=7 days in the trailing 14; otherwise None
    # (treated as "pass" by the gate).
    prior14 = [p for p in prior_core_name[-14:] if p is not None]
    if len(prior14) >= 7:
        med = statistics.median(prior14)
        deviation = (core_pct_name / med) if med > 0 else None
    else:
        deviation = None

    assessment = assess_composite(
        core_trump, core_total, core_comparisons,
        breadth=breadth, deviation=deviation, smoothed_pct=smoothed_pct,
    )
    # Keep the old theme rank as context (not used for the zone anymore).
    theme_rank_ctx = assess_rank_based(core_trump, core_total, core_themes)

    # Macro-average (each outlet weighed equally). Kept as a background
    # cross-check, computed on the full per-outlet summary. Gate on KEPT
    # count so an outlet whose feed was mostly URL duplicates doesn't
    # qualify on its raw pre-dedup size.
    qualifying = [s for s in source_summary.values() if s["kept"] >= 10]
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
        "last_checked_at": generated_at,
        # Headline numbers = CORE tier, NAME-ONLY (zone-driving).
        "total_articles": core_total,
        "trump_articles": core_trump_name,
        "percentage": core_pct_name,
        "core_percentage": core_pct_name,
        "core_percentage_name": core_pct_name,
        # Expanded detector (name + indirect references). Archival readout
        # only; does not drive the zone. `indirect_references` is the
        # count of headlines that matched the expanded detector but not
        # name-only, i.e. pieces that referred to Trump by role or
        # location rather than by name.
        "trump_articles_expanded": core_trump_expanded,
        "core_percentage_expanded": core_pct_expanded,
        "indirect_references": core_trump_expanded - core_trump_name,
        # Wide tier kept as cross-check.
        "wide_total_articles": wide_total,
        "wide_trump_articles": wide_trump_name,
        "wide_percentage": wide_pct_name,
        "wide_trump_articles_expanded": wide_trump_expanded,
        "wide_percentage_expanded": wide_pct_expanded,
        # Outlet-equal sanity check.
        "macro_percentage": macro_share,
        "qualifying_outlets": len(qualifying),
        # Denominator control: how many core outlets published enough
        # today to count, and what fraction of the kept core corpus is
        # wire copy running in >=2 outlets. Lets drift in the corpus
        # itself be distinguished from drift in Trump coverage.
        "core_outlets_total": core_outlets_total,
        "core_outlets_active": core_outlets_active,
        "active_core_fraction": active_core_fraction,
        "cross_outlet_dup_headlines": cross_outlet_dup_headlines,
        "cross_outlet_dup_groups": cross_outlet_dup_groups,
        "cross_outlet_dup_rate": cross_outlet_dup_rate,
        # Zone comes from the composite classifier on the core corpus.
        "zone": assessment["zone"],
        "label": assessment["label"],
        "narrative": assessment["narrative"],
        "rank": assessment["rank"],              # rank AMONG PEOPLE
        "n_people": assessment["n_people"],
        "dominance": assessment["dominance"],     # trump / sum(others)
        "breadth": assessment["breadth"],         # core outlets carrying Trump
        "deviation": assessment["deviation"],     # today / 14d-median
        "smoothed_pct": smoothed_pct,
        "assessment_method": assessment["method"],
        "thresholds_version": assessment.get("thresholds_version"),
        # Legacy theme rank kept as secondary context (not driving zone).
        "theme_rank": theme_rank_ctx["rank"],
        "n_themes": theme_rank_ctx["n_themes"],
        # Corpus artefacts. `matches` holds the EXPANDED set (so the
        # today-list shows all Trump-related headlines); each entry has a
        # name_only flag so the UI can highlight indirect references.
        "sources": source_summary,
        "core_sources": sorted(CORE_FEED_KEYS),
        "matches": core_matched_expanded,
        "wide_matches": wide_matched_expanded,
        "comparisons": core_comparisons,
        "wide_comparisons": wide_comparisons,
        "themes": core_themes,
        "wide_themes": wide_themes,
    }

    # ------ Max-over-runs: keep today's peak observation -------------------
    # Three runs per day means three different snapshots. RSS feeds only
    # expose the latest N items, so the afternoon run may show fewer Trump
    # headlines than the morning one (they've rolled off the feed). We want
    # the *peak* of the day, not the last snapshot. Rule: if a prior run
    # today already saw a higher core share, keep that record and just
    # update last_checked_at. If today's new share is higher, replace.
    existing_today = next(
        (r for r in existing_log if r.get("date") == record["date"]), None
    )
    # Pre-transition records have `percentage` in the expanded-detector
    # meaning, not name-only. If we find one, replace it rather than
    # comparing apples-to-oranges (expanded would almost always beat name-
    # only and freeze the day on a metric we no longer publish).
    existing_is_old_format = (
        existing_today is not None
        and "trump_articles_expanded" not in existing_today
    )
    if (existing_today is not None
            and not existing_is_old_format
            and (existing_today.get("percentage") or 0) >= record["percentage"]):
        logging.info(
            "Keeping earlier peak for %s (existing pct=%s >= new pct=%s)",
            record["date"],
            existing_today.get("percentage"),
            record["percentage"],
        )
        existing_today["last_checked_at"] = generated_at
        # Backfill any newly-added fields from this run's record so schema
        # additions (e.g. thresholds_version, corpus diagnostics) land on
        # the day they are introduced rather than waiting for a later
        # peak-replacing run. Never overwrites an existing non-None value.
        for k, v in record.items():
            if k not in existing_today or existing_today.get(k) is None:
                existing_today[k] = v
        record = existing_today   # render site from the preserved peak
        log = existing_log        # no replacement needed
    else:
        # New run is the new peak (or first record of the day, or a
        # one-time replacement of a pre-transition record).
        if existing_is_old_format:
            logging.info(
                "Replacing pre-transition record for %s (old expanded pct=%s)",
                record["date"], existing_today.get("percentage"),
            )
        log = [r for r in existing_log if r.get("date") != record["date"]]
        log.append(record)
        log.sort(key=lambda r: r.get("date", ""))

    LOG_FILE.write_text(json.dumps(log, indent=2, ensure_ascii=False))

    # Render the PNG from the record we actually PUBLISHED (which may be the
    # preserved earlier peak). Using this run's fresh assessment/core_pct
    # when the peak belongs to an earlier run produces a daily PNG that
    # contradicts the site card and the JSON log.
    out_path = OUTPUT_DIR / f"{today.isoformat()}.png"
    _comps = record.get("comparisons") or {}
    _others = sorted(
        ((k, v) for k, v in _comps.items() if k != "trump" and v > 0),
        key=lambda kv: kv[1], reverse=True,
    )
    from comparators import label_for as _lbl
    _rival_label = _lbl(_others[0][0]) if _others else None
    _rival_count = _others[0][1] if _others else 0
    generate_image(
        out_path,
        record["label"],
        today,
        record["percentage"],
        record["total_articles"],
        zone=record.get("zone", "dry"),
        trump_count=record.get("trump_articles", 0),
        rank=record.get("rank"),
        n_people=record.get("n_people"),
        dominance=record.get("dominance"),
        breadth=record.get("breadth"),
        core_outlets_active=record.get("core_outlets_active", 0),
        rival_label=_rival_label,
        rival_count=_rival_count,
    )
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
