"""
Comparator subjects measured on the same Belgian RSS corpus as Trump.
Used by main.py (writes counts into the daily log) and by site_gen.py
(renders the comparison panel).
"""
import re

# (key, regex, display_label) -- regex matches against article titles, case-insensitive.
# Patterns include the Dutch/French/English variants used in Belgian press.
_TERMS = [
    ("trump",     r"\btrump\b",                                  "Trump"),
    ("de_wever",  r"\bde\s*wever\b",                             "De Wever"),
    ("macron",    r"\bmacron\b",                                 "Macron"),
    ("putin",     r"\b(putin|poetin|poutine)\b",                 "Putin"),
    ("netanyahu", r"\bnetanyahu\b",                              "Netanyahu"),
    ("zelensky",  r"\bzelensk(?:y|yi|i)\b",                      "Zelensky"),
    ("musk",      r"\bmusk\b",                                   "Musk"),
    ("orban",     r"\borb[aá]n\b",                               "Orb\u00e1n"),
    ("meloni",    r"\bmeloni\b",                                 "Meloni"),
    ("bouchez",   r"\bbouchez\b",                                "Bouchez"),
]

COMPARATORS = [
    {"key": k, "label": label, "pattern": re.compile(pat, re.IGNORECASE)}
    for k, pat, label in _TERMS
]


def count_matches(titles):
    """Return {key: count} for each comparator across the given titles.
    `titles` is materialized to a list so it can be iterated repeatedly."""
    titles = list(titles)
    out = {}
    for c in COMPARATORS:
        out[c["key"]] = sum(1 for t in titles if c["pattern"].search(t or ""))
    return out


def label_for(key):
    for c in COMPARATORS:
        if c["key"] == key:
            return c["label"]
    return key
