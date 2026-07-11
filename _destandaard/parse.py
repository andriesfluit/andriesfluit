"""Parse a raw Twipe JSON bundle (dumped by the browser bookmarklet) into a
clean list of article dicts.

The capture step deliberately keeps the *raw* JSON: all HTML/entity cleaning
happens here, in Python, where a real HTML parser decodes every entity
correctly and the logic is testable. (The old browser script hand-rolled a
regex stripper that only knew a handful of named entities; anything else —
&agrave;, &hellip;, &mdash;, numeric refs — leaked through as literal text.)
"""

import hashlib
import logging
from html.parser import HTMLParser

logger = logging.getLogger(__name__)

# Block-level tags whose close (or, for <br>, presence) marks a line break in
# the plain-text rendering. Everything else is inline.
_BLOCK_TAGS = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
               "ul", "ol", "table", "blockquote", "section", "article"}


class _TextExtractor(HTMLParser):
    """Turn HtmlText into plain text, inserting newlines at block boundaries.

    convert_charrefs=True (the default) means the parser decodes *all* HTML
    entities — named and numeric — into real characters before they reach
    handle_data. That is the whole point of doing this in a parser instead of
    with regex substitutions."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._parts = []

    def handle_data(self, data):
        self._parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def text(self):
        return "".join(self._parts)


def html_to_text(html):
    """Decode HTML to clean plain text with paragraphs separated by blank lines."""
    if not html:
        return ""
    p = _TextExtractor()
    try:
        p.feed(str(html))
        p.close()
        raw = p.text()
    except Exception as e:  # malformed markup — fall back to a naive strip
        logger.warning("HTML parse failed, falling back: %s", e)
        raw = str(html)

    # Normalise whitespace: collapse runs of spaces/tabs, trim each line,
    # drop blank lines, then re-join paragraphs with a blank line between them.
    lines = []
    for line in raw.replace("\r", "\n").split("\n"):
        line = " ".join(line.split())  # collapse internal whitespace
        if line:
            lines.append(line)
    return "\n\n".join(lines).strip()


def _uid(publication_id, title, page):
    """Short stable id for an article, used to tie feedback back to history."""
    h = hashlib.md5(f"{publication_id}|{page}|{title}".encode("utf-8")).hexdigest()
    return h[:8]


def parse_bundle(bundle):
    """Turn a raw capture bundle into a flat list of normalised articles.

    Expected bundle shape (produced by capture/bookmarklet.js):
        {edition, date, captured_at, package, publications: [{id, name, content}]}
    where each `content` is a GetPublicationContentItems-*.json payload.
    """
    edition = str(bundle.get("edition", "")).strip()
    date = (bundle.get("date") or bundle.get("package", {}).get("PublicationDate", ""))[:10]

    articles = []
    for pub in bundle.get("publications", []):
        pub_id = str(pub.get("id", ""))
        pub_name = pub.get("name", "")
        items = (pub.get("content") or {}).get("Content") or []
        for c in items:
            ci = (c.get("ContentItem") or [{}])[0] or {}
            body = html_to_text(ci.get("HtmlText"))
            if not body:
                continue  # adverts, podcast stubs, image-only items: no text
            title = html_to_text(ci.get("Title")).replace("\n", " ").strip()
            page = c.get("PageNumber")
            articles.append({
                "uid": _uid(pub_id, title, page),
                "edition": edition,
                "date": date,
                "publication": pub_name,
                "page": page if isinstance(page, int) else _to_int(page),
                "rubriek": (c.get("Category") or "Overig").strip(),
                "title": title or "(zonder titel)",
                "suptitle": html_to_text(ci.get("SupTitle")).replace("\n", " ").strip(),
                "subtitle": html_to_text(ci.get("SubTitle")).replace("\n", " ").strip(),
                "author": str(ci.get("Author") or ci.get("Byline") or "").strip(),
                "intro": html_to_text(ci.get("Introduction")).replace("\n", " ").strip(),
                "body": body,
                "wordcount": len(body.split()),
            })

    articles.sort(key=lambda a: (a["page"] if a["page"] is not None else 9999))
    logger.info("parsed %d articles from edition %s (%s)", len(articles), edition, date)
    return {"edition": edition, "date": date, "articles": articles}


def _to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
