"""Fetch today's headlines from all configured feeds.

Adapted from _trumpflood/fetcher.py — same Cloudflare handling and
Brussels-local date filter, but returns the wider feed set from feeds.py
and tracks per-article source tier.
"""

import html as _html
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import feedparser
import requests

try:
    from zoneinfo import ZoneInfo
    _BRUSSELS = ZoneInfo("Europe/Brussels")
except ImportError:  # pragma: no cover
    _BRUSSELS = None

try:
    import cloudscraper
    _SCRAPER = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "darwin", "mobile": False}
    )
except ImportError:
    _SCRAPER = None

from feeds import (
    CLOUDSCRAPER_FALLBACKS,
    CLOUDSCRAPER_FEEDS,
    all_feeds,
)

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "nl-BE,nl;q=0.9,fr;q=0.8,en;q=0.7",
}


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(s):
    """Convert RSS-summary markup to plain text.

    Google News feeds put HTML inside <description>: anchor tags to the
    source outlet, &nbsp; padding, <font color> for the byline, related-link
    lists. Left raw, that HTML survives our html.escape() in the renderer
    and shows up as literal tags in the email body.
    """
    if not s:
        return ""
    s = _TAG_RE.sub(" ", s)
    s = _html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def _entry_datetime(entry):
    """Return the entry's publication datetime in Brussels-local tz,
    or None if no timestamp is parseable."""
    for key in ("published_parsed", "updated_parsed"):
        val = entry.get(key)
        if val:
            utc_dt = datetime(
                val.tm_year, val.tm_mon, val.tm_mday,
                val.tm_hour, val.tm_min, val.tm_sec,
                tzinfo=timezone.utc,
            )
            if _BRUSSELS is not None:
                return utc_dt.astimezone(_BRUSSELS)
            return utc_dt
    return None


def _get(name, url):
    if _SCRAPER is not None and name in CLOUDSCRAPER_FEEDS:
        return _SCRAPER.get(url, timeout=30)
    return requests.get(url, headers=_HEADERS, timeout=20)


def fetch_one(name, url, since_dt, tier=None):
    """Fetch one feed; return articles published at-or-after since_dt.

    Articles without a parseable timestamp are KEPT when they come from
    a search-tier feed (Google News already date-filters via when:Xh),
    and DROPPED when they come from generalist outlet feeds (where an
    undated entry might be ancient evergreen content). Kept-undated
    items are marked `date_unknown=True` so downstream sorting and dedup
    can deprioritize them."""
    try:
        resp = _get(name, url)
        resp.raise_for_status()
    except Exception as e:
        fallback = CLOUDSCRAPER_FALLBACKS.get(name)
        if fallback:
            logger.warning("fetch failed for %s (%s), trying fallback", name, e)
            try:
                resp = requests.get(fallback, headers=_HEADERS, timeout=20)
                resp.raise_for_status()
            except Exception as e2:
                logger.warning("fallback failed for %s: %s", name, e2)
                return []
        else:
            logger.warning("fetch failed for %s: %s", name, e)
            return []

    parsed = feedparser.parse(resp.content)
    articles = []
    for entry in parsed.entries or []:
        entry_dt = _entry_datetime(entry)
        date_unknown = entry_dt is None
        if date_unknown:
            # Only trust an undated entry when the feed itself date-bounds it.
            if tier != "search":
                continue
        elif entry_dt < since_dt:
            continue
        link = entry.get("link")
        title = (entry.get("title") or "").strip()
        if not link or not title:
            continue
        # feedparser exposes the RSS <description>/<summary> under .summary.
        # For Google News it contains anchor tags + related-link HTML; for
        # direct feeds it's typically the lede. Strip HTML so the matcher
        # sees plain text and the renderer doesn't show literal tags.
        summary = _strip_html(entry.get("summary") or "")
        articles.append({
            "source": name,
            "title": _strip_html(title),
            "link": link,
            "summary": summary,
            "published_dt": entry_dt,         # datetime or None
            "date_unknown": date_unknown,
        })
    return articles


def fetch_all(since_dt, feeds=None, max_workers=10):
    """Fetch every configured feed in parallel and return a flat list of articles.

    `since_dt` is a Brussels-local timezone-aware datetime; articles older
    than that are filtered out. `feeds` defaults to the outlet-wide catalogue
    via all_feeds(); pass a custom dict (e.g. all_feeds_with_searches(...))
    to include per-company search feeds.

    With ~200 search feeds the sequential version would blow the workflow
    timeout. 10 concurrent fetches keeps total wall time around 30-60 s
    while staying conservative for Google News rate limits."""
    if feeds is None:
        feeds = all_feeds()

    def task(item):
        name, meta = item
        tier = meta.get("tier")
        results = fetch_one(name, meta["url"], since_dt, tier=tier)
        for art in results:
            art["tier"] = tier
            art["origin_company_key"] = meta.get("company_key")
        return results

    out = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for batch in ex.map(task, feeds.items()):
            out.extend(batch)
    return out
