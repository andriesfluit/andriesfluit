"""Gedeelde instellingen en hulpfuncties voor collect.py, classify.py en report.py."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
OUTPUT_DIR = ROOT / "output"
JOBS_FILE = DATA_DIR / "vacatures.jsonl"

# Harde grenzen uit de opdracht.
MAX_RESULTS = 50
MAX_DAYS = 30

SEARCH_TERMS = {
    "bouwen": [
        "RAG",
        "retrieval augmented generation",
        "LLM engineer",
        "AI engineer",
        "GenAI engineer",
        "vector database",
        "LangChain",
        "Azure OpenAI",
        "Copilot Studio",
    ],
    "beheren": [
        "knowledge manager",
        "kennisbeheer",
        "kennisbank",
        "base de connaissances",
        "conversational designer",
        "chatbot content",
    ],
    "kopen_uitrollen": [
        "GenAI product owner",
        "AI product owner",
        "chatbot",
        "AI-assistent",
        "assistant virtuel",
        "virtual assistant",
        "IA générative",
        "generatieve AI",
    ],
    "governance": [
        "AI Act",
        "AI governance",
        "AI compliance",
        "responsible AI",
    ],
}
ALL_TERMS = [term for terms in SEARCH_TERMS.values() for term in terms]
TERM_CATEGORY = {term: cat for cat, terms in SEARCH_TERMS.items() for term in terms}


def fold(text: str | None) -> str:
    """Kleine letters, zonder accenten, leestekens als spatie, enkele spaties."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = re.sub(r"[^\w]+", " ", text)
    return " ".join(text.split())


def slug(text: str) -> str:
    return fold(text).replace(" ", "-") or "leeg"


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


# --- Persoonsgegevens verwijderen -------------------------------------------------
# Best effort met patronen: e-mail, telefoon en LinkedIn-profielen overal, namen enkel
# in zinnen die over contact gaan. Liever te veel weg dan te weinig.

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
OBFUSCATED_EMAIL_RE = re.compile(
    r"[\w.+-]+\s*[\[(]\s*(?:at|@|apenstaart|arobase)\s*[\])]\s*[\w-]+"
    r"(?:\s*(?:[\[(]\s*(?:dot|punt|point)\s*[\])]|\.)\s*[\w-]+)+",
    re.I,
)
PROFILE_RE = re.compile(r"(?:https?://)?(?:[\w-]+\.)?linkedin\.com/in/[^\s)\]>]+", re.I)
PHONE_RE = re.compile(
    r"(?<![\w/])(?:(?:\+|00)\s?\d{2,3}[\s./-]?(?:\(0\)\s?)?\d{1,4}(?:[\s./-]?\d{2,4}){2,4}"
    r"|0\d{1,3}(?:[\s./-]?\d{2,3}){3,4})(?![\w/])"
)
CONTACT_CUE_RE = re.compile(
    r"\b(?:contact\w*|aanspreekpunt|interlocut\w*|recruiter|recruteu(?:r|se)|"
    r"talent acquisition|hr business partner|vragen\s*\?|questions?\s*\?|des questions|"
    r"meer info\w*|more info\w*|plus d.info\w*|bel|tel|t[ée]l|gsm|phone|telefoon|"
    r"t[ée]l[ée]phone|e-?mail|reach out|neem contact)\b",
    re.I,
)
_UPPER = "A-ZÀ-ÖØ-Þ"
_LOWER = "a-zß-öø-ÿ"
_WORD = rf"[{_UPPER}][{_LOWER}'’-]+"
_PARTICLE = r"(?:van|de|der|den|le|la|du|des|von|di|da|ter|ten|vanden|vander|d['’])"
_NOT_FIRST = r"(?!(?:Contact\w*|Neem|Bel|Mail|Stuur|Vragen|Questions?|Interested|Interesse)\b)"
NAME_RE = re.compile(rf"\b{_NOT_FIRST}{_WORD}(?:\s+(?:{_PARTICLE}\s+)*{_WORD})+")
NAME_AFTER_VERB_RE = re.compile(
    rf"(\b(?:met|with|avec|aan|to|contacteer|contactez|contacter|contact|bel|appelez|mail)\s+){_WORD}"
)
TITLE_NAME_RE = re.compile(
    rf"\b(?:Mr|Mrs|Ms|Mevr|Mevrouw|Dhr|Meneer|Mme|Madame|Monsieur)\.?\s+{_WORD}(?:\s+{_WORD})*"
)
NOT_NAMES = {"HR", "Us", "Ons", "Nous", "Talent", "Recruitment", "Rekrutering"}
SEGMENT_SPLIT_RE = re.compile(r"(\n+|(?<=[.!?])\s+)")


