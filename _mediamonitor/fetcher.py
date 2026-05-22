"""Fetch today's headlines from all configured feeds.

Adapted from _trumpflood/fetcher.py — same Cloudflare handling and
Brussels-local date filter, but returns the wider feed set from feeds.py
and tracks per-article source tier.
"""

import logging
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


def _entry_date(entry):
    for key in ("published_parsed", "updated_parsed"):
        val = entry.get(key)
        if val:
            utc_dt = datetime(
                val.tm_year, val.tm_mon, val.tm_mday,
                val.tm_hour, val.tm_min, val.tm_sec,
                tzinfo=timezone.utc,
            )
            if _BRUSSELS is not None:
                return utc_dt.astimezone(_BRUSSELS).date()
            return utc_dt.date()
    return None


def _get(name, url):
    if _SCRAPER is not None and name in CLOUDSCRAPER_FEEDS:
        return _SCRAPER.get(url, timeout=30)
    return requests.get(url, headers=_HEADERS, timeout=20)


def fetch_one(name, url, today):
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
        d = _entry_date(entry)
        if d != today:
            continue
        link = entry.get("link")
        title = (entry.get("title") or "").strip()
        if not link or not title:
            continue
        # feedparser exposes the RSS <description>/<summary> under .summary.
        # For Google News it contains a list of related links; for direct
        # feeds it's the lede. Useful context for the LLM filter.
        summary = (entry.get("summary") or "").strip()
        articles.append({
            "source": name,
            "title": title,
            "link": link,
            "summary": summary,
        })
    return articles


def fetch_all(today):
    """Return [{source, tier, title, link, summary}, ...] for today's articles."""
    out = []
    feeds = all_feeds()
    for name, meta in feeds.items():
        for art in fetch_one(name, meta["url"], today):
            art["tier"] = meta["tier"]
            out.append(art)
    return out
