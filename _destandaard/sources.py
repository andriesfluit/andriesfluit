"""Registry of e-paper sources (all on the Twipe platform).

Adding a source is just adding an entry here: same JSON structure, same public
CDN, same +2/day edition-ID pattern. `seed_id`/`seed_date` anchor the edition
predictor on first run; after that the per-source state file takes over.
"""

SOURCES = {
    "destandaard": {
        "key": "destandaard",
        "short": "ds",
        "label": "De Standaard",
        "base": "https://epaper.standaard.be",
        "seed_id": 3307,
        "seed_date": "2026-06-26",
    },
    "detijd": {
        "key": "detijd",
        "short": "dt",
        "label": "De Tijd",
        "base": "https://krant.tijd.be",
        "seed_id": 3330,
        "seed_date": "2026-06-26",
    },
}

# Order the nightly run and the web reader present the sources in.
ORDER = ["destandaard", "detijd"]


def get(key):
    return SOURCES[key]
