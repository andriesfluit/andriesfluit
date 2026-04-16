"""
Theme classification for Belgian news headlines (NL + FR + EN regex).
Used to give context to the Trump number: how does one person compare
to broad subject categories?
"""
import re

# (key, display_label, regex)
_THEMES = [
    ("war",       "War/conflict",
     r"\b(oorlog|guerre|war|conflict|conflit|leger|arm[ée]e|militair|militaire|raket|missile|drone|aanval|attaque|bombard|invas|oekra[iï]ne|ukraine|russisch|russe|gaza|israel|isra[eë]l|hamas|hezbollah|iran|jemen|sudan|soedan)\b"),
    ("crime",     "Crime/justice",
     r"\b(politie|police|misdaad|crime|crimine(el|l)|moord|meurtre|verdacht|suspect|gevangen|prison|veroordeel|condamn[eé]|rechter|juge|parket|parquet|gerecht|justice|advocaat|avocat|onderzoek|enqu[eê]te|drugs?|drogue|wapen|arme|geweld|violence|mishandel|agression)\b"),
    ("eu",        "EU politics",
     r"\b(europa|europese|europees|europe|europ[eé]en(s|ne|nes)?|brussel|bruxelles|commission|commissie|navo|otan|nato|von der leyen|orban|orb[aá]n)\b"),
    ("politics",  "Politics",
     r"\b(politiek|politique|regering|gouvernement|parlement|kamer|senaat|s[ée]nat|minister|ministre|premier|president|coalitie|coalition|verkiezing|[ée]lection|partij|parti|kiezer|[ée]lecteur|votes?|stemmen|opposit(ie|ion))\b"),
    ("be_gov",    "Belgium gov",
     r"\b(de wever|bouchez|magnette|rousseau|francken|jambon|crevits|coninck|prevot|fran[cç]ois|federale|f[eé]d[eé]rale|vlaams|vlaamse|wallon|wallonie|gewest|r[eé]gion)\b"),
    ("culture",   "Culture/media",
     r"\b(film|s[eé]rie|netflix|festival|concert|muziek|musique|kunst|art|expositie|exposition|theater|th[ée][aâ]tre|literat(uur|ure)|boek|livre|auteur|schrijver|cin[ée]ma|bioscoop|tv|t[eé]l[eé]vision|radio|programma|[ée]mission)\b"),
    ("tech",      "Tech/AI",
     r"\b(ai|kunstmatige intelligentie|intelligence artificielle|chatgpt|openai|google|meta|x\.com|twitter|facebook|instagram|tiktok|cyber|hack|data\s?lek|fuite\s?de\s?donn[ée]es|app|smartphone|robot|tech|technologie|technologique)\b"),
    ("economy",   "Economy/finance",
     r"\b(econom(ie|y|ique)|inflatie|inflation|beurs|bourse|werkloos|ch[oô]mage|sala(ris|ire)|bedrijf|entreprise|bank(en|s|aire)?|investeer|investiss|begrot(ing|aire)|budget|belasting|imp[oô]t|fiscaal|fiscal|btw|tva|prijs|prix|consument|consommat|export|import|handel|commerce)\b"),
    ("sports",    "Sports",
     r"\b(sport|voetbal|football|tennis|wielrenn|cyclis(me|te)|formule\s?1|f1|olympi(c|qu)|rugby|basket|hockey|atletiek|athl[ée]tisme|sporter|athl[ée]te|wedstrijd|match|tornooi|tournoi|kampioenschap|championnat|club|liga|ligue|competitie|comp[ée]tition|trainer|entra[iî]neur)\b"),
    ("health",    "Health",
     r"\b(gezondheid|sant[ée]|ziekenhuis|h[oô]pital|arts|m[ée]decin|patient|verpleeg|infirmi[eè]r|kanker|cancer|virus|epidem|pandem|vaccin|geneesm|m[eé]dicament|operatie|op[eé]ration|behandel|traitement|psych|ggz|covid)\b"),
    ("climate",   "Climate/energy",
     r"\b(klimaat|climat|opwarming|r[eé]chauffement|broeikas|co2|emiss(ie|ion)|energie|[eé]nergie|stroom|[ée]lectricit[eé]|gas|nucleair|nucl[eé]aire|kernenerg|hernieuw|renouvelable|zonnepan|panneau\s?solaire|wind(molen|turbine)|[eé]olien|duurzaam|durable|milieu|environnement)\b"),
    ("migration", "Migration",
     r"\b(migrant|migrat(ie|ion)|asiel|asile|vluchteling|r[eé]fugi[eé]|opvang|accueil|grens|fronti[eè]re|illegaal|sans\s?papiers?|fedasil|cgvs|cgra|nationaliteit|nationalit[eé])\b"),
    ("education", "Education",
     r"\b([ée]cole|school|onderwijs|enseignement|universit(eit|[ée])|leerling|[ée]l[eè]ve|student|[ée]tudiant|leraar|enseignant|professor|professeur|examen|diploma|diplome)\b"),
    ("weather",   "Weather",
     r"\b(weer|m[eé]t[eé]o|regen|pluie|sneeuw|neige|temperatuur|temp[eé]rature|hitte|chaleur|storm|temp[eê]te|onweer|orage|graden?|degr[eé]s?)\b"),
]

THEMES = [
    {"key": k, "label": label, "pattern": re.compile(pat, re.IGNORECASE)}
    for k, label, pat in _THEMES
]


def count_matches(titles):
    """Return {key: count} for each theme. Themes are not mutually exclusive
    (a headline can match multiple themes)."""
    titles = list(titles)
    out = {}
    for t in THEMES:
        out[t["key"]] = sum(1 for title in titles if t["pattern"].search(title or ""))
    return out


def label_for(key):
    for t in THEMES:
        if t["key"] == key:
            return t["label"]
    return key
