"""Registry of e-paper sources (all on the Twipe platform).

Adding a source is just adding an entry here: same JSON structure, same public
CDN, same +2/day edition-ID pattern. `seed_id`/`seed_date` anchor the edition
predictor on first run; after that the per-source state file takes over.

`days` lists the weekdays a title is published (Mon=0 … Sun=6); the run skips a
source on any other day. De Standaard: ma–za. De Tijd: di–za (geen maandag,
geen zondag).
"""

# Weekday constants (date.weekday(): Monday=0 … Sunday=6).
MA, DI, WO, DO, VR, ZA, ZO = 0, 1, 2, 3, 4, 5, 6

SOURCES = {
    "destandaard": {
        "key": "destandaard",
        "short": "ds",
        "label": "De Standaard",
        "base": "https://epaper.standaard.be",
        "seed_id": 3307,
        "seed_date": "2026-06-26",
        "days": {MA, DI, WO, DO, VR, ZA},
    },
    "detijd": {
        "key": "detijd",
        "short": "dt",
        "label": "De Tijd",
        "base": "https://krant.tijd.be",
        "seed_id": 3330,
        "seed_date": "2026-06-26",
        "days": {DI, WO, DO, VR, ZA},
    },
}

# Order the nightly run and the web reader present the sources in.
ORDER = ["destandaard", "detijd"]


def get(key):
    return SOURCES[key]