def _redact_phone(match: re.Match, counts: dict) -> str:
    digits = re.sub(r"\D", "", match.group())
    international = match.group().startswith(("+", "00"))
    if (international and 10 <= len(digits) <= 14) or (not international and len(digits) in (9, 10)):
        counts["telefoon"] += 1
        return "[telefoon verwijderd]"
    return match.group()


def _redact_names(segment: str, counts: dict) -> str:
    def sub(pattern: re.Pattern, text: str, keep_group: bool = False) -> str:
        def repl(m: re.Match) -> str:
            name = m.group()[len(m.group(1)) :] if keep_group else m.group()
            if name in NOT_NAMES:
                return m.group()
            counts["naam"] += 1
            return (m.group(1) if keep_group else "") + "[naam verwijderd]"

        return pattern.sub(repl, text)

    segment = sub(TITLE_NAME_RE, segment)
    segment = sub(NAME_RE, segment)
    return sub(NAME_AFTER_VERB_RE, segment, keep_group=True)


def scrub_pii(text: str | None) -> tuple[str | None, dict]:
    """Tekst zonder e-mailadressen, telefoonnummers, profiel-URL's en contactnamen."""
    counts = {"email": 0, "telefoon": 0, "naam": 0, "profiel": 0}
    if not text:
        return text, counts

    def count(kind: str, label: str):
        def repl(_: re.Match) -> str:
            counts[kind] += 1
            return label

        return repl

    text = PROFILE_RE.sub(count("profiel", "[profiel verwijderd]"), text)
    text = EMAIL_RE.sub(count("email", "[e-mail verwijderd]"), text)
    text = OBFUSCATED_EMAIL_RE.sub(count("email", "[e-mail verwijderd]"), text)
    text = PHONE_RE.sub(lambda m: _redact_phone(m, counts), text)
    parts = SEGMENT_SPLIT_RE.split(text)
    text = "".join(
        _redact_names(part, counts) if CONTACT_CUE_RE.search(part) else part for part in parts
    )
    return text, counts


# --- Normaliseren en dedupliceren --------------------------------------------------

LEGAL_FORMS = {
    "nv", "sa", "bv", "bvba", "srl", "sprl", "cvba", "scrl", "sc", "cv", "vzw", "asbl",
    "ag", "gmbh", "ltd", "limited", "inc", "llc", "plc", "sas", "sarl", "se", "co",
    "group", "groep", "groupe", "belgium", "belgique", "belgie", "benelux", "the",
}
GENDER_MARKER_RE = re.compile(r"\(?\b[mfvhxd](?:\s*[/|,]\s*[mfvhxd]){1,3}\b\)?", re.I)
CITY_ALIASES = {
    "brussel": "brussels", "bruxelles": "brussels", "brussels": "brussels",
    "antwerpen": "antwerp", "anvers": "antwerp", "antwerp": "antwerp",
    "gent": "ghent", "gand": "ghent", "ghent": "ghent",
    "leuven": "leuven", "louvain": "leuven",
    "luik": "liege", "liege": "liege",
    "bergen": "mons", "mons": "mons",
    "namen": "namur", "namur": "namur",
    "mechelen": "mechelen", "malines": "mechelen",
    "brugge": "bruges", "bruges": "bruges",
    "kortrijk": "kortrijk", "courtrai": "kortrijk",
    "doornik": "tournai", "tournai": "tournai",
    "hasselt": "hasselt",
}
PLACE_NOISE = {"region", "metropolitan", "area", "greater", "hoofdstedelijk", "gewest", "capitale", "de"}
COUNTRY_NAMES = {"belgium", "belgique", "belgie", "be", "belgien"}


CONNECTOR_WORDS = {"and", "en", "et", "und"}  # "Johnson & Johnson" = "Johnson and Johnson"


