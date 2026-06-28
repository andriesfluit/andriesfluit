#!/usr/bin/env python3
"""Daily personal news digest — combined across sources.

Each night the run fetches that day's edition of every source (De Standaard, De
Tijd, …) straight from the public Twipe CDN (no login), pools all articles, and
asks Claude for ONE combined digest: KERN op maat + protected VERRASSING, with
duplicate stories across the two papers merged. Every item keeps its source
label. Result: one mail and one MyNews page — your single place for all the news
that interests you.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from digest import build_digest, KERN_COUNT, VERRASSING_COUNT
from feedback import load_feedback_context, record_shown
from parse import parse_bundle
from render import render_html, render_json, render_markdown
import sources as sources_mod

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
INCOMING_DIR = DATA_DIR / "incoming"
DIGEST_DIR = DATA_DIR / "digests"
PREFERENCES = ROOT / "preferences.md"
SITE_DATA_DIR = ROOT.parent / "mynews" / "data"

DEFAULT_TO = "andries.fluit@gmail.com"

# Combined digest spans two papers, so aim a little higher than a single source.
COMBINED_KERN = 10
COMBINED_VERR = 5

# Feedback/history live under one "combined" namespace — one place.
FEEDBACK_KEY = "combined"

_SHORT = {k: v["short"] for k, v in sources_mod.SOURCES.items()}


def _state_file(key):
    return DATA_DIR / f"{key}_last_edition.json"


def _load_state(cfg):
    try:
        return json.loads(_state_file(cfg["key"]).read_text(encoding="utf-8"))
    except Exception:
        return {"id": cfg["seed_id"], "date": cfg["seed_date"]}


def _save_state(key, edition, date):
    try:
        _state_file(key).write_text(json.dumps({"id": int(edition), "date": date}),
                                    encoding="utf-8")
    except (ValueError, OSError) as e:
        logging.warning("kon editie-state niet schrijven: %s", e)


def _assign_handles(date, kern, verrassing):
    """Source-prefixed, date-scoped handles with a global counter per bucket,
    e.g. ds-0626-a1, dt-0626-a2 (kern) / ds-0626-v1 (verrassing)."""
    mmdd = "".join(date.split("-")[1:]) if date else datetime.now().strftime("%m%d")
    for n, a in enumerate(kern, 1):
        a["handle"] = f"{_SHORT.get(a.get('source'), 'xx')}-{mmdd}-a{n}"
    for n, a in enumerate(verrassing, 1):
        a["handle"] = f"{_SHORT.get(a.get('source'), 'xx')}-{mmdd}-v{n}"


def _gather(target, force):
    """Fetch + parse every source for `target`; return (pool, editions)."""
    from capture import fetch_bundle
    pool, editions = [], []
    for key in sources_mod.ORDER:
        cfg = sources_mod.get(key)
        state = _load_state(cfg)
        bundle = fetch_bundle(cfg["base"], state.get("id"), state.get("date"),
                              target_date=target)
        if not bundle or not bundle.get("publications"):
            logging.warning("[%s] geen editie voor %s", key, target)
            continue
        parsed = parse_bundle(bundle)
        for a in parsed["articles"]:
            a["bron"] = cfg["label"]
            a["source"] = cfg["key"]
        pool += parsed["articles"]
        _save_state(key, parsed["edition"], parsed["date"])
        editions.append(f"{cfg['label']} {parsed['edition']}")
        logging.info("[%s] %d artikels (editie %s)", key, len(parsed["articles"]),
                     parsed["edition"])
    return pool, editions


def run(to_addr=None, dry_run=False, no_llm=False, force=False,
        kern_n=COMBINED_KERN, verr_n=COMBINED_VERR, input_path=None):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    for d in (DATA_DIR, INCOMING_DIR, DIGEST_DIR, SITE_DATA_DIR):
        d.mkdir(parents=True, exist_ok=True)
    preferences = PREFERENCES.read_text(encoding="utf-8") if PREFERENCES.exists() else \
        "Geen voorkeuren ingesteld — kies een brede, evenwichtige selectie."

    from capture import _today
    target = _today()
    if not force and (SITE_DATA_DIR / f"{target}.json").exists():
        logging.info("digest voor %s bestaat al; niets te doen", target)
        return 0

    if input_path:
        # Single-source manual capture (testing): treat it as the whole pool.
        bundle = json.loads(Path(input_path).read_text(encoding="utf-8"))
        parsed = parse_bundle(bundle)
        for a in parsed["articles"]:
            a["bron"] = "(handmatig)"
            a["source"] = "destandaard"
        pool, editions = parsed["articles"], [f"editie {parsed['edition']}"]
    else:
        pool, editions = _gather(target, force)

    if not pool:
        # Expected on Sundays/holidays: no paper is published that day. Treat it
        # as a clean no-op (exit 0) so the nightly cron doesn't send a spurious
        # "Run failed" mail; the previous digest simply stays in place.
        logging.info("geen editie voor %s (zon-/feestdag?) — niets te doen", target)
        return 0
    logging.info("totaal %d artikels uit %d kranten", len(pool), len(editions))

    if no_llm:
        kern = [{**a, "score": 3, "waarom": "", "samenvatting": a.get("intro", "")}
                for a in pool[:kern_n]]
        verrassing = [{**a, "waarom": "", "samenvatting": a.get("intro", "")}
                      for a in pool[kern_n:kern_n + verr_n]]
        digest = {"rode_draad": "", "kern": kern, "verrassing": verrassing}
    else:
        fb = load_feedback_context(DATA_DIR, FEEDBACK_KEY)
        if fb:
            logging.info("feedback-context (%d tekens)", len(fb))
        digest = build_digest(pool, preferences, fb, kern_n=kern_n, verr_n=verr_n)

    logging.info("digest: %d kern, %d verrassing", len(digest["kern"]), len(digest["verrassing"]))
    _assign_handles(target, digest["kern"], digest["verrassing"])

    meta = {"date": target, "article_count": len(pool),
            "label": "De Standaard + De Tijd", "sources_line": " · ".join(editions)}

    md = render_markdown(meta, digest)
    html = render_html(meta, digest)
    blob = json.dumps(render_json(meta, digest), ensure_ascii=False, indent=2)

    (DIGEST_DIR / f"combined_{target}.md").write_text(md, encoding="utf-8")
    (SITE_DATA_DIR / f"{target}.json").write_text(blob, encoding="utf-8")
    (SITE_DATA_DIR / "latest.json").write_text(blob, encoding="utf-8")
    logging.info("geschreven naar %s", SITE_DATA_DIR)

    if not no_llm:
        record_shown(DATA_DIR, FEEDBACK_KEY, target, digest["kern"], digest["verrassing"])

    if dry_run or no_llm:
        (SITE_DATA_DIR / f"{target}.html").write_text(html, encoding="utf-8")
        logging.info("DRY RUN")
        return 0

    if to_addr and os.environ.get("GMAIL_APP_PASSWORD"):
        from mailer import send as send_mail
        subject = (f"Jouw nieuwsdigest — {target} "
                   f"({len(digest['kern'])}+{len(digest['verrassing'])})")
        send_mail(subject, html, md, to_addr)
        logging.info("mail verstuurd naar %s", to_addr)
    else:
        logging.info("geen mail (geen GMAIL_APP_PASSWORD)")
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--auto", action="store_true",
                   help="Fetch today's editions from the public CDN (default mode).")
    p.add_argument("--force", action="store_true", help="Rebuild even if today exists.")
    p.add_argument("--input", default=None, help="A .raw.json capture (single-source test).")
    p.add_argument("--to", default=None, help="Email recipient.")
    p.add_argument("--dry-run", action="store_true", help="Write files, never mail.")
    p.add_argument("--no-llm", action="store_true", help="Skip Claude (smoke test).")
    p.add_argument("--kern", type=int, default=COMBINED_KERN)
    p.add_argument("--verrassing", type=int, default=COMBINED_VERR)
    args = p.parse_args()

    to_addr = args.to or os.environ.get("DESTANDAARD_TO_ADDR") or DEFAULT_TO
    sys.exit(run(to_addr=to_addr, dry_run=args.dry_run, no_llm=args.no_llm,
                 force=args.force, kern_n=args.kern, verr_n=args.verrassing,
                 input_path=args.input))


if __name__ == "__main__":
    main()
