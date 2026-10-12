"""Vacatureteksten van een selectie organisaties in één bestand, als basis voor fiches per organisatie.

Gebruik:
    python fiches.py                        # de 10 organisaties uit de shortlist
    python fiches.py Argenta "Delen Private Bank"   # een eigen selectie

Schrijft output/fiches_input.md. Geen netwerkverkeer en geen kosten.
"""

from __future__ import annotations

import sys

import common
from classify import load_classifications

SHORTLIST = [
    "Delen Private Bank", "Argenta", "Baloise", "Partenamut", "Mutualité chrétienne",
    "Europ Assistance", "Mega", "Projective Group", "Capco", "EY",
]
MAX_TEXT = 8000  # tekens per vacaturetekst; langere teksten worden ingekort en zo gemarkeerd
FICHES_FILE = common.OUTPUT_DIR / "fiches_input.md"


def matches(query: str, company: str | None) -> bool:
    """Alle woorden van de zoeknaam komen als los woord voor in de bedrijfsnaam."""
    wanted = common.normalize_company(query).split()
    words = set(common.normalize_company(company).split())
    return bool(wanted) and all(w in words for w in wanted)


def org_section(query: str, jobs: list[dict], classified: dict[str, dict]) -> list[str]:
    found = [j for j in jobs if matches(query, j.get("bedrijf")) and j["job_id"] in classified]
    found.sort(key=lambda j: -classified[j["job_id"]]["score"])
    relevant = [j for j in found if classified[j["job_id"]]["relevant"] == "ja"]
    names = sorted({j["bedrijf"] for j in found})
    out = [f"# {query}", ""]
    if not found:
        return out + ["Geen vacatures gevonden.", ""]
    out += [
        f"Namen in de data: {', '.join(names)}",
        f"Vacatures: {len(found)}, waarvan {len(relevant)} relevant.",
        "",
    ]
    others = [j for j in found if j not in relevant]
    if others:
        out += ["Andere (niet relevante) vacatures van deze organisatie:"]
        out += [f"- {j['titel']} ({j.get('plaats') or 'plaats onbekend'})" for j in others]
        out.append("")
    for j in relevant:
        c = classified[j["job_id"]]
        text = (j.get("beschrijving") or "").strip()
        if len(text) > MAX_TEXT:
            text = text[:MAX_TEXT] + f"\n[... ingekort, {len(text) - MAX_TEXT} tekens weggelaten]"
        out += [
            f"## {j['titel']}",
            "",
            f"- Plaats: {j.get('plaats') or '-'} | datum: {j.get('datum') or '-'} | bron: {j.get('bron')}",
            f"- URL: {j.get('url')}",
            f"- Score {c['score']}, signaaltype {', '.join(c['signaaltype']) or '-'}, rol {c['rol_organisatie']}, "
            f"sector {c['sector']}, gereguleerd {c['gereguleerd']}",
            f"- Motivatie model: {c['motivatie']}",
            "",
            "Vacaturetekst:",
            "",
            text or "(geen tekst)",
            "",
        ]
    return out


def main() -> None:
    queries = sys.argv[1:] or SHORTLIST
    if not common.JOBS_FILE.exists():
        sys.exit("data/vacatures.jsonl ontbreekt. Draai eerst collect.py en classify.py.")
    jobs = common.read_jsonl(common.JOBS_FILE)
    classified = load_classifications()
    lines = ["Vacatureteksten per organisatie (persoonsgegevens verwijderd in fase 1).", ""]
    for query in queries:
        lines += org_section(query, jobs, classified)
    common.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FICHES_FILE.write_text("\n".join(lines), encoding="utf-8")
    size = FICHES_FILE.stat().st_size
    print(f"Opgeslagen: output/fiches_input.md ({len(queries)} organisaties, {size // 1000} kB).")


if __name__ == "__main__":
    main()
