"""Monitoring profiles: bundle everything that differs between tracks.

Two profiles share one pipeline:
  - akkanto: the original daily client issue-monitor (IKEA, Accent, Helios, BVA).
  - bikon:   a business/market/tech radar for Bikon (competitors, funding,
             AI regulation, gen-AI technique, pension & bancassurance market).

A Profile carries its companies dict, the outlet-feed catalogue, the Claude
system prompt, whether to ask Claude for an action line, the state file name,
the subject/title, the footer and the recipient env var. main.py selects a
profile via --profile and threads it through the (otherwise shared) modules,
so there are no `if profile == ...` branches anywhere else.
"""

from dataclasses import dataclass

from bikon_companies import BIKON_COMPANIES, BIKON_OUTLET_FEEDS
from companies import COMPANIES
from feeds import all_feeds


@dataclass(frozen=True)
class Profile:
    name: str
    companies: dict
    outlet_feeds: dict
    llm_system: str
    include_action: bool
    state_filename: str
    subject_prefix: str
    to_addr_env: str
    default_to: str
    render_footer: str
    max_per_bucket: int


# --- akkanto: the original client issue-monitor framing -----------------
AKKANTO_SYSTEM = (
    "Je bent een mediamonitoring-assistent voor een Belgische strategische "
    "communicatieadviseur. Per klant krijg je een briefing met de strategische "
    "thema's, en een lijst kandidaat-artikels uit Belgische pers en sectorpers. "
    "Voor elk artikel beoordeel je of de adviseur het zou willen zien: "
    "ja als het rechtstreeks over de klant gaat, over een directe concurrent, "
    "over regelgeving/beleid dat hen raakt, of over een sector- of "
    "maatschappelijk thema waar zij geloofwaardig op zouden kunnen reageren "
    "(via actie, interne of externe communicatie). Nee bij passing mentions, "
    "naam-collisions, of sectornieuws zonder concreet aanknopingspunt voor "
    "deze klant. Wees streng maar niet eng, twijfelgevallen liever wel dan niet.\n\n"
    "Voor elk relevant item geef je ook een prioriteits-score 1-5:\n"
    "  5 = rechtstreeks over de klant, mogelijk reactie vereist\n"
    "  4 = directe concurrent, of regelgeving die hen rechtstreeks raakt\n"
    "  3 = sectornieuws met duidelijk aanknopingspunt voor de klant\n"
    "  2 = adjacent thema, mogelijk relevant\n"
    "  1 = grensgeval, twijfelachtig\n"
    "Voor relevant=false: score=0.\n\n"
    "Antwoord uitsluitend met geldige JSON."
)

AKKANTO_FOOTER = (
    "Automatisch gegenereerd door _mediamonitor. "
    "Bronnen: Belgische pers (NL+FR) + sectorpers. "
    "Topic-filtering en samenvatting door Claude, strikt uit de artikeltekst."
)

# --- bikon: business/market/tech radar framing --------------------------
BIKON_SYSTEM = (
    "Je bent de media-, markt- en techniekradar voor Bikon, een UGent/VUB-spin-off "
    "die een vertrouwenslaag op AI bouwt voor gereguleerde sectoren. Bikon levert "
    "antwoorden die verankerd zijn in regelgeving, traceerbaar naar de bron en "
    "verdedigbaar onder toetsing. Eerste domein: Belgische pensioenen (96% "
    "accuraatheid, anchor is een grote Belgische bancassureur). Volgende verticals: "
    "HR/payroll, fiscaliteit, juridisch, douane. Andries Fluit (Head of Business) "
    "leest deze radar.\n\n"
    "Per spoor krijg je een briefing en een lijst kandidaat-artikels uit business-pers, "
    "internationale tech/AI-pers, funding-bronnen, EU-regelgeving en AI-engineering-blogs. "
    "Beoordeel of het artikel nuttig is voor Bikon's business of product. Relevant als "
    "het raakt aan: concurrenten of funding in RegTech/AI-advies, AI-regelgeving die Bikon "
    "raakt (EU AI Act, FSMA, NBB, DORA, GDPR), concrete gen-AI-techniek die Bikon's pipeline "
    "kan versterken (RAG, knowledge graphs, retrieval, agents, evaluatie), markt- en "
    "klantsignalen (pensioenhervorming, bancassureurs, verzekeraars), of voer voor thought "
    "leadership. Nee bij passing mentions, naamcollisions of generieke AI-hype zonder "
    "concreet nut voor Bikon.\n\n"
    "Voor elk relevant item geef je een prioriteits-score 1-5:\n"
    "  5 = directe concurrentbeweging (funding, launch, bankdeal), AI-regelgeving die Bikon's "
    "product rechtstreeks raakt, of een techniek die Bikon meteen kan overnemen\n"
    "  4 = significante RegTech/AI-advies funding, of een concrete RAG/knowledge-graph/agent/"
    "evaluatie-ontwikkeling\n"
    "  3 = markt- of klantsignaal (pensioen, bancassurance AI), of thought-leadership voer\n"
    "  2 = adjacent AI/enterprise-trend\n"
    "  1 = grensgeval, twijfelachtig\n"
    "Voor relevant=false: score=0.\n\n"
    "Geef daarnaast per relevant item een korte concrete actie voor Andries: wat zou hij "
    "ermee kunnen doen (bv. 'update battlecard', 'overweeg LinkedIn-post', 'deel met "
    "tech-team', 'check voor consultatie-submission', 'sales-signaal richting bank'). Laat "
    "leeg als er geen zinvolle actie is.\n\n"
    "Antwoord uitsluitend met geldige JSON."
)

BIKON_FOOTER = (
    "Automatisch gegenereerd door _mediamonitor (Bikon-radar). "
    "Bronnen: BE business/tech-pers, internationale tech/AI/funding, EU-regelgeving en "
    "AI-engineering-blogs. Filtering, scoring, actie en samenvatting door Claude, strikt "
    "uit de artikeltekst."
)


AKKANTO = Profile(
    name="akkanto",
    companies=COMPANIES,
    outlet_feeds=all_feeds(),
    llm_system=AKKANTO_SYSTEM,
    include_action=False,
    state_filename="last_sent.txt",
    subject_prefix="Mediamonitor",
    to_addr_env="MONITOR_TO_ADDR",
    default_to="andries.fluit@akkanto.com",
    render_footer=AKKANTO_FOOTER,
    max_per_bucket=40,
)

BIKON = Profile(
    name="bikon",
    companies=BIKON_COMPANIES,
    outlet_feeds=all_feeds(belgian=BIKON_OUTLET_FEEDS, sector={}),
    llm_system=BIKON_SYSTEM,
    include_action=True,
    state_filename="last_sent_bikon.txt",
    subject_prefix="Bikon Radar",
    to_addr_env="BIKON_MONITOR_TO_ADDR",
    default_to="andries@bikon.ai",
    render_footer=BIKON_FOOTER,
    max_per_bucket=15,
)

PROFILES = {"akkanto": AKKANTO, "bikon": BIKON}


def get_profile(name):
    try:
        return PROFILES[name]
    except KeyError:
        raise SystemExit(f"unknown profile: {name!r} (choose from {sorted(PROFILES)})")
