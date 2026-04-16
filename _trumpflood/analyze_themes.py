#!/usr/bin/env python3
"""
Theme analysis: how many of today's Belgian headlines fall into broad
news categories, and how does Trump compare?

Themes are deliberately wide (multi-keyword regex per language) to give
an honest baseline. If 'sport' or 'politiek' dwarfs Trump, that recalibrates
how dramatic the Trump number really is.
"""
import re
from datetime import date

from comparators import COMPARATORS, count_matches as count_comparators
from fetcher import fetch_all

# Themes: NL + FR + EN keywords. Broad on purpose.
# (label, regex)
_THEMES = [
    ("Politics",        r"\b(politiek|politique|regering|gouvernement|parlement|kamer|senaat|s[ée]nat|minister|ministre|premier|president|coalitie|coalition|verkiezing|[ée]lection|partij|parti|kiezer|[ée]lecteur|votes?|stemmen|opposit(ie|ion))\b"),
    ("Economy/finance", r"\b(econom(ie|y|ique)|inflatie|inflation|beurs|bourse|werkloos|ch[oô]mage|sala(ris|ire)|bedrijf|entreprise|bank(en|s|aire)?|investeer|investiss|begrot(ing|aire)|budget|belasting|imp[oô]t|fiscaal|fiscal|btw|tva|prijs|prix|consument|consommat|export|import|handel|commerce)\b"),
    ("Sports",          r"\b(sport|voetbal|football|tennis|wielrenn|cyclis(me|te)|formule\s?1|f1|olympi(c|qu)|rugby|basket|hockey|atletiek|athl[ée]tisme|sporter|athl[ée]te|wedstrijd|match|tornooi|tournoi|kampioenschap|championnat|club|liga|ligue|competitie|comp[ée]tition|trainer|entra[iî]neur)\b"),
    ("Crime/justice",   r"\b(politie|police|misdaad|crime|crimine(el|l)|moord|meurtre|verdacht|suspect|gevangen|prison|veroordeel|condamn[eé]|rechter|juge|parket|parquet|gerecht|justice|advocaat|avocat|onderzoek|enqu[eê]te|drugs?|drogue|wapen|arme|geweld|violence|mishandel|agression)\b"),
    ("Health",          r"\b(gezondheid|sant[ée]|ziekenhuis|h[oô]pital|arts|m[ée]decin|patient|verpleeg|infirmi[eè]r|kanker|cancer|virus|epidem|pandem|vaccin|geneesm|m[eé]dicament|operatie|op[eé]ration|behandel|traitement|psych|ggz|covid)\b"),
    ("Education",       r"\b([ée]cole|school|onderwijs|enseignement|universit(eit|[ée])|leerling|[ée]l[eè]ve|student|[ée]tudiant|leraar|enseignant|professor|professeur|examen|diploma|diplome)\b"),
    ("Climate/energy",  r"\b(klimaat|climat|opwarming|r[eé]chauffement|broeikas|co2|emiss(ie|ion)|energie|[eé]nergie|stroom|[ée]lectricit[eé]|gas|nucleair|nucl[eé]aire|kernenerg|hernieuw|renouvelable|zonnepan|panneau\s?solaire|wind(molen|turbine)|[eé]olien|duurzaam|durable|milieu|environnement)\b"),
    ("Migration",       r"\b(migrant|migrat(ie|ion)|asiel|asile|vluchteling|r[eé]fugi[eé]|opvang|accueil|grens|fronti[eè]re|illegaal|sans\s?papiers?|fedasil|cgvs|cgra|nationaliteit|nationalit[eé])\b"),
    ("War/conflict",    r"\b(oorlog|guerre|war|conflict|conflit|leger|arm[ée]e|militair|militaire|raket|missile|drone|aanval|attaque|bombard|invas|oekra[iï]ne|ukraine|russisch|russe|gaza|israel|isra[eë]l|hamas|hezbollah|iran|jemen|sudan|soedan)\b"),
    ("EU politics",     r"\b(europa|europese|europees|europe|europ[eé]en(s|ne|nes)?|brussel|bruxelles|commission|commissie|navo|otan|nato|von der leyen|macron|merz|meloni|orban|orb[aá]n)\b"),
    ("Belgium gov",     r"\b(de wever|bouchez|magnette|rousseau|francken|jambon|crevits|coninck|prevot|fran[cç]ois|federale|f[eé]d[eé]rale|vlaams|vlaamse|wallon|wallonie|brussels|gewest|r[eé]gion)\b"),
    ("Tech/AI",         r"\b(ai|kunstmatige intelligentie|intelligence artificielle|chatgpt|openai|google|meta|x\.com|twitter|facebook|instagram|tiktok|cyber|hack|data\s?lek|fuite\s?de\s?donn[ée]es|app|smartphone|robot|tech|technologie|technologique)\b"),
    ("Culture/media",   r"\b(film|s[eé]rie|netflix|festival|concert|muziek|musique|kunst|art|expositie|exposition|theater|th[ée][aâ]tre|literat(uur|ure)|boek|livre|auteur|schrijver|cin[ée]ma|bioscoop|tv|t[eé]l[eé]vision|radio|programma|[ée]mission)\b"),
    ("Weather",         r"\b(weer|m[eé]t[eé]o|regen|pluie|sneeuw|neige|temperatuur|temp[eé]rature|hitte|chaleur|storm|temp[eê]te|onweer|orage|wind|vent|graden?|degr[eé]s?|zon|soleil|wolken|nuage)\b"),
]