def normalize_company(name: str | None) -> str:
    # Punten weg, zodat "N.V." als "NV" herkend wordt en niet als losse letters.
    words = [w for w in fold((name or "").replace(".", "")).split() if w not in LEGAL_FORMS and w not in CONNECTOR_WORDS]
    return " ".join(words)


def normalize_title(title: str | None) -> str:
    """Zonder m/v/x en zonder landnaam achteraan ("... - BE")."""
    words = fold(GENDER_MARKER_RE.sub(" ", title or "")).split()
    while words and words[-1] in COUNTRY_NAMES:
        words.pop()
    return " ".join(words)


def normalize_place(place: str | None) -> str:
    first = fold((place or "").split(",")[0])
    words = [w for w in first.split() if w not in PLACE_NOISE]
    first = " ".join(words)
    if first in COUNTRY_NAMES:
        return ""
    return CITY_ALIASES.get(first, first)


def dedup_key(company: str | None, title: str | None, place: str | None, fallback: str) -> str:
    """Bedrijf + titel + plaats; zonder bedrijfsnaam valt de sleutel terug op de URL."""
    company_norm = normalize_company(company)
    if not company_norm:
        return f"url|{fallback}"
    return f"{company_norm}|{normalize_title(title)}|{normalize_place(place)}"


def job_id(key: str) -> str:
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def term_in_text(term: str, text: str | None) -> bool:
    """Komt de zoekterm voor, ook als meervoud of begin van een samenstelling (chatbots,
    chatbotteam)? Korte woorden (RAG, Act, AI) moeten wel als los woord staan."""
    words = fold(term).split()
    end = r"s?\b" if len(words[-1]) < 4 else ""
    return re.search(rf"\b{re.escape(' '.join(words))}{end}", fold(text)) is not None


# --- Recruitmentbureaus en interimkantoren -----------------------------------------

RECRUITER_NAMES = [
    "randstad", "adecco", "tempo team", "start people", "manpower", "experis", "hays",
    "michael page", "page personnel", "page executive", "robert half", "robert walters",
    "walters people", "accent jobs", "nowjobs", "synergie", "unique", "daoust", "trace",
    "agilitas", "konvert", "t interim", "asap", "vivaldis", "proselect", "hudson",
    "harvey nash", "computer futures", "nigel frank", "frank recruitment", "jefferson wells",
    "brightplus", "house of hr", "olympia", "covebo", "sd worx staffing", "sd worx jobs",
    "creyf s", "solvus", "kelly services", "darwin recruitment", "huxley", "sthree",
    "progressive recruitment", "selecthr", "select hr", "jobs4sales",
    # Uit de eerste run: tussenpersonen die de eigenlijke werkgever niet noemen.
    "koda tech", "koda staff", "collective work", "talentsquare", "deeprec",
]
RECRUITER_NAME_RE = re.compile(
    r"recruit|recrut|interim|uitzend|staffing|headhunt|executive search|selection|"
    r"rekrutering|werving|\bjobs\b|talent solutions|personnel|interimaire|interimkantoor",
    re.I,
)
RECRUITER_TEXT_RE = re.compile(
    r"(?:on behalf of (?:our|a) client|namens onze klant|voor rekening van onze klant|"
    r"pour le compte de (?:notre|l.un de nos) client|"
    r"(?:voor|for) (?:een|één|one) van onze klanten|for one of our clients|"
    r"pour (?:l.)?un de nos clients|our client is (?:looking|seeking|searching)|"
    r"onze klant is op zoek|notre client (?:recherche|est a la recherche)|"
    r"we are recruiting for our client|wij zoeken voor onze klant|nous recherchons pour notre client)",
    re.I,
)


def recruiter_flag(company: str | None, description: str | None) -> tuple[bool, str]:
    """Is dit (waarschijnlijk) een recruitmentbureau of interimkantoor? Met reden."""
    company_norm = fold(company)
    padded = f" {company_norm} "
    for name in RECRUITER_NAMES:
        if f" {name} " in padded:
            return True, f"bekend bureau ({name})"
    if RECRUITER_NAME_RE.search(company_norm):
        return True, "naam lijkt op bureau"
    match = RECRUITER_TEXT_RE.search(fold(description))
    if match:
        return True, f"tekst: '{match.group()}'"
    return False, ""
