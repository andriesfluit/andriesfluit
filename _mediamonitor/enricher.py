"""Fetch the actual article body so the summarizer has real content to work
with, instead of a 40-char RSS snippet.

Three possible outcomes per URL:
  - ok       : extracted body text (>= 300 useful chars)
  - paywall  : page loaded but the body is locked behind a paywall snippet
  - fail     : fetch error, redirect dead-end, or trafilatura couldn't parse

The summarizer (summarizer.py) sees the body when ok, and falls back to the
RSS summary for paywall/fail without ever asking the LLM to fill the gap.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor

import requests

try:
    import cloudscraper
    _SCRAPER = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "darwin", "mobile": False}
    )
except ImportError:
    _SCRAPER = None

try:
    import trafilatura
except ImportError:
    trafilatura = None

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "nl-BE,nl;q=0.9,fr;q=0.8,en;q=0.7",
}

# Snippets that signal we hit a paywall instead of the article body.
_PAYWALL_MARKERS = [
    r"reeds abonnee",
    r"abonnee worden",
    r"déjà abonné",
    r"d[ée]j[àa]\s+abonn[eé]",
    r"s['']abonner",
    r"abonneer\s+je",
    r"plus pour les abonn[eé]s",
    r"premium content",
    r"toegang voorbehouden",
    r"this article is for subscribers",
    r"voor abonnees",
]
_PAYWALL_RE = re.compile("|".join(_PAYWALL_MARKERS), re.IGNORECASE)

# Sites that consistently block direct requests but accept cloudscraper.
_CLOUDFLARE_HOSTS = ("standaard.be", "demorgen.be", "hln.be", "nieuwsblad.be",
                     "tijd.be", "lecho.be", "lalibre.be", "dhnet.be",
                     "lesoir.be", "knack.be")


def _fetch(url, timeout=15):
    use_scraper = _SCRAPER is not None and any(h in url for h in _CLOUDFLARE_HOSTS)
    if use_scraper:
        try:
            return _SCRAPER.get(url, timeout=timeout)
        except Exception:
            pass  # fall through to plain requests
    return requests.get(url, headers=_HEADERS, timeout=timeout, allow_redirects=True)


def enrich_one(url):
    """Return (status, text). status ∈ {"ok", "paywall", "fail"}."""
    if trafilatura is None:
        return "fail", ""
    try:
        resp = _fetch(url)
        if resp.status_code != 200:
            return "fail", ""
        html = resp.text
    except Exception as e:
        logger.debug("enrich fetch %s: %s", url, e)
        return "fail", ""

    body = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        favor_recall=True,
    )
    if not body:
        return "fail", ""

    cleaned = body.strip()
    if len(cleaned) < 300 or _PAYWALL_RE.search(cleaned):
        return "paywall", cleaned
    return "ok", cleaned


def enrich_many(articles, max_workers=8):
    """Annotate each article in-place with `body_status` and `body_text`."""
    def task(art):
        # Prefer the resolved outlet URL — fetching the news.google.com
        # redirect page yields a JS bootstrap document trafilatura can't parse.
        status, text = enrich_one(art.get("canonical_url") or art["link"])
        art["body_status"] = status
        art["body_text"] = text
        return art

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        list(ex.map(task, articles))
    return articles
