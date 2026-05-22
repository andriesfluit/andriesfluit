"""Companies to monitor.

Each company has one or more match rules. A rule fires on a (title, source)
pair when:
  - at least one pattern in `any` matches the title, AND
  - if `context_any` is set: at least one of those patterns also matches the title, AND
  - if `none` is set: none of those patterns match the title.

An article hits a company when any of its rules fires. Title-only matching is
intentionally loose; the LLM relevance filter (filter_llm.py) does the second
pass and rejects false positives. Patterns are case-insensitive (we compile
with re.IGNORECASE).
"""

COMPANIES = {
    "ikea_be": {
        "label": "IKEA België",
        "rules": [
            {
                "any": [r"\bIKEA\b"],
                # IKEA worldwide is huge — restrict to Belgian context in the
                # title. The Claude filter still gets the call on edge cases.
                "context_any": [
                    r"\bBelgi[ëe]\b",
                    r"\bBelgique\b",
                    r"\bAnderlecht\b",
                    r"\bArlon\b",
                    r"\bMons\b",
                    r"\bGent\b",
                    r"\bWilrijk\b",
                    r"\bZaventem\b",
                    r"\bHognoul\b",
                    r"\bMaasmechelen\b",
                    r"\bHasselt\b",
                    r"\bBrugge\b",
                    r"\bBrussel\b",
                    r"\bBruxelles\b",
                ],
            },
        ],
    },
    "accent": {
        "label": "Accent (Jobs / Group / Construct / Logistics / Industry / Select / Business)",
        "rules": [
            {
                "any": [
                    r"\bAccent\s+Jobs(\s+for\s+People)?\b",
                    r"\bAccent\s+Group\b",
                    r"\bAccent\s+Construct\b",
                    r"\bAccent\s+Logistics\b",
                    r"\bAccent\s+Industry\b",
                    r"\bAccent\s+Select\b",
                    r"\bAccent\s+Business\b",
                ],
            },
        ],
    },
    "nowjobs": {
        "label": "NowJobs",
        "rules": [
            {"any": [r"\bNowJobs\b", r"\bNow\s+Jobs\b"]},
        ],
    },
    "helios": {
        "label": "Helios Foundation",
        "rules": [
            {
                "any": [
                    r"\bHelios\s+Foundation\b",
                    r"\bStichting\s+Helios\b",
                    r"\bFondation\s+Helios\b",
                ],
                # Explicitly NOT linking to the King Baudouin Foundation —
                # any article framing Helios primarily via KBF is filtered.
                "none": [
                    r"\bKoning\s+Boudewijnstichting\b",
                    r"\bFondation\s+Roi\s+Baudouin\b",
                    r"\bKing\s+Baudouin\s+Foundation\b",
                ],
            },
        ],
    },
    "bva_abpe": {
        "label": "BVA / ABPE (Belgische Vereniging van Asfaltproducenten)",
        "rules": [
            # Full names always count.
            {
                "any": [
                    r"Belgische\s+Vereniging\s+van\s+Asfaltproducenten",
                    r"Association\s+Belge\s+des\s+Producteurs\s+d['’]Enrob[ée]s?",
                ],
            },
            # Acronym-only — BVA and ABPE collide with other entities (BVA
            # market research, etc.), so require asphalt/road-construction
            # context in the title.
            {
                "any": [r"\bABPE\b", r"\bBVA\b"],
                "context_any": [
                    r"\basfalt",
                    r"\benrob[ée]",
                    r"\basphalte",
                    r"\bbitume",
                    r"\bwegenbouw",
                    r"\bvoirie",
                    r"\bweginfrastructuur\b",
                ],
            },
        ],
    },
}
