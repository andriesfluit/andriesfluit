"""Map articles to companies via the topic-driven pattern lists in companies.py.

Matching is loose by design: an article hits a company if ANY pattern in
that company's list matches the title or RSS summary (case-insensitive).
The LLM filter (llm_filter.py) handles strategic relevance afterwards.
"""

import re

from companies import COMPANIES


_COMPILED = {
    key: [re.compile(p, re.IGNORECASE) for p in cfg["patterns"]]
    for key, cfg in COMPANIES.items()
}


def match_article(article):
    """Return the list of company keys this article hits."""
    text = f"{article['title']} {article.get('summary', '')}"
    return [
        key
        for key, patterns in _COMPILED.items()
        if any(p.search(text) for p in patterns)
    ]


def group_hits(articles):
    """Group articles by company key. One article can belong to several.
    Within a company, dedupe on normalized title (same headline often shows
    up in multiple feeds, e.g. direct + Google News mirror)."""
    by_company = {key: [] for key in COMPANIES}
    seen = {key: set() for key in COMPANIES}
    for art in articles:
        for key in match_article(art):
            norm = re.sub(r"\s+", " ", art["title"].lower()).strip()
            if norm in seen[key]:
                continue
            seen[key].add(norm)
            by_company[key].append(art)
    return by_company
