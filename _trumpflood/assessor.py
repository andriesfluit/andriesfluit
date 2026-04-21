"""
Zone assessment for Trump prevalence in Belgian news.

Zone floors are loaded from thresholds.json at import time. That file
starts out with hand-picked cutoffs; once the live name-only archive
has enough history (>= 30 days), calibrate.py can regenerate it as
percentiles of the observed distribution and save the version metadata
so readers can see how the floors were derived.

Live records (from main.py) use the composite classifier
(assess_composite). Backfilled GDELT records have no comparator data
and fall back to the original % thresholds (assess_pct_based); we
mark them so the site can show the difference.
"""

import json as _json
from pathlib import Path as _Path

_THRESHOLDS_FILE = _Path(__file__).parent / "thresholds.json"


def _load_thresholds():
    """Load zone thresholds as a dict keyed by zone name. Falls back to
    the hand-picked defaults if thresholds.json is missing or malformed
    so the tool still runs on a fresh checkout."""
    defaults = {
        "flooding": {"pct": 4.0, "dominance": 2.0, "breadth": 0.55, "rank_max": 1},
        "soaked":   {"pct": 2.5, "dominance": 1.2, "breadth": 0.40, "rank_max": 1},
        "wet":      {"pct": 1.5, "dominance": None, "breadth": 0.25, "rank_max": 2},
        "puddles":  {"pct": 0.8, "dominance": None, "breadth": None, "rank_max": 4},
    }
    version = "v0-eyeballed (defaults)"
    if _THRESHOLDS_FILE.exists():
        try:
            data = _json.loads(_THRESHOLDS_FILE.read_text())
            zones = {z["key"]: z for z in data.get("zones", [])}
            if all(k in zones for k in defaults):
                version = data.get("version", version)
                return {k: zones[k] for k in defaults}, version, data
        except (_json.JSONDecodeError, KeyError, TypeError):
            pass
    return defaults, version, None


THRESHOLDS, THRESHOLDS_VERSION, THRESHOLDS_META = _load_thresholds()

# (zone_key, label, narrative_template). {rank} and {n} get filled in.
ZONES = [
    ("dry",      "The zone is dry",            "Barely registered today."),
    ("puddles",  "Puddles are forming",        "Present, but a minor topic of the day."),
    ("wet",      "The zone is getting wet",    "Prominent \u2014 rank #{rank} of {n} subjects."),
    ("soaked",   "The zone is soaked",         "Among the very top stories \u2014 rank #{rank} of {n}."),
    ("flooding", "Trump is flooding the zone", "THE story of the day."),
]
ZONE_KEYS = [z[0] for z in ZONES]
ZONE_LABELS = {k: lbl for k, lbl, _ in ZONES}
ZONE_NARRATIVES = {k: n for k, _, n in ZONES}

# Rank-based criteria. A zone is awarded if rank <= max_rank AND share >= min_share.
# Evaluated top-down (most extreme first).
# WET threshold loosened to rank<=6 (top 40% of subjects) so a clearly
# prominent placement counts even when the percentage is moderate.
_RANK_RULES = [
    # (zone, max_rank, min_share_pct)
    ("flooding", 1,  5.0),
    ("soaked",   3,  3.5),
    ("wet",      6,  1.5),
    ("puddles", 12,  0.4),
]


def assess_rank_based(trump_count, total, theme_counts):
    """Use Trump's rank within `theme_counts.values()` plus minimum share to
    pick a zone. Returns (zone_key, label, narrative_text, rank, n)."""
    pct = trump_count / total * 100 if total else 0.0
    if not theme_counts:
        return assess_pct_based(trump_count, total)

    counts = list(theme_counts.values())
    n = len(counts) + 1  # themes + Trump as one entry
    rank = sum(1 for c in counts if c > trump_count) + 1

    chosen = "dry"
    for zone, max_rank, min_share in _RANK_RULES:
        if rank <= max_rank and pct >= min_share:
            chosen = zone
            break

    label = ZONE_LABELS[chosen]
    narrative = ZONE_NARRATIVES[chosen].format(rank=rank, n=n)
    return {
        "zone": chosen,
        "label": label,
        "narrative": narrative,
        "rank": rank,
        "n_themes": n,
        "method": "rank",
    }


