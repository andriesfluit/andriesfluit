"""Match articles to companies + deduplicate cross-source.

Two-step pipeline:
  1. Resolve Google News redirect URLs to canonical outlet URLs so the
     same story routed through Google News and through the outlet's own
     feed gets recognized as one item.
  2. Deduplicate by canonical URL first, then by fuzzy title similarity
     (difflib, no extra dependency) to catch wire-syndicated stories
     that share a headline across outlets.
  3. Match the surviving articles against each company's loose regex
     pattern set in companies.py. A search-tier hit (article came from
     a per-company search feed) implicitly counts as a hit for that
     company even if no pattern matches the title.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from urllib.parse import urlparse

import requests

from companies import COMPANIES
from fetcher import _HEADERS  # reuse browser-y headers from fetcher

try:
    import cloudscraper
    _SCRAPER = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "darwin", "mobile": False}
    )
except ImportError:
    _SCRAPER = None

logger = logging.getLogger(__name__)


_COMPILED = {
    key: [re.compile(p, re.IGNORECASE) for p in cfg["patterns"]]
    for key, cfg in COMPANIES.items()
}


def match_article(article):
    """Return the list of company keys this article hits.

    A search-tier article's `origin_company_key` is an implicit hit even
    if no pattern matches, since the search feed already confirmed the
    term is present in the body."""
    hits = set()
    text = f"{article['title']} {article.get('summary', '')}"
    for key, patterns in _COMPILED.items():
        if any(p.search(text) for p in patterns):
            hits.add(key)
    origin = article.get("origin_company_key")
    if origin and origin in COMPANIES:
        hits.add(origin)
    return sorted(hits)


# -----------------------------------------------------------------------
# Canonical URL resolution for Google News redirect links.
# Google News RSS gives us https://news.google.com/rss/articles/CBMi...?oc=5
# which 30x-redirects to the real outlet URL. We resolve via a HEAD with
# follow_redirects so the same story doesn't appear twice.

def _resolve_one(url):
    if "news.google.com" not in url:
        return url
    try:
        client = _SCRAPER or requests
        # HEAD often suffices; some hosts don't support it, fall back to GET.
        for method in ("head", "get"):
            try:
                r = getattr(client, method)(
                    url, headers=_HEADERS, timeout=8,
                    allow_redirects=True, stream=(method == "get"),
                )
                if r.url and "news.google.com" not in r.url:
                    return r.url
            except Exception:
                continue
    except Exception as e:
        logger.debug("URL resolve failed for %s: %s", url, e)
    return url


def resolve_canonical(articles, max_workers=8):
    """Annotate each article with `canonical_url` (resolved or same as link)."""
    def task(art):
        art["canonical_url"] = _resolve_one(art["link"])
        return art

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        list(ex.map(task, articles))
    return articles


# -----------------------------------------------------------------------
# Deduplication.

_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)


def _norm_title(t):
    t = _PUNCT_RE.sub(" ", t.lower())
    return _WS_RE.sub(" ", t).strip()


def _origin_host(art):
    try:
        return urlparse(art.get("canonical_url") or art["link"]).netloc.lower()
    except Exception:
        return ""


# Source tier priority — when collapsing duplicates we keep the version with
# the most informative provenance.
_TIER_RANK = {"sector": 0, "press": 1, "search": 2}


def _prefer(a, b):
    """Return whichever of two duplicate articles is the better keeper."""
    # 1. Prefer the one with a known publication datetime.
    if a.get("date_unknown") and not b.get("date_unknown"):
        return b
    if b.get("date_unknown") and not a.get("date_unknown"):
        return a
    # 2. Prefer the one from a direct outlet host (not news.google.com).
    a_ng = "news.google.com" in (a.get("link") or "")
    b_ng = "news.google.com" in (b.get("link") or "")
    if a_ng and not b_ng:
        return b
    if b_ng and not a_ng:
        return a
    # 3. Prefer better source tier (sector > press > search).
    return a if _TIER_RANK.get(a.get("tier"), 99) <= _TIER_RANK.get(b.get("tier"), 99) else b


def dedupe(articles, title_threshold=0.75):
    """Collapse duplicates across sources. Strategy:
       - First pass: exact match on canonical_url.
       - Second pass: fuzzy match on normalized title above threshold.
    """
    by_url = {}
    for art in articles:
        url = art.get("canonical_url") or art["link"]
        existing = by_url.get(url)
        by_url[url] = _prefer(existing, art) if existing else art

    survivors = list(by_url.values())

    out = []
    for art in survivors:
        art_norm = _norm_title(art["title"])
        merged_with = None
        for kept in out:
            if SequenceMatcher(None, art_norm, kept["_norm_title"]).ratio() >= title_threshold:
                merged_with = kept
                break
        if merged_with is None:
            art["_norm_title"] = art_norm
            out.append(art)
        else:
            winner = _prefer(merged_with, art)
            if winner is not merged_with:
                # Replace in-place but keep the cached norm to avoid recompute.
                winner["_norm_title"] = merged_with["_norm_title"]
                idx = out.index(merged_with)
                out[idx] = winner

    # Strip internal helper field before handing back.
    for art in out:
        art.pop("_norm_title", None)
    return out


# -----------------------------------------------------------------------

def group_hits(articles):
    """Return {company_key: [articles, ...]} based on match_article."""
    by_company = {key: [] for key in COMPANIES}
    for art in articles:
        for key in match_article(art):
            by_company[key].append(art)
    return by_company
