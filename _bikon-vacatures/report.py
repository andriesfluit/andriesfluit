"""Fase 3: output/vacatures.csv en output/samenvatting.md maken uit fase 1 en 2.

Gebruik:
    python report.py

Geen netwerkverkeer en geen kosten: je kan dit zo vaak draaien als je wil.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict
from datetime import datetime

import common
from classify import EFFORT, MODEL, PROMPT_VERSION, load_classifications

CSV_FILE = common.OUTPUT_DIR / "vacatures.csv"
SUMMARY_FILE = common.OUTPUT_DIR / "samenvatting.md"
CSV_COLUMNS = [
    "bedrijf", "titel", "bron", "url", "datum", "plaats", "zoekterm", "relevant", "signaaltype",
    "rol_organisatie", "sector", "gereguleerd", "score", "motivatie", "recruiter_vlag", "tekst_onvolledig",
]

# Organisatiescore: de hoogste score van de relevante vacatures, plus 0,5 per extra relevante
# vacature (hoogstens +1,5). Zo telt een organisatie met meerdere vacatures als sterker signaal.
EXTRA_PER_JOB = 0.5
MAX_EXTRA = 1.5
TOP_N = 25
NOISE_THRESHOLD = 0.20  # minder dan 20% relevant = veel ruis
MIN_FOR_NOISE = 5  # pas oordelen vanaf 5 vacatures


def joined(text: str | None) -> str:
    return (text or "").replace("; ", ", ")


def build_rows(jobs: list[dict], classified: dict[str, dict]) -> list[dict]:
    rows = []
    for job in jobs:
        c = classified.get(job["job_id"])
        if not c:
            continue
        rows.append(
            {
                "bedrijf": job.get("bedrijf") or "",
                "titel": job.get("titel") or "",
                "bron": joined(job.get("bron")),
                "url": job.get("url") or "",
                "datum": job.get("datum") or "",
                "plaats": job.get("plaats") or "",
                "zoekterm": joined(job.get("zoekterm")),
                "relevant": c["relevant"],
                "signaaltype": ", ".join(c["signaaltype"]),
                "rol_organisatie": c["rol_organisatie"],
                "sector": c["sector"],
                "gereguleerd": c["gereguleerd"],
                "score": c["score"],
                "motivatie": c["motivatie"],
                "recruiter_vlag": "ja" if job.get("recruiter_vlag") else "",
                # Enkel via Adzuna gevonden: de tekst was afgekapt op 500 tekens.
                "tekst_onvolledig": "ja" if job.get("bron") == "adzuna" else "",
                "_signalen": c["signaaltype"],
                "_termen": (job.get("zoekterm") or "").split("; "),
                "_bronnen": (job.get("bron") or "").split("; "),
            }
        )
    rows.sort(key=lambda r: (-r["score"], r["relevant"] != "ja", r["bedrijf"].lower(), r["titel"].lower()))
    return rows


def write_csv(rows: list[dict]) -> None:
    common.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Puntkomma en BOM: zo opent Excel met Belgische instellingen het bestand meteen in kolommen.
    with CSV_FILE.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def org_ranking(rows: list[dict]) -> list[dict]:
    orgs: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["relevant"] == "ja" and not r["recruiter_vlag"]:
            orgs[common.normalize_company(r["bedrijf"]) or r["bedrijf"].lower()].append(r)
    ranking = []
    for jobs in orgs.values():
        jobs.sort(key=lambda r: -r["score"])
        best = jobs[0]
        extra = min(MAX_EXTRA, EXTRA_PER_JOB * (len(jobs) - 1))
        ranking.append(
            {
                "naam": Counter(j["bedrijf"] for j in jobs).most_common(1)[0][0],
                "orgscore": best["score"] + extra,
                "aantal": len(jobs),
                "hoogste": best["score"],
                "gemiddelde": sum(j["score"] for j in jobs) / len(jobs),
                "rol": ", ".join(sorted({j["rol_organisatie"] for j in jobs})),
                "sector": Counter(j["sector"] for j in jobs).most_common(1)[0][0],
                "gereguleerd": "ja" if any(j["gereguleerd"] == "ja" for j in jobs) else "nee",
                "signalen": ", ".join(s for s in common.SEARCH_TERMS if any(s in j["_signalen"] for j in jobs)),
                "titels": [j["titel"] for j in jobs[:2]],
                "motivatie": best["motivatie"],
                "onvolledig": best["tekst_onvolledig"] == "ja",
            }
        )
    ranking.sort(key=lambda o: (-o["orgscore"], -o["aantal"], -o["gemiddelde"], o["naam"].lower()))
    return ranking


def md_cell(value) -> str:
    return str(value).replace("|", "/").replace("\n", " ")


def md_table(headers: list[str], rows: list[list]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(md_cell(c) for c in row) + " |" for row in rows]
    return lines + [""]


def pct(part: int, total: int) -> str:
    return f"{100 * part / total:.0f}%" if total else "-"


def build_summary(rows: list[dict], ranking: list[dict], unclassified: int) -> str:
    relevant = [r for r in rows if r["relevant"] == "ja"]
    out = [f"# Samenvatting vacaturetest ({datetime.now():%Y-%m-%d})", ""]

    out += ["## Kern", ""]
    out += [
        f"- {len(relevant)} van de {len(rows)} unieke vacatures zijn relevant ({pct(len(relevant), len(rows))}).",
        f"- Die komen van {len(ranking)} organisaties (zonder recruitmentbureaus en interimkantoren).",
        f"- Gereguleerde sector: {sum(r['gereguleerd'] == 'ja' for r in relevant)} van de relevante vacatures.",
        f"- Score 4 of 5: {sum(r['score'] >= 4 for r in relevant)} relevante vacatures.",
        "",
    ]

    out += ["## Relevante vacatures per signaaltype", "", "Een vacature kan meerdere signaaltypes hebben.", ""]
    signals = Counter(s for r in relevant for s in r["_signalen"])
    out += md_table(["signaaltype", "vacatures", "aandeel"],
                    [[s, signals[s], pct(signals[s], len(relevant))] for s in common.SEARCH_TERMS])

    out += ["## Relevante vacatures per sector", ""]
    sectors = Counter(r["sector"] for r in relevant)
    out += md_table(["sector", "vacatures", "waarvan score 4-5"],
                    [[s, n, sum(r["score"] >= 4 for r in relevant if r["sector"] == s)] for s, n in sectors.most_common()])

    out += ["## Relevante vacatures per rol van de organisatie", ""]
    roles = Counter(r["rol_organisatie"] for r in relevant)
    out += md_table(["rol", "vacatures", "aandeel"], [[k, n, pct(n, len(relevant))] for k, n in roles.most_common()])

    out += [f"## Top {TOP_N} organisaties", ""]
    out += [
        f"Organisatiescore = hoogste score van haar relevante vacatures + {EXTRA_PER_JOB:g} per extra relevante "
        f"vacature (hoogstens +{MAX_EXTRA:g}). Recruitmentbureaus en interimkantoren tellen niet mee.",
        "",
    ]
    out += md_table(
        ["#", "organisatie", "orgscore", "relevante vacatures", "rol", "sector", "gereg.", "signaaltypes",
         "voorbeelden", "motivatie (beste vacature)"],
        [
            [i, o["naam"], f"{o['orgscore']:g}", o["aantal"], o["rol"], o["sector"], o["gereguleerd"], o["signalen"],
             " / ".join(o["titels"]), o["motivatie"] + (" (tekst onvolledig)" if o["onvolledig"] else "")]
            for i, o in enumerate(ranking[:TOP_N], start=1)
        ],
    )

    out += ["## Ruis per zoekterm", ""]
    out += [
        "Per zoekterm: hoeveel unieke vacatures ze opleverde en welk deel daarvan relevant is. Een vacature die "
        f"via meerdere zoektermen binnenkwam, telt bij elk ervan. 'Veel ruis' = minder dan {NOISE_THRESHOLD:.0%} "
        f"relevant, bij minstens {MIN_FOR_NOISE} vacatures.",
        "",
    ]
    term_rows = []
    for term in common.ALL_TERMS:
        found = [r for r in rows if term in r["_termen"]]
        hits = [r for r in found if r["relevant"] == "ja"]
        share = len(hits) / len(found) if found else 0
        if len(found) < MIN_FOR_NOISE:
            verdict = "te weinig resultaten"
        elif share < NOISE_THRESHOLD:
            verdict = "veel ruis"
        else:
            verdict = ""
        term_rows.append((share, len(found), [term, common.TERM_CATEGORY[term], len(found), len(hits), pct(len(hits), len(found)), verdict]))
    term_rows.sort(key=lambda t: (t[1] < MIN_FOR_NOISE, t[0]))
    out += md_table(["zoekterm", "categorie", "vacatures", "relevant", "aandeel relevant", "oordeel"], [t[2] for t in term_rows])

    out += ["## Relevant per bron", "", "Een vacature die op meerdere bronnen stond, telt bij elk ervan.", ""]
    source_rows = []
    for source in ("indeed", "glassdoor", "linkedin", "adzuna"):
        found = [r for r in rows if source in r["_bronnen"]]
        hits = sum(r["relevant"] == "ja" for r in found)
        only = [r for r in found if r["_bronnen"] == [source]]
        source_rows.append([source, len(found), hits, pct(hits, len(found)), len(only)])
    out += md_table(["bron", "vacatures", "relevant", "aandeel relevant", "enkel op deze bron"], source_rows)

    incomplete = [r for r in rows if r["tekst_onvolledig"]]
    recruiters = [r for r in rows if r["recruiter_vlag"]]
    out += ["## Kanttekeningen", ""]
    out += [
        "- LinkedIn is maar voor 6 van de 27 zoektermen doorzocht: daarna gaf het een rate limit (HTTP 429) "
        "en werd het volgens de regels overgeslagen.",
        f"- {len(incomplete)} vacatures kwamen enkel via Adzuna en zijn beoordeeld op de eerste 500 tekens "
        f"(kolom tekst_onvolledig); {sum(r['relevant'] == 'ja' for r in incomplete)} daarvan zijn relevant. "
        "Bij de andere kan een relevant signaal gemist zijn.",
        f"- {len(recruiters)} vacatures hebben een recruitervlag; ze staan in de CSV maar tellen niet mee in de top {TOP_N}.",
        f"- Classificatie: {MODEL}, effort {EFFORT}, promptversie {PROMPT_VERSION}. Het model is niet volledig "
        "voorspelbaar: twijfelgevallen kunnen tussen twee runs één punt verschuiven.",
        "- Integrators zijn gescoord als mogelijke klant voor RaaS, niet als concurrent.",
        "- Persoonsgegevens zijn met patronen uit de teksten gehaald; dat is niet waterdicht.",
    ]
    if unclassified:
        out.append(f"- {unclassified} vacatures zijn nog niet geclassificeerd en ontbreken hier. Draai classify.py opnieuw.")
    return "\n".join(out) + "\n"


def main() -> None:
    if not common.JOBS_FILE.exists():
        sys.exit("data/vacatures.jsonl ontbreekt. Draai eerst collect.py en classify.py.")
    jobs = common.read_jsonl(common.JOBS_FILE)
    classified = load_classifications()
    rows = build_rows(jobs, classified)
    if not rows:
        sys.exit("Nog geen classificaties met de huidige prompt. Draai eerst classify.py.")
    write_csv(rows)
    ranking = org_ranking(rows)
    summary = build_summary(rows, ranking, len(jobs) - len(rows))
    SUMMARY_FILE.write_text(summary, encoding="utf-8")
    print(summary)
    print(f"Opgeslagen: output/vacatures.csv ({len(rows)} vacatures) en output/samenvatting.md")


if __name__ == "__main__":
    main()
