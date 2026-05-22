"""Produce a 2-3 sentence factual summary in Dutch from the article body.

Hard rule: only what is in the supplied text. No filling in, no extrapolating,
no 'context' from prior knowledge. If the body is too thin (paywall or fetch
failed), we use the RSS snippet verbatim and skip the LLM — never let the
model invent.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5"

# Cap body length we send to the model. 4000 chars ≈ first 5-8 paragraphs
# which is plenty for a 2-3 sentence summary, and keeps cost in check.
_BODY_CHAR_LIMIT = 4000


def _client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    from anthropic import Anthropic
    return Anthropic(api_key=api_key)


_SYSTEM = (
    "Je vat artikels samen voor een Nederlandstalige communicatieadviseur. "
    "Strikte regels:\n"
    "1. Gebruik UITSLUITEND informatie uit de meegeleverde tekst. Niets "
    "aanvullen uit eigen kennis.\n"
    "2. Geen interpretatie, geen commentaar, geen advies. Enkel beknopte "
    "feitelijke samenvatting.\n"
    "3. 2-3 zinnen, Nederlands, neutrale toon.\n"
    "4. Als de tekst onvoldoende inhoud bevat voor een zinvolle samenvatting, "
    "antwoord exact met: ONVOLDOENDE_INFO\n"
    "5. Verzin NOOIT cijfers, namen, citaten of feiten die niet expliciet "
    "in de tekst staan.\n"
    "Antwoord uitsluitend met geldige JSON: array van {idx, summary}."
)


def _user_prompt(items):
    lines = ["Vat elk artikel hieronder samen (2-3 zinnen NL, alleen uit de tekst):"]
    for i, art in enumerate(items):
        body = (art.get("body_text") or "")[:_BODY_CHAR_LIMIT]
        lines.append(f"\n[{i}] titel: {art['title']}")
        lines.append(f"     tekst:\n{body}")
    lines.append('\nFormat: [{"idx": 0, "summary": "..."}, ...]')
    return "\n".join(lines)


def _parse(text):
    s = text.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1]
        if s.lstrip().lower().startswith("json"):
            s = s.lstrip()[4:]
        s = s.rsplit("```", 1)[0]
    return json.loads(s)


def summarize_batch(articles):
    """Annotate each article in-place with `summary`.

    For articles where body_status != 'ok' we use the RSS summary verbatim
    (no LLM, no risk of fabrication). For 'ok' articles we send the body
    to Claude with the strict prompt above.
    """
    fallback = []
    enriched = []
    for art in articles:
        if art.get("body_status") == "ok" and (art.get("body_text") or "").strip():
            enriched.append(art)
        else:
            fallback.append(art)

    # Fallback: never call the LLM, use what we already have.
    for art in fallback:
        snippet = (art.get("summary") or "").strip()
        if art.get("body_status") == "paywall":
            art["summary_long"] = snippet or "(achter betaalmuur — geen samenvatting beschikbaar)"
            art["summary_source"] = "rss_snippet_paywall"
        else:
            art["summary_long"] = snippet or "(geen samenvatting beschikbaar)"
            art["summary_source"] = "rss_snippet_fail"

    if not enriched:
        return articles

    client = _client()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=_SYSTEM,
        messages=[{"role": "user", "content": _user_prompt(enriched)}],
    )
    raw = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    try:
        verdicts = _parse(raw)
    except Exception as e:
        logger.warning("summarize parse failed: %s\nRaw: %s", e, raw[:400])
        # Fail safe: use RSS snippets so we never accidentally show LLM garbage.
        for art in enriched:
            art["summary_long"] = (art.get("summary") or "").strip() or "(samenvatting niet beschikbaar)"
            art["summary_source"] = "rss_snippet_parsefail"
        return articles

    by_idx = {v["idx"]: v.get("summary", "") for v in verdicts if isinstance(v, dict) and "idx" in v}
    for i, art in enumerate(enriched):
        s = (by_idx.get(i) or "").strip()
        if not s or s == "ONVOLDOENDE_INFO":
            # Model itself flagged the text as too thin — fall back to RSS snippet.
            art["summary_long"] = (art.get("summary") or "").strip() or "(samenvatting niet beschikbaar)"
            art["summary_source"] = "rss_snippet_thin"
        else:
            art["summary_long"] = s
            art["summary_source"] = "llm_from_body"

    return articles
