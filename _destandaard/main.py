#!/usr/bin/env python3
"""De Standaard daily digest pipeline.

raw Twipe JSON (captured in the browser) → parse + clean → Claude editor
(KERN op maat + protected VERRASSING) folding in learned feedback → render
markdown + HTML → write the .md, record what was shown, and optionally mail.

Capture is manual (your logged-in session dumps the raw JSON via
capture/bookmarklet.js); everything after that is automated and testable.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from digest import build_digest, KERN_COUNT, VERRASSING_COUNT, VERRASSING_MIN
from feedback import load_feedback_context, record_shown
from parse import parse_bundle
from render import render_html, render_markdown

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
INCOMING_DIR = DATA_DIR / "incoming"
DIGEST_DIR = DATA_DIR / "digests"
PREFERENCES = ROOT / "preferences.md"

# Personal digest → your own inbox. Override with --to or DESTANDAARD_TO_ADDR.
# Defaulting here means the pipeline reuses mediamonitor's existing Gmail
# secrets and needs no new repo secret of its own.
DEFAULT_TO = "andries.fluit@gmail.com"


def _newest_raw():
    candidates = sorted(INCOMING_DIR.glob("*.raw.json"),
                        key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def _assign_handles(date, kern, verrassing):
    """Give every shown item a short, date-scoped feedback handle (e.g. 0626-a3)."""
    mmdd = "".join(date.split("-")[1:]) if date else datetime.now().strftime("%m%d")
    for n, a in enumerate(kern, 1):
        a["handle"] = f"{mmdd}-a{n}"
    for n, a in enumerate(verrassing, 1):
        a["handle"] = f"{mmdd}-v{n}"


def run(input_path=None, to_addr=None, dry_run=False, no_llm=False,
        kern_n=KERN_COUNT, verr_n=VERRASSING_COUNT):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    for d in (DATA_DIR, INCOMING_DIR, DIGEST_DIR):
        d.mkdir(exist_ok=True)

    raw_path = Path(input_path) if input_path else _newest_raw()
    if not raw_path or not raw_path.exists():
        logging.error("no raw capture found. Run the bookmarklet and put the "
                      ".raw.json in %s, or pass --input.", INCOMING_DIR)
        return 2
    logging.info("parsing %s", raw_path)

    bundle = json.loads(raw_path.read_text(encoding="utf-8"))
    parsed = parse_bundle(bundle)
    articles = parsed["articles"]
    date = parsed["date"]
    edition = parsed["edition"]
    if not articles:
        logging.error("no articles parsed from %s", raw_path)
        return 2

    preferences = PREFERENCES.read_text(encoding="utf-8") if PREFERENCES.exists() else \
        "Geen voorkeuren ingesteld — kies een brede, evenwichtige selectie."

    if no_llm:
        # No-API smoke test: take the first items by page order, no summaries.
        kern = [{**a, "score": 3, "waarom": "", "samenvatting": a.get("intro", "")}
                for a in articles[:kern_n]]
        verrassing = [{**a, "waarom": "", "samenvatting": a.get("intro", "")}
                      for a in articles[kern_n:kern_n + verr_n]]
        digest = {"rode_draad": "", "kern": kern, "verrassing": verrassing}
    else:
        feedback_context = load_feedback_context(DATA_DIR)
        if feedback_context:
            logging.info("folding in feedback context (%d chars)", len(feedback_context))
        digest = build_digest(articles, preferences, feedback_context,
                              kern_n=kern_n, verr_n=verr_n)

    logging.info("digest: %d kern, %d verrassing", len(digest["kern"]), len(digest["verrassing"]))

    _assign_handles(date, digest["kern"], digest["verrassing"])
    meta = {"date": date, "edition": edition, "article_count": len(articles)}

    md = render_markdown(meta, digest)
    html = render_html(meta, digest)

    out_md = DIGEST_DIR / f"De_Standaard_{date or edition}.md"
    out_md.write_text(md, encoding="utf-8")
    logging.info("wrote %s", out_md)

    # Record what we showed so future feedback handles resolve. Skip on no-llm
    # smoke tests so they don't pollute the history.
    if not no_llm:
        record_shown(DATA_DIR, date, digest["kern"], digest["verrassing"])

    if dry_run or no_llm:
        out_html = DIGEST_DIR / f"De_Standaard_{date or edition}.html"
        out_html.write_text(html, encoding="utf-8")
        print(f"DRY RUN wrote {out_md} and {out_html}")
        return 0

    if to_addr and os.environ.get("GMAIL_APP_PASSWORD"):
        from mailer import send as send_mail
        subject = f"De Standaard — digest {date} ({len(digest['kern'])}+{len(digest['verrassing'])})"
        send_mail(subject, html, md_to_text(md), to_addr)
        logging.info("mail sent to %s", to_addr)
    else:
        logging.info("no mail sent (no GMAIL_APP_PASSWORD); digest written to %s", out_md)
    return 0


def md_to_text(md):
    """Plain-text email alternative: markdown is already readable as text."""
    return md


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default=None,
                   help="Path to a .raw.json capture. Defaults to newest in data/incoming/.")
    p.add_argument("--to", default=None,
                   help="Email recipient. Without it, only the .md file is written.")
    p.add_argument("--dry-run", action="store_true",
                   help="Write .md + .html, never mail.")
    p.add_argument("--no-llm", action="store_true",
                   help="Skip Claude (smoke test): page-order pick, no summaries, no history.")
    p.add_argument("--kern", type=int, default=KERN_COUNT)
    p.add_argument("--verrassing", type=int, default=VERRASSING_COUNT)
    args = p.parse_args()

    to_addr = args.to or os.environ.get("DESTANDAARD_TO_ADDR") or DEFAULT_TO
    sys.exit(run(input_path=args.input, to_addr=to_addr, dry_run=args.dry_run,
                 no_llm=args.no_llm, kern_n=args.kern, verr_n=args.verrassing))


if __name__ == "__main__":
    main()
