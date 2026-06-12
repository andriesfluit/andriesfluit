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
from difflib import SequenceMatcher
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# Compiled patterns are cached per companies-dict (keyed by id) so each
# profile compiles its regexes once. COMPANIES and BIKON_COMPANIES are both
# module-level singletons, so their id() is stable for the whole run.
_COMPILED_CACHE = {}


def _compiled_for(companies):
    cached = _COMPILED_CACHE.get(id(companies))
    if cached is None:
        cached = {
            key: [re.compile(p, re.IGNORECASE) for p in cfg["patterns"]]
            for key, cfg in companies.items()
        }
        _COMPILED_CACHE[id(companies)] = cached
    return cached


def match_article(article, companies):
    """Return the list of company keys this article hits.

    A search-tier article's `origin_company_key` is an implicit hit even
    if no pattern matches, since the search feed already confirmed the
    term is present in the body."""
    hits = set()
    text = f"{article['title']} {article.get('summary', '')}"
    for key, patterns in _compiled_for(companies).items():
        if any(p.search(text) for p in patterns):
            hits.add(key)
    origin = article.get("origin_company_key")
    if origin and origin in companies:
        hits.add(origin)
    return sorted(hits)


# -----------------------------------------------------------------------
# Canonical URL annotation for Google News redirect links.
# New-style Google News article IDs (since 2024) no longer HTTP-redirect to
# the outlet — resolving them needs Google's batchexecute endpoint (two
# requests per article, see gnews.py). Doing that for the full fetch corpus
# (~1000 articles/day) would burn minutes on network calls, so here we only
# apply gnews.decode_offline (instant, works for legacy CBMi-style IDs) and
# leave new-style links for main.py to resolve AFTER the LLM filter, when
# only a few dozen articles remain. Title-similarity dedup below covers the
# google-mirror-vs-direct-feed duplicates the URL pass can't see.

from gnews import decode_offline


def resolve_canonical(articles, max_workers=None):
    """Annotate each article with `canonical_url` (offline decode only)."""
    for art in articles:
        decoded = decode_offline(art["link"]) if "news.google.com" in art["link"] else None
        art["canonical_url"] = decoded or art["link"]
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

def group_hits(articles, companies):
    """Return {company_key: [articles, ...]} based on match_article."""
    by_company = {key: [] for key in companies}
    for art in articles:
        for key in match_article(art, companies):
            by_company[key].append(art)
    return by_company
