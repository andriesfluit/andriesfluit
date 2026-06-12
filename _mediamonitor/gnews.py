"""Decode Google News RSS article URLs to the real publisher URL.

Google News RSS links look like
    https://news.google.com/rss/articles/CBMi...?oc=5
which a normal HTTP GET only resolves to a JS-redirect consent page, so the
enricher cannot fetch the article body (this is why Bikon summaries were all
RSS snippets: every link came via Google News). Two-step decode:

  1. Fast path, no network: the base64 in the path is a protobuf that, in the
     older format, carries the publisher URL as a length-delimited string.
  2. Slow path: fetch the article page to read its signature + timestamp, then
     POST Google's internal batchexecute endpoint, which returns the real URL.

Everything fails soft: on any error we return the original URL and the caller
falls back to the RSS snippet, exactly as before. Decoding is therefore
upside-only.
"""

import base64
import json
import logging
import re

import requests

logger = logging.getLogger(__name__)

_BATCH_URL = "https://news.google.com/_/DotsSplashUi/data/batchexecute"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )
}


def _segment(url):
    m = re.search(r"/(?:rss/)?articles/([^?/]+)", url)
    return m.group(1) if m else None


def _read_varint(buf, i):
    val = shift = 0
    while i < len(buf):
        b = buf[i]
        i += 1
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            return val, i
        shift += 7
    return val, i


def _plaintext_url(b64):
    """Older protobuf format: field 4 (tag 0x22) is the publisher URL string."""
    try:
        raw = base64.urlsafe_b64decode(b64 + "=" * (-len(b64) % 4))
    except Exception:
        return None
    # Expect leading \x08\x13 then the 0x22 length-delimited URL field.
    if len(raw) < 4 or raw[0:2] != b"\x08\x13" or raw[2] != 0x22:
        return None
    ln, i = _read_varint(raw, 3)
    cand = raw[i:i + ln].decode("utf-8", "ignore")
    return cand if cand.startswith("http") and "news.google.com" not in cand else None


def _batchexecute_url(b64, session, timeout):
    """Newer format: ask Google's internal endpoint for the real URL."""
    r = session.get(f"https://news.google.com/rss/articles/{b64}",
                    headers=_HEADERS, timeout=timeout)
    r.raise_for_status()
    sig = re.search(r'data-n-a-sg="([^"]+)"', r.text)
    ts = re.search(r'data-n-a-ts="([^"]+)"', r.text)
    if not (sig and ts):
        return None
    inner = (
        '["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,'
        'null,null,null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],'
        f'"{b64}",{ts.group(1)},"{sig.group(1)}"]'
    )
    body = "f.req=" + requests.utils.quote(json.dumps([[["Fbv4je", inner, None, "generic"]]]))
    r2 = session.post(
        _BATCH_URL, data=body, timeout=timeout,
        headers={**_HEADERS,
                 "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
    )
    r2.raise_for_status()
    # Response: XSSI guard + length-prefixed lines; the URL sits in an escaped
    # JSON string under our rpc id. Try a structured parse, then regex.
    for line in r2.text.splitlines():
        line = line.strip()
        if line.startswith("[[") and "garturlres" in line:
            try:
                return json.loads(json.loads(line)[0][2])[1]
            except Exception:
                break
    m = re.search(r'garturlres\\?",\\?"(https?:.+?)\\?"', r2.text)
    if m:
        return m.group(1).replace("\\/", "/").encode().decode("unicode_escape")
    return None


def decode(url, session=None, timeout=6):
    """Return the real publisher URL for a Google News link, or `url` itself."""
    if "news.google.com" not in url:
        return url
    b64 = _segment(url)
    if not b64:
        return url
    plain = _plaintext_url(b64)
    if plain:
        return plain
    own = session or requests.Session()
    try:
        return _batchexecute_url(b64, own, timeout) or url
    except Exception as e:
        logger.debug("gnews decode failed for %s: %s", url, e)
        return url
    finally:
        if session is None:
            own.close()