# ---------------------------------------------------------------------------
# People-based zone classifier (v2). This is the one main.py calls going
# forward. Rationale: "flooding the zone" is about one figure dominating
# attention. Comparing Trump to broad THEME categories (war, crime, ...) is
# structurally unfair because themes aggregate dozens of stories while Trump
# is a single entity. The right comparison is Trump vs. other NAMED PEOPLE.
#
# Inputs:
#   trump_count       matches for Trump in today's core-tier corpus
#   core_total        size of today's core-tier corpus (deduped articles)
#   comparisons       dict {person_key: count} from comparators.count_matches
#                     on the core-tier corpus (must include 'trump')
#   smoothed_pct      7-day rolling average of core percentage (may be None
#                     if we don't yet have enough core history)
#
# Signals:
#   pct               Trump's share of today's core corpus
#   rank              Trump's rank among comparator PEOPLE (1 = top)
#   dominance         Trump mentions / sum of all OTHER comparator people
#                     (>= 1.0 means Trump alone outweighs the other 9 combined)
#
# Zone rules (top-down, first match wins):
#   Flooding  rank=1 AND dominance >= 1.0 AND pct >= 3.0
#             AND (smoothed >= 2.0 OR smoothed is None)
#   Soaked    rank=1 AND dominance >= 0.5 AND pct >= 2.0
#   Wet       rank <= 2 AND pct >= 1.5
#   Puddles   rank <= 4 AND pct >= 0.4
#   Dry       otherwise
# ---------------------------------------------------------------------------
_PEOPLE_LABELS = {
    "flooding": ("Trump is flooding the zone",
                 "Out-mentions every other figure combined \u2014 THE story of the day."),
    "soaked":   ("The zone is soaked",
                 "Most-mentioned figure by a wide margin."),
    "wet":      ("The zone is getting wet",
                 "Among the top-covered figures today."),
    "puddles":  ("Puddles are forming",
                 "Present, but a minor figure in today's mix."),
    "dry":      ("The zone is dry",
                 "Barely registered today."),
}


