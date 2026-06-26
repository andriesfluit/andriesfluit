#!/usr/bin/env python3
"""Daily e-paper digest pipeline — multi-source.

For each configured source (De Standaard, De Tijd, …) the nightly run fetches
that day's edition straight from the public Twipe CDN (no login), builds the
personal digest with Claude (KERN op maat + protected VERRASSING, folding in
that source's feedback), mails it, and publishes the JSON the MyNews web reader
consumes — all per source.
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

# Personal digest → your own inbox. Override with --to or DESTANDAARD_TO_ADDR.
DEFAULT_TO = "andries.fluit@gmail.com"


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


def _assign_handles(short, date, kern, verrassing):
    """Short, source- and date-scoped feedback handles, e.g. ds-0626-a3."""
    mmdd = "".join(date.split("-")[1:]) if date else datetime.now().strftime("%m%d")
    for n, a in enumerate(kern, 1):
        a["handle"] = f"{short}-{mmdd}-a{n}"
    for n, a in enumerate(verrassing, 1):
        a["handle"] = f"{short}-{mmdd}-v{n}"


def build_source(cfg, preferences, to_addr=None, dry_run=False, no_llm=False,
                 kern_n=KERN_COUNT, verr_n=VERRASSING_COUNT,
                 auto=False, force=False, input_path=None):
    """Build (and optionally mail) the digest for one source. Returns 0 on
    success, 3 when no edition is available yet."""
    key, label, short = cfg["key"], cfg["label"], cfg["short"]
    site_dir = SITE_DATA_DIR / key
    site_dir.mkdir(parents=True, exist_ok=True)

    if auto:
        from capture import fetch_bundle, _today
        target = _today()
        if not force and (site_dir / f"{target}.json").exists():
            logging.info("[%s] digest voor %s bestaat al; overslaan", key, target)
            return 0
        state = _load_state(cfg)
        bundle = fetch_bundle(cfg["base"], state.get("id"), state.get("date"),
                              target_date=target)
        if not bundle or not bundle.get("publications"):
            logging.warning("[%s] geen editie voor %s beschikbaar", key, target)
            return 3
    else:
        if not input_path or not Path(input_path).exists():
            logging.error("[%s] --input vereist (of gebruik --auto)", key)
            return 2
        bundle = json.loads(Path(input_path).read_text(encoding="utf-8"))

    parsed = parse_bundle(bundle)
    articles = parsed["articles"]
    date = parsed["date"]
    edition = parsed["edition"]
    if not articles:
        logging.error("[%s] geen artikels geparseerd", key)
        return 2
    logging.info("[%s] %d artikels (editie %s, %s)", key, len(articles), edition, date)

    if no_llm:
        kern = [{**a, "score": 3, "waarom": "", "samenvatting": a.get("intro", "")}
                for a in articles[:kern_n]]
        verrassing = [{**a, "waarom": "", "samenvatting": a.get("intro", "")}
                      for a in articles[kern_n:kern_n + verr_n]]
        digest = {"rode_draad": "", "kern": kern, "verrassing": verrassing}
    else:
        fb = load_feedback_context(DATA_DIR, key)
        if fb:
            logging.info("[%s] feedback-context (%d tekens)", key, len(fb))
        digest = build_digest(articles, preferences, fb, kern_n=kern_n, verr_n=verr_n)

    logging.info("[%s] digest: %d kern, %d verrassing", key,
                 len(digest["kern"]), len(digest["verrassing"]))

    _assign_handles(short, date, digest["kern"], digest["verrassing"])
    meta = {"date": date, "edition": edition, "article_count": len(articles),
            "source": key, "label": label}

    md = render_markdown(meta, digest)
    html = render_html(meta, digest)
    data = render_json(meta, digest)
    blob = json.dumps(data, ensure_ascii=False, indent=2)

    DIGEST_DIR.mkdir(exist_ok=True)
    (DIGEST_DIR / f"{key}_{date or edition}.md").write_text(md, encoding="utf-8")
    (site_dir / f"{date or edition}.json").write_text(blob, encoding="utf-8")
    (site_dir / "latest.json").write_text(blob, encoding="utf-8")
    logging.info("[%s] geschreven naar %s", key, site_dir)

    if not no_llm:
        record_shown(DATA_DIR, key, date, digest["kern"], digest["verrassing"])
        if auto:
            _save_state(key, edition, date)

    if dry_run or no_llm:
        (site_dir / f"{date or edition}.html").write_text(html, encoding="utf-8")
        logging.info("[%s] DRY RUN", key)
        return 0

    if to_addr and os.environ.get("GMAIL_APP_PASSWORD"):
        from mailer import send as send_mail
        subject = f"{label} — digest {date} ({len(digest['kern'])}+{len(digest['verrassing'])})"
        send_mail(subject, html, md, to_addr)
        logging.info("[%s] mail verstuurd naar %s", key, to_addr)
    else:
        logging.info("[%s] geen mail (geen GMAIL_APP_PASSWORD)", key)
    return 0


def run(source_keys, **kw):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    for d in (DATA_DIR, INCOMING_DIR, DIGEST_DIR):
        d.mkdir(exist_ok=True)
    preferences = PREFERENCES.read_text(encoding="utf-8") if PREFERENCES.exists() else \
        "Geen voorkeuren ingesteld — kies een brede, evenwichtige selectie."

    rc = 0
    for key in source_keys:
        cfg = sources_mod.get(key)
        try:
            r = build_source(cfg, preferences, **kw)
            rc = rc or (r if r not in (0, 3) else 0)
        except Exception as e:  # one source failing shouldn't sink the others
            logging.exception("[%s] gefaald: %s", key, e)
            rc = 1
    return rc


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--auto", action="store_true",
                   help="Fetch today's edition(s) from the public CDN (no login).")
    p.add_argument("--force", action="store_true",
                   help="With --auto: rebuild even if today's digest already exists.")
    p.add_argument("--source", default=None, choices=list(sources_mod.SOURCES),
                   help="Only this source (default: all in sources.ORDER).")
    p.add_argument("--input", default=None,
                   help="Path to a .raw.json capture (single source, with --source).")
    p.add_argument("--to", default=None, help="Email recipient.")
    p.add_argument("--dry-run", action="store_true", help="Write files, never mail.")
    p.add_argument("--no-llm", action="store_true", help="Skip Claude (smoke test).")
    p.add_argument("--kern", type=int, default=KERN_COUNT)
    p.add_argument("--verrassing", type=int, default=VERRASSING_COUNT)
    args = p.parse_args()

    keys = [args.source] if args.source else list(sources_mod.ORDER)
    to_addr = args.to or os.environ.get("DESTANDAARD_TO_ADDR") or DEFAULT_TO
    sys.exit(run(keys, to_addr=to_addr, dry_run=args.dry_run, no_llm=args.no_llm,
                 kern_n=args.kern, verr_n=args.verrassing, auto=args.auto,
                 force=args.force, input_path=args.input))


if __name__ == "__main__":
    main()
