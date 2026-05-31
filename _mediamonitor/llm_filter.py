"""Strategic-relevance filter via Claude.

The regex matcher casts a wide net across sector terms, competitors and
adjacent themes. This second pass asks Claude — given each company's
strategic brief — whether an item is worth flagging to the consultant,
and if so under which topic.

We deliberately do NOT generate reaction advice ('we suggest a press
release'). The consultant does that. We only label relevance, topic and
a one-line nut graf.
"""

import json
import logging
import os

from companies import COMPANIES

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5"


def _client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    from anthropic import Anthropic
    return Anthropic(api_key=api_key)


_SYSTEM = (
    "Je bent een mediamonitoring-assistent voor een Belgische strategische "
    "communicatieadviseur. Per klant krijg je een briefing met de strategische "
    "thema's, en een lijst kandidaat-artikels uit Belgische pers en sectorpers. "
    "Voor elk artikel beoordeel je of de adviseur het zou willen zien: "
    "ja als het rechtstreeks over de klant gaat, over een directe concurrent, "
    "over regelgeving/beleid dat hen raakt, of over een sector- of "
    "maatschappelijk thema waar zij geloofwaardig op zouden kunnen reageren "
    "(via actie, interne of externe communicatie). Nee bij passing mentions, "
    "naam-collisions, of sectornieuws zonder concreet aanknopingspunt voor "
    "deze klant. Wees streng maar niet eng — twijfelgevallen liever wel dan niet.\n\n"
    "Voor elk relevant item geef je ook een prioriteits-score 1-5:\n"
    "  5 = rechtstreeks over de klant, mogelijk reactie vereist\n"
    "  4 = directe concurrent, of regelgeving die hen rechtstreeks raakt\n"
    "  3 = sectornieuws met duidelijk aanknopingspunt voor de klant\n"
    "  2 = adjacent thema, mogelijk relevant\n"
    "  1 = grensgeval, twijfelachtig\n"
    "Voor relevant=false: score=0.\n\n"
    "Antwoord uitsluitend met geldige JSON."
)


def _user_prompt(company_key, articles):
    cfg = COMPANIES[company_key]
    lines = [
        f"KLANT: {cfg['label']}",
        "",
        "BRIEFING:",
        cfg["brief"],
        "",
        "KANDIDAAT-ARTIKELS:",
    ]
    for i, art in enumerate(articles):
        snippet = (art.get("summary") or "").strip()
        if len(snippet) > 300:
            snippet = snippet[:300] + "…"
        lines.append(f"[{i}] bron={art['source']}")
        lines.append(f"     titel: {art['title']}")
        if snippet:
            lines.append(f"     samenvatting: {snippet}")
    lines += [
        "",
        "Geef een JSON-array met één object per artikel:",
        '  {"idx": int, "relevant": bool, "score": int 0-5, "topic": "korte topictag NL (max 4 woorden)", "nut": "1 zin NL waarom dit deze klant raakt"}',
        "Voor relevant=false mag topic en nut leeg (\"\") en score=0.",
    ]
    return "\n".join(lines)


def _parse(text):
    s = text.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1]
        if s.lstrip().lower().startswith("json"):
            s = s.lstrip()[4:]
        s = s.rsplit("```", 1)[0]
    return json.loads(s)


# Cap input per company to keep prompt size + latency bounded on noisy days.
# Most days will be well under this; the cap only kicks in if pattern flood.
MAX_PER_COMPANY = 80


def filter_company(company_key, articles):
    """Return Claude-filtered relevant articles, each augmented with
    'topic' and 'nut' fields."""
    if not articles:
        return []
    if len(articles) > MAX_PER_COMPANY:
        logger.warning(
            "%s: %d candidates exceeds MAX_PER_COMPANY=%d, truncating",
            company_key, len(articles), MAX_PER_COMPANY,
        )
        articles = articles[:MAX_PER_COMPANY]

    client = _client()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=_SYSTEM,
        messages=[{"role": "user", "content": _user_prompt(company_key, articles)}],
    )
    raw = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    try:
        verdicts = _parse(raw)
    except Exception as e:
        logger.warning("LLM parse failed for %s: %s\nRaw: %s", company_key, e, raw[:400])
        # Fail open with a clear marker so we notice in the mail.
        return [{**a, "topic": "(filter failed)", "nut": "", "score": 3} for a in articles]

    by_idx = {v["idx"]: v for v in verdicts if isinstance(v, dict) and "idx" in v}
    kept = []
    for i, art in enumerate(articles):
        v = by_idx.get(i)
        if v and v.get("relevant"):
            try:
                score = int(v.get("score", 3))
            except (TypeError, ValueError):
                score = 3
            score = max(1, min(5, score))
            kept.append({
                **art,
                "topic": v.get("topic", ""),
                "nut":   v.get("nut", ""),
                "score": score,
            })
    return kept