def assess_composite(trump_count, core_total, comparisons,
                     breadth=None, deviation=None, smoothed_pct=None):
    """Composite zone classifier. Every zone above 'dry' requires multiple
    signals to clear a floor, not just rank.

    Signals:
      pct         Trump's share of today's core corpus (%). Driven by
                  trump_count, which uses the expanded detector (name +
                  'White House', 'US president', ...).
      rank        Trump's rank among named comparator people (1 = top).
                  Uses comparisons['trump'] (name-only) so the comparison
                  is apples-to-apples with the other nine figures.
      dominance   trump-by-name / sum(other_comparator_counts). Also uses
                  the name-only count for the same reason.
      breadth     fraction of core outlets (with >=5 today articles) that
                  carried at least one Trump reference. Range [0, 1]. None
                  if not yet computable.
      deviation   today_pct / median(prior 14d core_pct). None if not yet
                  enough history. When None, the gate is treated as passed.

    Zone ladder (top-down, first match wins):
      flooding  pct>=4.0 AND dominance>=2.0 AND rank==1 AND breadth>=0.55
      soaked    pct>=2.5 AND dominance>=1.2 AND rank==1 AND breadth>=0.40
      wet       pct>=1.5 AND rank<=2 AND (breadth>=0.25 OR breadth is None)
      puddles   pct>=0.8 AND rank<=4
      dry       otherwise

    Deviation (today's share vs. the 14-day median) is reported back to
    the caller and displayed next to the zone, but it is no longer a
    gate. The old >=1.5x floor on Flooding was non-binding in practice:
    any day clearing the other four Flooding floors always cleared 1.5x
    baseline by a wide margin, so deviation was ornamental. Keeping it
    as an annotation lets readers see when a day is unusual for the
    site's own baseline without the gate pretending to filter.

    Thresholds were lowered from their original values (5.0/3.5/2.0 pct
    floors, 0.60/0.45/0.30 breadth floors) because those were calibrated
    against GDELT's broader corpus. Our core-tier RSS sampling is smaller
    and narrower; 2.7% of core headlines is meaningful salience, not
    background noise. Dominance and rank floors stay unchanged since they
    are corpus-independent ratios.
    """
    pct = (trump_count / core_total * 100) if core_total else 0.0
    comps = dict(comparisons or {})
    others = {k: v for k, v in comps.items() if k != "trump"}
    n_people = len(comps) or 1

    # Use the NAME-ONLY count for rank and dominance so Trump is measured
    # on the same footing as Macron, Putin, De Wever, etc. The expanded
    # detector (used for pct above) would otherwise give Trump an unfair
    # lift by counting 'White House' / 'président américain' headlines.
    trump_by_name = comps.get("trump", trump_count)

    if others:
        others_sum = sum(others.values())
        rank = sum(1 for v in others.values() if v > trump_by_name) + 1
    else:
        others_sum = 0
        rank = 1

    if others_sum > 0:
        dominance = trump_by_name / others_sum
    elif trump_by_name > 0:
        dominance = float("inf")
    else:
        dominance = 0.0

    # None-safe breadth gate: a missing signal does not block a zone.
    breadth_ok = lambda floor: (floor is None) or (breadth is None) or (breadth >= floor)
    dominance_ok = lambda floor: (floor is None) or (dominance >= floor)

    def _fits(zone_key):
        t = THRESHOLDS[zone_key]
        return (
            rank <= (t["rank_max"] or 99)
            and pct >= (t["pct"] or 0)
            and dominance_ok(t["dominance"])
            and breadth_ok(t["breadth"])
        )

    if _fits("flooding"):
        chosen = "flooding"
    elif _fits("soaked"):
        chosen = "soaked"
    elif _fits("wet"):
        chosen = "wet"
    elif _fits("puddles"):
        chosen = "puddles"
    else:
        chosen = "dry"

    label, narrative = _PEOPLE_LABELS[chosen]
    return {
        "zone": chosen,
        "label": label,
        "narrative": narrative,
        "rank": rank,
        "n_people": n_people,
        "dominance": round(dominance, 2) if dominance != float("inf") else None,
        "breadth": round(breadth, 2) if breadth is not None else None,
        "deviation": round(deviation, 2) if deviation is not None else None,
        "smoothed_pct": smoothed_pct,
        "method": "composite",
        "thresholds_version": THRESHOLDS_VERSION,
    }


# Backwards-compatible alias so older callers keep working. The signature
# is a superset of the previous one.
def assess_people_based(trump_count, core_total, comparisons, smoothed_pct=None,
                         breadth=None, deviation=None):
    return assess_composite(
        trump_count, core_total, comparisons,
        breadth=breadth, deviation=deviation, smoothed_pct=smoothed_pct,
    )


# Original % thresholds (for backfilled records without theme data).
_PCT_RULES = [
    (5,    "dry"),
    (15,   "puddles"),
    (25,   "wet"),
    (40,   "soaked"),
    (1e9,  "flooding"),
]


def assess_pct_based(trump_count, total):
    pct = trump_count / total * 100 if total else 0.0
    chosen = "flooding"
    for cap, zone in _PCT_RULES:
        if pct < cap:
            chosen = zone
            break
    return {
        "zone": chosen,
        "label": ZONE_LABELS[chosen],
        "narrative": ZONE_NARRATIVES[chosen].format(rank="?", n="?"),
        "rank": None,
        "n_themes": None,
        "method": "pct",
    }
