"""The editorial brain: Claude reads the whole edition + Andries' preferences +
learned feedback, and returns two buckets.

  KERN — op maat: the articles that best match his stated interests and the
         feedback signal, ranked, each with a one-line why + a strict summary.

  VERRASSING — buiten je bubbel: a deliberately diverse set of strong articles
         OUTSIDE his stated interests, to keep the digest from collapsing into
         a filter bubble. This bucket is protected: feedback may raise its
         quality bar but may never shrink it or pull it toward his tastes.

Hard no-fabrication rule (same as the mediamonitor summarizer): every summary
must come strictly from the supplied article text. No outside knowledge, no
invented figures, names or quotes.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

# Sonnet 4.6: strong editorial judgement for the nuanced selection + anti-echo
# reasoning, cheap enough to run once a day on a full edition. Swap freely.
MODEL = "claude-sonnet-4-6"

# How many items each bucket aims for. VERRASSING_MIN is the protected floor:
# the model must not go below it, whatever the feedback says.
KERN_COUNT = 8
VERRASSING_COUNT = 4
VERRASSING_MIN = 3

# Body chars sent per article. The lede carries the facts a 2-3 sentence
# summary needs; capping keeps a ~60-article prompt affordable.
_BODY_CHAR_LIMIT = 1800


def _client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    from anthropic import Anthropic
    return Anthropic(api_key=api_key)


_SYSTEM = """Je bent de persoonlijke krantenredacteur van Andries. Elke ochtend \
krijg je de volledige edities van meerdere kranten (De Standaard én De Tijd) en \
stel je voor hem ÉÉN gecombineerde digest samen uit twee delen.

1. KERN (op maat). De artikels die het best aansluiten bij zijn voorkeuren en \
bij wat hij eerder waardeerde. Gerangschikt van meest naar minst relevant.

2. VERRASSING (buiten zijn bubbel). Bewust artikels BUITEN zijn opgegeven \
voorkeuren — sterk, belangrijk of verrassend genoeg dat ze hem een nieuw \
perspectief geven. Maximaal divers gespreid over rubrieken. Dit is geen \
restpost: kies hier met zorg om hem uit zijn echokamer te houden.

MEERDERE KRANTEN — SAMENVOEGEN (belangrijk)
- Bij elk artikel staat de bron (krant). De twee kranten dekken vaak DEZELFDE \
verhalen. Maak hier NOOIT twee aparte items van.
- Behandelen beide kranten hetzelfde onderwerp, voeg ze samen tot ÉÉN item: zet \
beide artikelnummers in 'idxs'. Schrijf dan één alinea die de berichtgeving \
combineert, en differentieer in de tekst waar het iets toevoegt — bv. "De Tijd \
benadrukt …, terwijl De Standaard meldt dat …". De twee bronnen verschijnen \
automatisch bovenaan het item.
- Dekt maar één krant het verhaal, dan bevat 'idxs' één nummer.
- Blijf strikt bij de feiten uit BEIDE meegeleverde teksten; verzin geen brug \
tussen de twee.

STRIKTE REGELS
- Samenvattingen UITSLUITEND uit de meegeleverde artikeltekst. Niets aanvullen \
uit eigen kennis. Verzin NOOIT cijfers, namen, citaten of feiten. Een korte \
alinea (3-5 zinnen) met duiding — wat is er gebeurd én waarom het ertoe doet — \
Nederlands, neutrale toon.
- 'waarom' is één korte zin: bij KERN waarom het bij hem past, bij VERRASSING \
waarom het hem zou kunnen verrassen of verrijken.
- Geen artikel mag in beide buckets staan.

ANTI-ECHOKAMER (belangrijk)
- De geleerde voorkeuren sturen ALLEEN de KERN en de kwaliteitslat. Ze mogen de \
VERRASSING-sectie nooit laten krimpen of naar zijn smaak toetrekken.
- Negatieve feedback op een verrassend thema betekent: kies een ÁNDER \
verrassend thema — niet minder verrassing.
- Lever altijd minstens het gevraagde minimum aan verrassingen, ook op een \
dag waarop alles binnen zijn voorkeuren lijkt te vallen.

Antwoord UITSLUITEND met geldige JSON, exact in dit schema:
{
  "rode_draad": "optioneel: 1 zin over de dominante lijn van de dag, of \\"\\"",
  "kern": [{"idxs": [int, ...], "score": int 1-5, "waarom": "1 zin", "samenvatting": "korte alinea met duiding"}],
  "verrassing": [{"idxs": [int, ...], "waarom": "1 zin", "samenvatting": "korte alinea met duiding"}]
}

