#!/usr/bin/env python3
"""Daily mediamonitor pipeline.

fetch (outlet feeds + per-company Google News search feeds, lookback window
since last sent) → resolve canonical URLs → cross-source dedupe → regex
match → LLM relevance filter (with 1-5 score) → enrich (real article body)
→ summarize (strict 2-3 zinnen NL) → render (sort by score) → mail.
"""

import argparse
import logging
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    _BRUSSELS = ZoneInfo("Europe/Brussels")
except ImportError:  # pragma: no cover
    _BRUSSELS = None

from enricher import enrich_many
from feeds import all_feeds_with_searches
from fetcher import fetch_all
from gnews import resolve_articles as resolve_gnews
from llm_filter import filter_company, MAX_PER_COMPANY
from mailer import send as send_mail
from matcher import dedupe, group_hits, resolve_canonical
from profiles import get_profile
from render import render_html, render_text
from summarizer import summarize_batch

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"

# How far back to look at most, even if last_sent.txt suggests further.
# Caps backlog after long outages.
MAX_LOOKBACK_HOURS = 96

# Small overlap so an article published right at last-sent isn't missed
# due to second-level clock skew.
OVERLAP_MINUTES = 30


def _now_brussels():
    if _BRUSSELS is not None:
        return datetime.now(_BRUSSELS)
    return datetime.now()


