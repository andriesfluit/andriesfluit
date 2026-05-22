"""Second-pass relevance filter via Claude.

Regex matching is intentionally loose, so this layer drops false positives
that regex can't tell apart (e.g. 'Accent' as a normal word, 'BVA' the
market-research firm, IKEA stories from other countries that happen to
mention 'Brussel' in the body).

We do NOT generate strategic advice here — only a relevance verdict and a
one-line nut graf. The user is a senior advisor; the email is a clean
reading list, not a briefing memo.
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


def _prompt(company_key, articles):
    cfg = COMPANIES[company_key]
    lines = [
        f"Bedrijf om te monitoren: {cfg['label']}",
        "",
        "Hieronder een lijst kandidaat-artikels uit Belgische pers (NL + FR) en sectorpers.",
        "Voor ELK artikel: bepaal of het écht over dit bedrijf gaat. Drop alles wat een",
        "naam-collisie is (bv. 'accent' als woord, 'BVA' marktonderzoek, IKEA buitenland)",
        "of waar het bedrijf slechts in passing genoemd wordt zonder betekenis.",
        "",
        "Antwoord uitsluitend met geldige JSON: een array van objecten met velden:",
        "  - idx (int, 0-based)",
        "  - relevant (bool)",
        "  - nut (string, max 15 woorden, NL, of '' als irrelevant)",
        "",
        "Artikels:",
    ]
    for i, art in enumerate(articles):
        snippet = (art.get("summary") or "").strip()
        if len(snippet) > 280:
            snippet = snippet[:280] + "…"
        lines.append(f"[{i}] bron={art['source']} | titel: {art['title']}")
        if snippet:
            lines.append(f"     samenvatting: {snippet}")
    return "\n".join(lines)


def _parse(text):
    # Claude sometimes wraps in ```json fences. Strip.
    s = text.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1]
        if s.lstrip().lower().startswith("json"):
            s = s.lstrip()[4:]
        s = s.rsplit("```", 1)[0]
    return json.loads(s)


def filter_company(company_key, articles):
    """Return the subset of articles Claude marks relevant, each augmented
    with a 'nut' field (one-line explainer)."""
    if not articles:
        return []
    client = _client()
    prompt = _prompt(company_key, articles)
    resp = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    try:
        verdicts = _parse(raw)
    except Exception as e:
        logger.warning("LLM filter parse failed for %s: %s\nRaw: %s", company_key, e, raw[:400])
        # Fail open: keep everything, no nut graf.
        return [{**a, "nut": ""} for a in articles]

    kept = []
    by_idx = {v["idx"]: v for v in verdicts if isinstance(v, dict) and "idx" in v}
    for i, art in enumerate(articles):
        v = by_idx.get(i)
        if v and v.get("relevant"):
            kept.append({**art, "nut": v.get("nut", "")})
    return kept
