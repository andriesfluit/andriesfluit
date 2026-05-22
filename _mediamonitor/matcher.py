"""Map articles to companies using the rules from companies.py."""

import re

from companies import COMPANIES


def _compile(patterns):
    return [re.compile(p, re.IGNORECASE) for p in (patterns or [])]


_COMPILED = {}
for key, cfg in COMPANIES.items():
    _COMPILED[key] = [
        {
            "any":         _compile(rule.get("any")),
            "context_any": _compile(rule.get("context_any")),
            "none":        _compile(rule.get("none")),
        }
        for rule in cfg["rules"]
    ]


def _rule_fires(rule, text):
    if not any(p.search(text) for p in rule["any"]):
        return False
    if rule["context_any"] and not any(p.search(text) for p in rule["context_any"]):
        return False
    if rule["none"] and any(p.search(text) for p in rule["none"]):
        return False
    return True


def match_article(article):
    """Return the list of company keys this article hits (0, 1, or more)."""
    text = f"{article['title']} {article.get('summary', '')}"
    return [
        key
        for key, rules in _COMPILED.items()
        if any(_rule_fires(rule, text) for rule in rules)
    ]


def group_hits(articles):
    """Group articles by company key. One article can belong to several."""
    by_company = {key: [] for key in COMPANIES}
    seen_per_company = {key: set() for key in COMPANIES}
    for art in articles:
        for key in match_article(art):
            # Same headline can appear in multiple feeds (Google News + direct).
            # Dedupe per company on normalized title.
            norm = re.sub(r"\s+", " ", art["title"].lower()).strip()
            if norm in seen_per_company[key]:
                continue
            seen_per_company[key].add(norm)
            by_company[key].append(art)
    return by_company
