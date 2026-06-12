"""Resolve Google News RSS redirect links to the real outlet URL.

Google News RSS gives links like
    https://news.google.com/rss/articles/CBMi...?oc=5
Until mid-2024 the article ID was a base64-encoded protobuf with the real
URL embedded — a cheap offline decode. Newer IDs (payload starts with
'AU_yqL') no longer embed the URL and the link doesn't HTTP-redirect either
(it serves a JS bootstrap page), so the only way to the outlet URL is
Google's internal batchexecute endpoint: fetch the article page for a
signature + timestamp, then POST a `garturlreq`. Two requests per article,
so we only do that for the handful of items that survive the LLM filter —
never for the full fetch corpus.

Everything degrades gracefully: any failure returns None and callers keep
the google link (mail still works, summary falls back to RSS snippet).
"""

import base64
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "nl-BE,nl;q=0.9,fr;q=0.8,en;q=0.7",
}

_ID_RE = re.compile(r"news\.google\.com/(?:rss/)?articles/([^?/&]+)")


def _article_id(url):
    m = _ID_RE.search(url or "")
    return m.group(1) if m else None


def decode_offline(url):
    """Cheap no-network decode for old-style (CBMi...) IDs.
    Returns the outlet URL or None."""
    gid = _article_id(url)
    if not gid:
        return None
    try:
        raw = base64.urlsafe_b64decode(gid + "=" * (-len(gid) % 4))
    except Exception:
        return None
    m = re.search(rb'https?://[^\x00-\x20"\x7f-\xff]+', raw)
    if not m:
        return None
    candidate = m.group(0).decode(errors="replace")
    # Old-style payloads sometimes append a second URL (AMP variant); the
    # first is the canonical one. Strip trailing protobuf noise.
    return candidate.rstrip("\\")


def _decode_via_api(gid, timeout=12):
    """Resolve a new-style ID via Google's batchexecute endpoint."""
    page = requests.get(
        f"https://news.google.com/rss/articles/{gid}",
        headers=_HEADERS, timeout=timeout,
    )
    sig = re.search(r'data-n-a-sg="([^"]+)"', page.text)
    ts = re.search(r'data-n-a-ts="([^"]+)"', page.text)
    if not sig or not ts:
        return None

    inner = (
        '["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,'
        'null,null,null,null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],'
        f'"{gid}",{ts.group(1)},"{sig.group(1)}"]'
    )
    payload = "f.req=" + quote(json.dumps([[["Fbv4je", inner, None, "generic"]]]))
    resp = requests.post(
        "https://news.google.com/_/DotsSplashUi/data/batchexecute",
        headers={**_HEADERS,
                 "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
        data=payload, timeout=timeout,
    )
    # Response is ")]}'" + JSON chunks. The URL sits nested in the payload;
    # structured parse first, regex as belt-and-braces.
    try:
        body = resp.text.replace(")]}'", "", 1)
        chunk = body.split("\n\n")[1]
        outer = json.loads(chunk)
        url = json.loads(outer[0][2])[1]
        if isinstance(url, str) and url.startswith("http"):
            return url
    except Exception:
        pass
    m = re.search(r'"(https?://(?!news\.google)[^"]+)"', resp.text)
    return m.group(1) if m else None


def resolve_url(url, timeout=12):
    """Full resolve: offline decode first, batchexecute for new-style IDs.
    Returns the outlet URL or None."""
    if "news.google.com" not in (url or ""):
        return url
    decoded = decode_offline(url)
    if decoded:
        return decoded
    gid = _article_id(url)
    if not gid:
        return None
    try:
        return _decode_via_api(gid, timeout=timeout)
    except Exception as e:
        logger.debug("batchexecute resolve failed for %s: %s", gid[:24], e)
        return None


def resolve_articles(articles, max_workers=6):
    """Resolve canonical_url in-place for articles whose link points at
    news.google.com. Intended for the SMALL post-filter set (typically
    10-40 items), not the full corpus — each new-style ID costs two
    requests. Logs the success rate so run logs show decoder health."""
    todo = [a for a in articles
            if "news.google.com" in (a.get("canonical_url") or a["link"])]
    if not todo:
        return articles

    def task(art):
        resolved = resolve_url(art["link"])
        if resolved and "news.google.com" not in resolved:
            art["canonical_url"] = resolved
            return True
        return False

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        results = list(ex.map(task, todo))
    ok = sum(results)
    logger.info("gnews resolve: %d/%d google-links resolved to outlet URLs",
                ok, len(todo))
    return articles
