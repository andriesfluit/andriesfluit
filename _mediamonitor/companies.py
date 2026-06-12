"""Topic profiles per company — issue monitoring, not brand monitoring.

For each company we list a BRIEF (used by the LLM filter to judge strategic
relevance), a flat list of regex PATTERNS that cast a wide net for matching
articles pulled from outlet feeds, and SEARCH_TERMS that get expanded into
per-company Google News search feeds (NL + FR Belgian locale, quoted exact
phrases to dodge word collisions like 'accent').

Patterns are case-insensitive and use word-boundary semantics (matcher.py
compiles with re.IGNORECASE). Multilingual where it matters (NL + FR).

Discipline:
  - patterns: include brand + direct competitors + sector verticals +
    regulatory levers + adjacent themes where a reaction (actie /
    interne comms / externe comms) is plausible.
  - search_terms: 4 categories (brand / competitors / policy / broad).
    Categories have no runtime effect — they're for tuning only.
    Every term is queried as an exact phrase ("...") in both nl-BE and
    fr-BE Google News locales.
  - Do NOT include generic words that drown the LLM ('Belgium', 'werk').
"""

COMPANIES = {
    # -----------------------------------------------------------------
    "ikea_be": {
        "label": "IKEA België",
        "brief": (
            "Zweedse meubel- en woninginrichtingsketen, Belgische tak met 8 "
            "winkels (Anderlecht, Zaventem, Wilrijk, Gent, Hognoul, Mons, "
            "Arlon, Hasselt) + online. Strategische thema's: woninginrichting, "
            "retail, duurzame productie, circulariteit, supply chain, "
            "koopkracht en consumentengedrag, e-commerce/omnichannel, "
            "winkelvastgoed, retailwerkgelegenheid, mobiliteit naar winkels. "
            "NIET relevant: nieuws over IKEA of meubelconcurrenten in het "
            "buitenland — vooral Frankrijk (Franse winkels, Franse promoties, "
            "Franse arbeidsconflicten, Franse rechtszaken) — tenzij het "
            "expliciete gevolgen heeft voor België of voor IKEA België "
            "(bv. een internationale terugroepactie, een groepsstrategie "
            "die ook Belgische winkels raakt)."
        ),
        "patterns": [
            # Brand
            r"\bIKEA\b",
            # Directe concurrenten (meubel / woninginrichting)
            r"\bMaisons\s+du\s+Monde\b", r"\bJYSK\b", r"\bKwantum\b",
            r"\bCasa\b\s+(?:winkel|magasin|store)", r"\bConforama\b",
            r"\bBUT\b\s+(?:meubel|mobilier)", r"\bAlinea\b",
            # Bredere concurrentiële context
            r"\bBrico\b", r"\bHubo\b", r"\bAction\b\s+(?:winkel|store|filiale)",
            r"\bVinted\b", r"\bTroc\b",
            # Sector — meubel & wonen
            r"\bmeubel", r"\bmobilier\b", r"\binterieur(?:trend)?\b",
            r"\bwoninginrichting\b", r"\bd[ée]coration\s+int[ée]rieure\b",
            r"\bameublement\b",
            # Retail België
            r"\bdetailhandel\b", r"\bretailsector\b", r"\bretailmarkt\b",
            r"\bwinkelketen\b", r"\bcha[îi]ne\s+de\s+magasins\b",
            r"\bComeos\b",  # federatie Belgische handel
            # Circulariteit / duurzaamheid
            r"\bcirculaire?\s+economie\b", r"\b[ée]conomie\s+circulaire\b",
            r"\bkringloop", r"\btweedehands\s+meubel",
            r"\brecyclage\s+meubel", r"\bduurzame?\s+productie\b",
            # Vastgoed / winkels
            r"\bwinkelvastgoed\b", r"\bretail\s+park\b", r"\bbaanwinkel",
            r"\bwinkelopening", r"\bwinkelsluiting", r"\bouverture\s+(?:de\s+)?magasin\b",
            # Beleid / koopkracht
            r"\bkoopkracht\b", r"\bpouvoir\s+d[''']achat\b",
            r"\bindexering\s+lonen", r"\bverpakkingstaks\b",
            r"\bkinderarbeid\b", r"\btravail\s+des\s+enfants\b",
        ],
        "search_terms": {
            # City-specific brand searches were intentionally dropped — exact
            # phrases like "IKEA Anderlecht" rarely appear; articles say
            # "IKEA opent in Anderlecht" instead. The outlet-feed scan already
            # picks those up via the \bIKEA\b + Belgian anchor pattern.
            "brand": [
                "IKEA België", "IKEA Belgique",
            ],
            "competitors": [
                "Maisons du Monde", "JYSK", "Kwantum", "Conforama",
            ],
            "policy": [
                "verpakkingstaks meubels",
                "circulaire economie meubels",
                "économie circulaire ameublement",
                "kinderarbeid retail",
            ],
            "broad": [
                "meubelmarkt België",
                "marché du meuble Belgique",
                "detailhandel België",
                "retailsector België",
            ],
        },
    },

    # -----------------------------------------------------------------
    "accent_nowjobs": {
        "label": "Accent + NowJobs (House of HR)",
        "brief": (
            "Accent is de Belgische uitzendgroep met o.a. Accent Jobs, Accent "
            "Group, Accent Construct, Logistics, Industry, Select, Business. "
            "NowJobs is hun digitale studenten-/flexjob-platform. Onderdeel "
            "van House of HR. Strategische thema's: uitzendarbeid, krapte op "
            "Belgische arbeidsmarkt, jongeren- en studentenwerk, flexi-jobs, "
            "arbeidsdeal, arbeidsmigratie, HR-tech, gig economy, "
            "diversiteit/inclusie op werkvloer."
        ),
        "patterns": [
            # Brand
            r"\bAccent\s+Jobs(\s+for\s+People)?\b",
            r"\bAccent\s+Group\b", r"\bAccent\s+Construct\b",
            r"\bAccent\s+Logistics\b", r"\bAccent\s+Industry\b",
            r"\bAccent\s+Select\b", r"\bAccent\s+Business\b",
            r"\bNowJobs\b", r"\bNow\s+Jobs\b", r"\bHouse\s+of\s+HR\b",
            # Concurrenten
            r"\bRandstad\b", r"\bAdecco\b", r"\bManpower\b", r"\bTempo[- ]Team\b",
            r"\bASAP\.be\b", r"\bDaoust\b", r"\bSynergie\b", r"\bKonvert\b",
            r"\bUSG\b", r"\bUnique\b\s+(?:uitzend|int[eé]rim)",
            # Federaties / sectorpers
            r"\bFederg[oó]n\b", r"\bAgoria\b\s+(?:HR|arbeidsmarkt)",
            # Sector kern
            r"\buitzend(?:arbeid|sector|kantoor|bureau|werk)\b",
            r"\bint[eé]rim\b", r"\btravail\s+int[eé]rimaire\b",
            r"\barbeidsmarkt\b", r"\bmarch[eé]\s+du\s+travail\b",
            r"\bkrapte\b\s+(?:op\s+)?(?:de\s+)?arbeidsmarkt",
            r"\bp[eé]nurie\s+(?:de\s+)?main[- ]d[''']œuvre\b",
            r"\bvacature", r"\boffres?\s+d['']emploi\b",
            # Jongeren / studenten / flexi
            r"\bstudentenarbeid\b", r"\btravail\s+étudiant\b",
            r"\bjobstudent", r"\bjob\s+d['']étudiant\b",
            r"\bflexi[- ]?job", r"\bjongerentewerkstelling\b",
            # Beleid / regelgeving
            r"\barbeidsdeal\b", r"\bdeal\s+pour\s+l['']emploi\b",
            r"\bRSZ\b", r"\bONSS\b",
            r"\bschijnzelfstandig", r"\bfaux\s+ind[eé]pendant",
            r"\bpayroll", r"\barbeidsmigratie\b", r"\bmigration\s+du\s+travail\b",
            r"\bgig\s+economy\b", r"\bplatformwerk\b", r"\btravail\s+de\s+plateforme\b",
            # Maatschappelijk / werkvloer
            r"\bdiversiteit\s+(?:op\s+)?(?:de\s+)?werkvloer\b",
            r"\bdiversit[eé]\s+au\s+travail\b",
            r"\bburn[- ]?out\b", r"\bhybride\s+werk\b", r"\bt[eé]l[eé]travail\b",
            r"\bgeneratie\s+Z\b", r"\bg[eé]n[eé]ration\s+Z\b",
        ],
        "search_terms": {
            "brand": [
                "Accent Jobs", "Accent Group",
                "Accent Construct", "Accent Logistics", "Accent Industry",
                "Accent Select", "Accent Business",
                "NowJobs", "House of HR",
            ],
            "competitors": [
                "Randstad België", "Adecco België", "Manpower België",
                "Tempo-Team", "Federgon",
                "Daoust", "Synergie interim", "Konvert", "ASAP.be",
            ],
            "policy": [
                "flexi-jobs", "flexi-jobs uitbreiding",
                "arbeidsdeal", "deal pour l'emploi",
                "studentenarbeid", "travail étudiant",
                "schijnzelfstandigheid", "faux indépendant",
                "arbeidsmigratie België",
            ],
            "broad": [
                "krapte arbeidsmarkt",
                "pénurie main d'œuvre Belgique",
                "uitzendsector België",
                "secteur intérim Belgique",
                "jongerentewerkstelling",
            ],
        },
    },

    # -----------------------------------------------------------------
    "helios": {
        "label": "Helios Foundation",
        "brief": (
            "Belgische private stichting opgericht ter ondersteuning van "
            "decarbonisatie en mental well-being op het werk. Lanceerde "
            "België's grootste private klimaatinitiatief (€2-3M per project, "
            "ambitie 100 Mt CO2 vermijden tegen 2050). Steunt o.a. SWIFT-chair "
            "ULB/VUB (€10,6M), STEAM-chair, decarbonisatie-challenge, ULB "
            "groene campus. Strategische thema's: klimaatbeleid België, "
            "private filantropie voor klimaat, decarbonisatie industrie, "
            "duurzame transitie, mental health op het werk, wetenschappelijk "
            "onderzoek klimaat. NIET koppelen aan Koning Boudewijnstichting."
        ),
        "patterns": [
            # Brand
            r"\bHelios\s+Foundation\b",
            r"\bStichting\s+Helios\b", r"\bFondation\s+Helios\b",
            # Klimaat / decarbonisatie
            r"\bdecarbonisatie\b", r"\bd[eé]carbonation\b", r"\bdecarbonization\b",
            r"\bnet[- ]zero\b", r"\bnetto[- ]?nul\b",
            r"\bklimaatbeleid\b", r"\bpolitique\s+climatique\b",
            r"\bklimaatakkoord\b", r"\baccord\s+climat",
            r"\bCO2[- ]uitstoot\b", r"\b[eé]mission[s]?\s+(?:de\s+)?CO2\b",
            r"\bbroeikasgas\b", r"\bgaz\s+à\s+effet\s+de\s+serre\b",
            r"\benergietransitie\b", r"\btransition\s+énergétique\b",
            r"\bklimaatdoelstelling", r"\bobjectifs?\s+climat",
            # Belgische klimaatcontext
            r"\bElia\b", r"\bFluvius\b",  # netbeheer-context
            r"\bChapter\s+Zero\b",  # peer-netwerk Brussel
            r"\bFebeg\b", r"\bEssenscia\b",  # energie/industrie federaties
            # Private filantropie & ESG
            r"\bprivate?\s+filantropie\b", r"\bphilanthropie\s+priv[eé]e\b",
            r"\bimpact\s+investing\b", r"\bESG\b",
            r"\bmaatschappelijk\s+verantwoord", r"\bresponsabilit[eé]\s+sociétale\b",
            # Academisch / research
            r"\bULB\b\s+(?:klimaat|d[eé]carbon|duurzaam|sustain)",
            r"\bVUB\b\s+(?:klimaat|d[eé]carbon|duurzaam|sustain)",
            r"\bSWIFT\b\s+(?:chair|leerstoel)", r"\bSTEAM\b\s+(?:chair|leerstoel)",
            # Mental well-being op het werk
            r"\bmentaal\s+welzijn\b\s+(?:op\s+)?(?:het\s+)?werk",
            r"\bbien[- ]être\s+mental\b\s+au\s+travail",
            r"\bwerknemerswelzijn\b", r"\bworkplace\s+mental\s+(?:health|wellbeing)\b",
            r"\bburn[- ]?out\b", r"\bpsychosociale?\s+risico",
        ],
        "search_terms": {
            "brand": [
                "Helios Foundation", "Fondation Helios", "Stichting Helios",
            ],
            "competitors": [
                "Chapter Zero Brussels",
                "Essenscia decarbonisatie",
                "SWIFT chair ULB VUB",
                "STEAM chair VUB",
            ],
            "policy": [
                "klimaatakkoord België industrie",
                "accord climat industrie Belgique",
                "net zero België",
                "decarbonisatie Belgische industrie",
                "décarbonation industrie belge",
                "workplace mental health België",
                "bien-être mental travail Belgique",
            ],
            "broad": [
                "private filantropie klimaat",
                "philanthropie privée climat",
                "ESG België",
                "burn-out preventie werkgevers",
                "prévention burn-out employeurs",
            ],
        },
    },

    # -----------------------------------------------------------------
    "bva_abpe": {
        "label": "BVA / ABPE (Belgische asfaltsector)",
        "brief": (
            "Belgische Vereniging van Asfaltproducenten (NL) / Association "
            "Belge des Producteurs d'Enrobés (FR). Sectorfederatie van "
            "asfaltcentrales en wegenbouw-toeleveranciers. Strategische "
            "thema's: wegenbouw, asfaltindustrie, bitumen, asfalt-recyclage, "
            "publieke aanbestedingen wegen, gewestelijke wegenbudgetten "
            "(AWV / SPW Mobilité), CO2-emissies bouw, circulaire economie, "
            "PFAS/stikstof, energieprijzen voor industrie, verkeers- en "
            "mobiliteitsbeleid, fietsinfrastructuur."
        ),
        "patterns": [
            # Brand (volledig)
            r"Belgische\s+Vereniging\s+van\s+Asfaltproducenten",
            r"Association\s+Belge\s+des\s+Producteurs\s+d['’]Enrob[ée]s?",
            # Sector core
            r"\basfalt", r"\benrob[eé]", r"\basphalte", r"\bbitume",
            r"\basfaltcentrale", r"\bcentrale\s+d['']enrobage\b",
            r"\bwegenbouw\b", r"\btravaux\s+routiers\b",
            r"\bwegenwerken\b", r"\bwegwerkzaamheden\b",
            r"\bweginfrastructuur\b", r"\binfrastructure\s+routière\b",
            r"\bvoirie", r"\bchauss[eé]e",
            # Aangrenzende federaties / peers
            r"\bConfederatie\s+Bouw\b", r"\bConf[eé]d[eé]ration\s+(?:de\s+la\s+)?Construction\b",
            r"\bEmbuild\b", r"\bBouwunie\b", r"\bFebelcem\b", r"\bFedbeton\b",
            r"\bFWEV\b", r"\bAWV\b", r"\bSPW\s+Mobilit[eé]\b",
            # Beleid & regelgeving
            r"\bopenbare\s+aanbesteding", r"\bmarch[eé]s?\s+publics?\b",
            r"\bPFAS\b", r"\bstikstof\b\s+(?:dossier|crisis|akkoord)?",
            r"\bazote\b\s+(?:dossier|crise)?",
            r"\bcirculaire?\s+economie\b\s+(?:in\s+de\s+bouw|construction)?",
            r"\bCO2\b\s+(?:bouw|construction)",
            r"\benergie[- ]?intensieve\s+industrie\b", r"\bindustrie\s+énergivore\b",
            r"\benergieprijzen?\s+(?:voor\s+)?industrie",
            # Mobiliteit (kan reactiekansen bieden)
            r"\bfietsinfrastructuur\b", r"\binfrastructure\s+cyclable\b",
            r"\bfietspad", r"\bpiste\s+cyclable\b",
            r"\bverkeersveiligheid\b", r"\bs[eé]curit[eé]\s+routi[eè]re\b",
            r"\bmobiliteitsplan\b", r"\bplan\s+de\s+mobilit[eé]\b",
        ],
        "search_terms": {
            "brand": [
                "Belgische Vereniging Asfaltproducenten",
                "Association Belge Producteurs Enrobés",
                "ABPE asfalt", "BVA asfalt",
            ],
            "competitors": [
                "Embuild", "Confederatie Bouw", "Confédération Construction",
                "Febelcem", "Fedbeton", "Bouwunie",
            ],
            "policy": [
                "PFAS asfalt", "PFAS enrobé",
                "openbare aanbesteding wegen", "marché public voirie",
                "AWV budget", "SPW Mobilité budget",
                "CO2 wegenbouw", "CO2 construction routière",
                "circulaire economie bouw", "économie circulaire construction",
            ],
            "broad": [
                "wegenwerken België", "travaux routiers Belgique",
                "wegeninfrastructuur België",
                "verkeersveiligheid België", "sécurité routière Belgique",
                "fietsinfrastructuur België",
            ],
        },
    },
}