THEMES = [(label, re.compile(pat, re.IGNORECASE)) for label, pat in _THEMES]


def main():
    today = date.today()
    print(f"Fetching today's RSS headlines ({today})...")
    results = fetch_all(today)

    seen = set()
    titles = []
    for src, payload in results.items():
        for url, title in payload["articles"]:
            if url in seen:
                continue
            seen.add(url)
            titles.append(title)

    n = len(titles)
    print(f"\n{n} unique headlines from today.\n")

    # Comparator counts (people)
    comp = count_comparators(titles)
    trump_count = comp["trump"]
    trump_pct = trump_count / n * 100 if n else 0

    # Theme counts (categories)
    theme_results = []
    for label, pat in THEMES:
        c = sum(1 for t in titles if pat.search(t))
        pct = c / n * 100 if n else 0
        theme_results.append((label, c, pct))
    theme_results.sort(key=lambda r: r[1], reverse=True)

    # Headlines that match NO theme (uncategorized)
    any_pat = re.compile("|".join(p.pattern for _, p in THEMES), re.IGNORECASE)
    uncategorized = [t for t in titles if not any_pat.search(t)]

    # === Print report ===
    print("=" * 64)
    print("THEMES (broad categories, multi-language regex)")
    print("=" * 64)
    print(f"{'Theme':<22} {'count':>6} {'share':>7}")
    print("-" * 44)
    for label, c, pct in theme_results:
        bar = "\u2588" * int(pct)
        print(f"{label:<22} {c:>6} {pct:>6.1f}%  {bar}")
    print(f"{'(uncategorized)':<22} {len(uncategorized):>6} {len(uncategorized)/n*100:>6.1f}%")

    print()
    print("=" * 64)
    print(f"TRUMP REFERENCE: {trump_count}/{n} = {trump_pct:.1f}%")
    print("=" * 64)
    print(f"Trump matches: {trump_count}")
    print(f"Top theme ({theme_results[0][0]}): {theme_results[0][1]} ({theme_results[0][2]:.1f}%)")
    print(f"Trump as fraction of top theme: {trump_count/max(theme_results[0][1],1)*100:.0f}%")

    # How does Trump rank among themes?
    rank = sum(1 for _, c, _ in theme_results if c > trump_count) + 1
    print(f"Trump would rank #{rank} if listed alongside the {len(theme_results)} themes")

    # Trump vs all comparators (non-trump people)
    others_total = sum(v for k, v in comp.items() if k != "trump")
    print()
    print("=" * 64)
    print("TRUMP vs OTHER PEOPLE")
    print("=" * 64)
    print(f"Trump:                      {trump_count}")
    print(f"Sum of other 7 comparators: {others_total}")
    if others_total:
        ratio = trump_count / others_total
        print(f"Trump / others ratio: {ratio:.2f}x")

    # Sample uncategorized so we can audit theme coverage
    print()
    print(f"Sample uncategorized (showing 10 of {len(uncategorized)}):")
    for t in uncategorized[:10]:
        print(f"  \u2022 {t[:110]}")


if __name__ == "__main__":
    main()
