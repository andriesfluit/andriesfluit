"""Does a headline reference Trump?

Expanded beyond the literal name to include common indirect references used
in the Belgian press (NL, FR, EN). The site is measuring current coverage of
the Trump administration, so "White House", "US president", "Amerikaanse
president", "président américain" etc. all count: in the current news cycle
they refer to Trump.

Note: `comparators.py` intentionally still matches people by name only. That
is a different question ("how does Trump's name rank among named people?")
and expanding one person's regex while the others stay name-only would bias
the rank.
"""
import re

_PATTERNS = [
    # Direct name, incl. Dutch s-genitive ("Trumps uitnodiging"). Word
    # boundary so "trumpeter" doesn't match. Kept in sync with
    # comparators.PATTERN_VERSION.
    r"\btrumps?\b",

    # White House / Witte Huis / Maison(-)Blanche.
    r"\bwhite\s+house\b",
    r"\bwitte\s+huis\b",
    r"\bmaison[-\s]+blanche\b",

    # "Oval Office" / "Bureau ovale" (rare but unambiguous).
    r"\boval\s+office\b",
    r"\bbureau\s+ovale\b",

    # US / American president (pinned to the current occupant by modifier).
    r"\bu\.?s\.?\s+president\b",
    r"\bamerican\s+president\b",
    r"\bamerikaans(?:e)?\s+president\b",
    r"\bpresident\s+van\s+de\s+(?:vs|vsa|verenigde\s+staten)\b",
    r"\bpr[eé]sident(?:e)?\s+am[eé]ricain(?:e)?\b",
    r"\bpr[eé]sident(?:e)?\s+des\s+[eé]tats[-\s]?unis\b",
]

_COMBINED = re.compile("|".join(_PATTERNS), re.IGNORECASE)


def contains_trump(text):
    return bool(_COMBINED.search(text or ""))
