"""
Comparator subjects measured on the same Belgian RSS corpus as Trump.
Used by main.py (writes counts into the daily log) and by site_gen.py
(renders the comparison panel).

Inclusion rule (applied manually; reviewed quarterly):
  - Belgian figures: current federal PM, current party president of a
    federal-coalition or major federal-opposition party, or a sitting
    federal minister who is recurrently named in Belgian front-page news.
  - International figures: heads of state or government, or leaders of
    major international institutions, whose actions make recurring
    Belgian front-page news.
  - Removed from earlier versions: Orbán, Meloni, Musk (intermittent
    Belgian daily-news salience); De Croo (former PM, left government
    February 2025).
  - Note: Jambon matches the French word for ham but political news
    headlines dominate in the RSS feeds used; noise is acceptable.
  - Once the live archive is 90+ days, this editorial list can be
    replaced by "anyone with ≥ N name mentions in the trailing
    90-day core corpus", making the list self-maintaining.

The patterns match article titles case-insensitively, with word
boundaries. Python 3 \\b is Unicode-aware so accented characters work.
"""
import re

# (key, regex, display_label, region)
# region is "intl" or "be"; used only for documentation/grouping.
_TERMS = [
    # ---- International (7) ----
    ("trump",         r"\btrump\b",                                 "Trump",         "intl"),
    ("putin",         r"\b(putin|poetin|poutine)\b",                "Putin",         "intl"),
    ("macron",        r"\bmacron\b",                                "Macron",        "intl"),
    ("netanyahu",     r"\bnetanyahu\b",                             "Netanyahu",     "intl"),
    ("zelensky",      r"\bzelensk(?:yy|y|yi|i)\b",                  "Zelensky",      "intl"),
    ("rutte",         r"\brutte\b",                                 "Rutte",         "intl"),
    ("von_der_leyen", r"\bvon\s+der\s+leyen\b",                     "Von der Leyen", "intl"),
    # ---- Belgian (10) ----
    ("de_wever",      r"\bde\s*wever\b",                            "De Wever",      "be"),
    ("bouchez",       r"\bbouchez\b",                               "Bouchez",       "be"),
    ("magnette",      r"\bmagnette\b",                              "Magnette",      "be"),
    ("prevot",        r"\bpr[eé]vot\b",                        "Prévot",   "be"),
    ("rousseau",      r"\brousseau\b",                              "Rousseau",      "be"),
    ("francken",      r"\bfrancken\b",                              "Francken",      "be"),
    ("crevits",       r"\bcrevits\b",                               "Crevits",       "be"),
    ("jambon",        r"\bjambon\b",                                "Jambon",        "be"),
    ("van_peteghem",  r"\bvan\s*peteghem\b",                        "Van Peteghem",  "be"),
    ("verlinden",     r"\bverlinden\b",                             "Verlinden",     "be"),
]

COMPARATORS = [
    {"key": k, "label": label, "region": region,
     "pattern": re.compile(pat, re.IGNORECASE)}
    for k, pat, label, region in _TERMS
]

# Name-only Trump pattern, exposed so main.py can count per-outlet Trump
# matches using the same regex used for comparator ranking (keeps share,
# breadth, rank and dominance on one consistent yardstick).
TRUMP_NAME_PATTERN = next(c["pattern"] for c in COMPARATORS if c["key"] == "trump")


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