def _compute_since(now_dt, last_sent_path):
    """Read the state file and return (since_dt, lookback_hours) for fetching.

    Supports both legacy date-only ('YYYY-MM-DD') and new ISO datetime
    formats. Falls back to 24h before now when missing or unparseable."""
    fallback_hours = 24
    if not last_sent_path.exists():
        return now_dt - timedelta(hours=fallback_hours), fallback_hours

    raw = last_sent_path.read_text(encoding="utf-8").strip()
    parsed = None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        try:
            # Legacy date-only format from earlier versions.
            d = date.fromisoformat(raw)
            parsed = datetime(d.year, d.month, d.day, 7, 30,
                              tzinfo=_BRUSSELS) if _BRUSSELS else datetime(
                d.year, d.month, d.day, 7, 30)
        except ValueError:
            parsed = None
    if parsed is None:
        return now_dt - timedelta(hours=fallback_hours), fallback_hours

    if parsed.tzinfo is None and _BRUSSELS is not None:
        parsed = parsed.replace(tzinfo=_BRUSSELS)
    since_dt = parsed - timedelta(minutes=OVERLAP_MINUTES)
    earliest = now_dt - timedelta(hours=MAX_LOOKBACK_HOURS)
    if since_dt < earliest:
        since_dt = earliest
    lookback = max(1, int((now_dt - since_dt).total_seconds() // 3600) + 1)
    return since_dt, lookback


# Tier priority for pre-LLM truncation when a company exceeds MAX_PER_COMPANY
# candidates. Search-tier means the brand/term explicitly matched in the
# article, so it's the highest-signal source.
_TIER_PRIORITY = {"search": 0, "sector": 1, "press": 2, None: 3}


def _candidate_sort_key(art):
    return (
        _TIER_PRIORITY.get(art.get("tier"), 99),
        # newer first
        -(art["published_dt"].timestamp() if art.get("published_dt") else 0),
    )


def run(profile, to_addr, dry_run=False, no_llm=False, no_enrich=False, no_resolve=False,
        lookback_override=None):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    DATA_DIR.mkdir(exist_ok=True)
    last_sent_path = DATA_DIR / profile.state_filename

    now_dt = _now_brussels()
    if lookback_override:
        lookback = int(lookback_override)
        since_dt = now_dt - timedelta(hours=lookback)
        logging.info("forced lookback=%dh (test run, state file ignored)", lookback)
    else:
        since_dt, lookback = _compute_since(now_dt, last_sent_path)
    today_str = now_dt.date().isoformat()
    logging.info("profile=%s lookback=%dh (since=%s, now=%s)",
                 profile.name, lookback, since_dt.isoformat(), now_dt.isoformat())

    feeds = all_feeds_with_searches(profile.companies, when_hours=lookback + 12,
                                    outlet_feeds=profile.outlet_feeds)
    logging.info("fetching %d feeds (%d outlet + per-company searches)",
                 len(feeds), len(profile.outlet_feeds))
    articles = fetch_all(since_dt, feeds=feeds)
    logging.info("%d articles fetched in window", len(articles))

    # Resolve Google News redirects so duplicate stories from the outlet's
    # direct feed AND its Google News mirror dedupe correctly.
    if not no_resolve and articles:
        resolve_canonical(articles)
    else:
        for a in articles:
            a["canonical_url"] = a["link"]

    deduped = dedupe(articles)
    logging.info("after dedup: %d articles (was %d)", len(deduped), len(articles))

    raw_hits = group_hits(deduped, profile.companies)
    pre_total = sum(len(v) for v in raw_hits.values())
    logging.info("regex+origin hits: %s (total=%d)",
                 {k: len(v) for k, v in raw_hits.items()}, pre_total)

    # Pre-LLM ranking & truncation so high-signal items survive the cap.
    for key, items in raw_hits.items():
        if len(items) > MAX_PER_COMPANY:
            items.sort(key=_candidate_sort_key)
            logging.warning("%s: %d candidates > cap %d, truncating to highest-signal",
                            key, len(items), MAX_PER_COMPANY)
            raw_hits[key] = items[:MAX_PER_COMPANY]

    # Stage 1: strategic relevance filter
    if no_llm:
        filtered = {k: [{**a, "topic": "", "nut": "", "score": 3} for a in v]
                    for k, v in raw_hits.items()}
    else:
        filtered = {}
        for key, items in raw_hits.items():
            filtered[key] = filter_company(key, items, profile.companies,
                                           profile.llm_system, profile.include_action)
            logging.info("LLM filter %s: %d → %d", key, len(items), len(filtered[key]))

    # Stage 2: enrich + summarize the survivors
    if not no_enrich and not no_llm:
        all_relevant = [a for items in filtered.values() for a in items]
        if all_relevant:
            # New-style Google News links don't HTTP-redirect to the outlet;
            # resolve them via the batchexecute decoder now that only a few
            # dozen articles remain (two requests per article). This gives
            # the enricher a real outlet URL to pull the body from and the
            # mail a direct link to the newspaper instead of news.google.com.
            if not no_resolve:
                resolve_gnews(all_relevant)
            logging.info("enriching %d articles (fetching bodies)", len(all_relevant))
            enrich_many(all_relevant)
            counts = {"ok": 0, "paywall": 0, "fail": 0}
            for a in all_relevant:
                counts[a.get("body_status", "fail")] += 1
            logging.info("enrich results: %s", counts)
            for key, items in filtered.items():
                if items:
                    summarize_batch(items)
                    logging.info("summarized %s (%d items)", key, len(items))
    else:
        for items in filtered.values():
            for a in items:
                a["summary_long"] = (a.get("summary") or "").strip()
                a["summary_source"] = "rss_snippet_noenrich"

    # Sort items per bucket by Claude score desc, then recency desc, and cap
    # the number shown. A noisy bucket (e.g. bikon's technique track) should
    # not bloat the mail; a smaller message also avoids Gmail throttling.
    for items in filtered.values():
        items.sort(key=lambda a: (
            -(a.get("score") or 0),
            -(a["published_dt"].timestamp() if a.get("published_dt") else 0),
        ))
        del items[profile.max_per_bucket:]

    post_total = sum(len(v) for v in filtered.values())

    stats = {
        "articles_total": len(articles),
        "articles_deduped": len(deduped),
        "feeds_total":    len(feeds),
        "hits_pre":       pre_total,
        "hits_post":      post_total,
        "lookback_hours": lookback,
    }
    html_body = render_html(today_str, filtered, stats, profile.companies,
                            title=profile.subject_prefix, footer=profile.render_footer)
    text_body = render_text(today_str, filtered, profile.companies,
                            title=profile.subject_prefix)

    if dry_run:
        out_html = DATA_DIR / f"preview-{profile.name}-{today_str}.html"
        out_txt  = DATA_DIR / f"preview-{profile.name}-{today_str}.txt"
        out_html.write_text(html_body, encoding="utf-8")
        out_txt.write_text(text_body, encoding="utf-8")
        print(f"DRY RUN wrote {out_html} and {out_txt}")
        print(f"Stats: {stats}")
        return 0

    subject = f"{profile.subject_prefix} - {today_str} ({post_total} items)"
    send_mail(subject, html_body, text_body, to_addr)
    logging.info("mail sent to %s", to_addr)
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--profile", default="akkanto", choices=("akkanto", "bikon"),
                   help="Which monitoring track to run.")
    p.add_argument("--to", default=None,
                   help="Recipient. Defaults to the profile's env var, then its default address.")
    p.add_argument("--dry-run", action="store_true",
                   help="Write HTML+text to data/ instead of sending mail.")
    p.add_argument("--no-llm", action="store_true",
                   help="Skip the Claude filter and summary (testing / no API key).")
    p.add_argument("--no-enrich", action="store_true",
                   help="Skip article body fetching + summarization (faster, less detail).")
    p.add_argument("--no-resolve", action="store_true",
                   help="Skip Google News canonical URL resolution (faster, weaker dedup).")
    p.add_argument("--lookback-hours", type=int, default=None,
                   help="Force the lookback window in hours, ignoring the state file "
                        "(for test runs). The caller is responsible for not stamping.")
    args = p.parse_args()
    profile = get_profile(args.profile)
    to_addr = args.to or os.environ.get(profile.to_addr_env) or profile.default_to
    sys.exit(run(profile, to_addr,
                 dry_run=args.dry_run,
                 no_llm=args.no_llm,
                 no_enrich=args.no_enrich,
                 no_resolve=args.no_resolve,
                 lookback_override=args.lookback_hours))


if __name__ == "__main__":
    main()
