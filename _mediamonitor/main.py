#!/usr/bin/env python3
"""Daily mediamonitor pipeline: fetch → match → LLM filter → mail."""

import argparse
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

from companies import COMPANIES
from feeds import all_feeds
from fetcher import fetch_all
from llm_filter import filter_company
from mailer import send as send_mail
from matcher import group_hits
from render import render_html, render_text

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"


def _today_brussels():
    if ZoneInfo is not None:
        return datetime.now(ZoneInfo("Europe/Brussels")).date()
    return date.today()


def run(to_addr, dry_run=False, no_llm=False):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    DATA_DIR.mkdir(exist_ok=True)

    today = _today_brussels()
    today_str = today.isoformat()

    logging.info("fetching feeds for %s", today_str)
    articles = fetch_all(today)
    logging.info("%d articles fetched across %d feeds", len(articles), len(all_feeds()))

    raw_hits = group_hits(articles)
    pre_total = sum(len(v) for v in raw_hits.values())
    logging.info("regex hits: %s (total=%d)",
                 {k: len(v) for k, v in raw_hits.items()}, pre_total)

    if no_llm:
        filtered = {k: [{**a, "nut": ""} for a in v] for k, v in raw_hits.items()}
    else:
        filtered = {}
        for key, items in raw_hits.items():
            filtered[key] = filter_company(key, items)
            logging.info("LLM filter %s: %d → %d", key, len(items), len(filtered[key]))

    post_total = sum(len(v) for v in filtered.values())

    stats = {
        "articles_total": len(articles),
        "feeds_total":    len(all_feeds()),
        "hits_pre":       pre_total,
        "hits_post":      post_total,
    }
    html_body = render_html(today_str, filtered, stats)
    text_body = render_text(today_str, filtered)

    if dry_run:
        out_html = DATA_DIR / f"preview-{today_str}.html"
        out_txt  = DATA_DIR / f"preview-{today_str}.txt"
        out_html.write_text(html_body, encoding="utf-8")
        out_txt.write_text(text_body, encoding="utf-8")
        print(f"DRY RUN — wrote {out_html} and {out_txt}")
        print(f"Stats: {stats}")
        return 0

    subject = f"Mediamonitor — {today_str} ({post_total} items)"
    send_mail(subject, html_body, text_body, to_addr)
    logging.info("mail sent to %s", to_addr)
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--to", default=os.environ.get("MONITOR_TO_ADDR", "andries.fluit@akkanto.com"))
    p.add_argument("--dry-run", action="store_true",
                   help="Write HTML+text to data/ instead of sending mail.")
    p.add_argument("--no-llm", action="store_true",
                   help="Skip the Claude relevance filter (testing / no API key).")
    args = p.parse_args()
    sys.exit(run(args.to, dry_run=args.dry_run, no_llm=args.no_llm))


if __name__ == "__main__":
    main()