'idxs' bevat meestal één artikelnummer; twee (of meer) bij overlap tussen de \
kranten over hetzelfde onderwerp."""


def _user_prompt(articles, preferences, feedback_context, kern_n, verr_n, verr_min):
    lines = ["VOORKEUREN VAN ANDRIES:", preferences.strip(), ""]
    if feedback_context:
        lines += [feedback_context.strip(), ""]
    lines += [
        f"OPDRACHT: kies {kern_n} artikels voor KERN en {verr_n} voor VERRASSING "
        f"(minimaal {verr_min} verrassingen, ook als alles binnen zijn voorkeuren lijkt te vallen).",
        "",
        "ARTIKELS UIT DE EDITIE:",
    ]
    for i, a in enumerate(articles):
        body = (a.get("body") or "")[:_BODY_CHAR_LIMIT]
        bron = f"bron={a['bron']} · " if a.get("bron") else ""
        lines.append(f"\n[{i}] {bron}rubriek={a['rubriek']} · p{a.get('page')}"
                     + (f" · {a['author']}" if a.get("author") else ""))
        lines.append(f"     titel: {a['title']}")
        if a.get("intro"):
            lines.append(f"     intro: {a['intro']}")
        lines.append(f"     tekst: {body}")
    return "\n".join(lines)


def _parse(text):
    s = text.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1]
        if s.lstrip().lower().startswith("json"):
            s = s.lstrip()[4:]
        s = s.rsplit("```", 1)[0]
    return json.loads(s)


def build_digest(articles, preferences, feedback_context="",
                 kern_n=KERN_COUNT, verr_n=VERRASSING_COUNT, verr_min=VERRASSING_MIN):
    """Return {rode_draad, kern, verrassing} where each kern/verrassing entry is
    a full article dict augmented with score/waarom/samenvatting. idx values
    from the model are resolved back to articles here."""
    if not articles:
        return {"rode_draad": "", "kern": [], "verrassing": []}

    client = _client()
    resp = client.messages.create(
        model=MODEL,
        # Combined digest = up to ~15 items with paragraph summaries (sometimes
        # merging two papers), so the JSON response can run long. 4096 truncated
        # it mid-string; give ample headroom.
        max_tokens=8192,
        system=_SYSTEM,
        messages=[{"role": "user",
                   "content": _user_prompt(articles, preferences, feedback_context,
                                           kern_n, verr_n, verr_min)}],
    )
    raw = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    try:
        verdict = _parse(raw)
    except Exception as e:
        logger.error("digest parse failed: %s\nRaw: %s", e, raw[:600])
        raise

    seen = set()

    def resolve(entries, extra_keys):
        """Each entry's 'idxs' may list one OR several articles about the same
        story (an overlap between the two papers). We merge them into one item:
        the primary article supplies title/page/rubriek, the sources/labels are
        the union, and the model's samenvatting already weaves both papers."""
        out = []
        for v in entries or []:
            idxs = v.get("idxs")
            if not idxs and isinstance(v.get("idx"), int):
                idxs = [v["idx"]]
            idxs = [i for i in (idxs or [])
                    if isinstance(i, int) and 0 <= i < len(articles) and i not in seen]
            if not idxs:
                continue
            for i in idxs:
                seen.add(i)
            art = dict(articles[idxs[0]])
            srcs, brons = [], []
            for i in idxs:
                s, b = articles[i].get("source"), articles[i].get("bron")
                if s and s not in srcs:
                    srcs.append(s)
                if b and b not in brons:
                    brons.append(b)
            art["sources"] = srcs
            if brons:
                art["bron"] = " + ".join(brons)
            art["waarom"] = (v.get("waarom") or "").strip()
            art["samenvatting"] = (v.get("samenvatting") or "").strip()
            for k in extra_keys:
                art[k] = v.get(k)
            out.append(art)
        return out

    kern = resolve(verdict.get("kern"), ["score"])
    verrassing = resolve(verdict.get("verrassing"), [])

    # Normalise scores to 1-5.
    for a in kern:
        try:
            a["score"] = max(1, min(5, int(a.get("score") or 3)))
        except (TypeError, ValueError):
            a["score"] = 3
    kern.sort(key=lambda a: -a["score"])

    if len(verrassing) < verr_min:
        logger.warning("only %d verrassingen returned (floor=%d); model under-delivered",
                       len(verrassing), verr_min)

    return {
        "rode_draad": (verdict.get("rode_draad") or "").strip(),
        "kern": kern,
        "verrassing": verrassing,
    }
