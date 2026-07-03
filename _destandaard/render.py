"""Render the digest to Markdown (the file Andries keeps / drops in a project),
to HTML (the email body), and to JSON (consumed by the MyNews web reader).
All show the feedback handles so he can react."""

import html as _html
from datetime import datetime, timezone


def render_json(meta, digest):
    """Compact JSON the MyNews page fetches and renders client-side."""
    def item(a, with_score):
        d = {
            "handle": a.get("handle", ""),
            "title": a.get("title", ""),
            "bron": a.get("bron", ""),
            "source": a.get("source", ""),
            "sources": a.get("sources") or ([a["source"]] if a.get("source") else []),
            "rubriek": a.get("rubriek", ""),
            "page": a.get("page"),
            "author": a.get("author", ""),
            "samenvatting": a.get("samenvatting", ""),
        }
        # score stays out of the payload the reader renders; kern arrives
        # pre-sorted by relevance, so array order already carries the ranking.
        return d

    return {
        "source": meta.get("source", ""),
        "label": meta.get("label", ""),
        "date": meta.get("date", ""),
        "edition": meta.get("edition", ""),
        "article_count": meta.get("article_count", 0),
        "rode_draad": digest.get("rode_draad", ""),
        "kern": [item(a, True) for a in digest["kern"]],
        "verrassing": [item(a, False) for a in digest["verrassing"]],
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _count(n):
    return f"{n} artikel" if n == 1 else f"{n} artikels"


def _meta_line(a):
    """Secondary info on one compact line, rubriek first as the scan anchor,
    the feedback handle last and dimmed. Order: rubriek · krant · pagina ·
    auteur · handle. Any missing piece is simply skipped."""
    bits = []
    if a.get("rubriek"):
        bits.append(f"**{a['rubriek'].upper()}**")
    if a.get("bron"):
        bits.append(a["bron"])
    if a.get("page") is not None:
        bits.append(f"p{a['page']}")
    if a.get("author"):
        bits.append(a["author"])
    line = " · ".join(bits)
    if a.get("handle"):
        # keep the feedback code present but visually last / lowest
        line = f"{line} · `{a['handle']}`" if line else f"`{a['handle']}`"
    return line


def _articles_block(out, items):
    """Numbered items: title as the lead (H3), one meta line, then the
    duiding paragraph. Numbering + a blank-line rhythm give the vertical
    hierarchy that makes the text version scannable."""
    for i, a in enumerate(items, 1):
        out.append(f"### {i}. {a['title']}")
        meta_line = _meta_line(a)
        if meta_line:
            out.append(meta_line)
        out.append("")
        out.append(a.get("samenvatting", ""))
        out.append("")


def render_markdown(meta, digest):
    date = meta.get("date", "")
    sources_line = meta.get("sources_line") or meta.get("label") or "editie " + str(meta.get("edition", ""))
    out = [f"# Jouw nieuwsdigest", ""]
    out.append(f"**{date}** · {sources_line} · {meta.get('article_count', 0)} artikels gescand")
    out.append("")
    if digest.get("rode_draad"):
        out.append(f"> **Rode draad.** {digest['rode_draad']}")
        out.append("")

    out.append(f"## Op maat · {_count(len(digest['kern']))}")
    out.append("")
    _articles_block(out, digest["kern"])

    out.append(f"## Verrassing · {_count(len(digest['verrassing']))}")
    out.append("")
    out.append("_Buiten je opgegeven voorkeuren gekozen, om je geen echokamer "
               "in te sturen._")
    out.append("")
    _articles_block(out, digest["verrassing"])

    out.append("---")
    out.append("")
    out.append("### Feedback")
    out.append("")
    out.append("Voeg in `_destandaard/data/feedback.md` regels toe met het "
               "handle vooraan, dan `+` of `-`, en optioneel een notitie:")
    out.append("")
    out.append("```")
    if digest["kern"]:
        out.append(f"{digest['kern'][0]['handle']} + meer van dit soort duiding")
    if digest["verrassing"]:
        out.append(f"{digest['verrassing'][0]['handle']} -")
    out.append("```")
    out.append("")
    out.append("De volgende digest leest die feedback en scherpt de **Op maat**-"
               "selectie aan. De **Verrassing**-sectie blijft bewust gevarieerd.")
    return "\n".join(out) + "\n"


def _h(s):
    return _html.escape(s or "")


def render_html(meta, digest):
    date = meta.get("date", "")
    edition = meta.get("edition", "")

    def article_block(a, i):
        # Meta line, same hierarchy as the text version: rubriek first as the
        # scan anchor (uppercase, accent), then krant · pagina · auteur, and
        # the feedback handle last and dimmed.
        bits = []
        if a.get("rubriek"):
            bits.append(f"<span style='color:#c8860a;font-weight:600;"
                        f"text-transform:uppercase;letter-spacing:.03em'>{_h(a['rubriek'])}</span>")
        if a.get("bron"):
            bits.append(_h(a["bron"]))
        if a.get("page") is not None:
            bits.append(f"p{_h(str(a['page']))}")
        if a.get("author"):
            bits.append(_h(a["author"]))
        if a.get("handle"):
            bits.append(f"<span style='font-family:monospace;color:#bbb'>{_h(a['handle'])}</span>")
        meta_line = " · ".join(bits)
        return f"""
        <div style="margin:0 0 20px 0">
          <h3 style="margin:0 0 3px 0;font-size:17px;line-height:1.3">{i}. {_h(a['title'])}</h3>
          <div style="font-size:12px;color:#888">{meta_line}</div>
          <p style="margin:6px 0;line-height:1.5">{_h(a.get('samenvatting',''))}</p>
        </div>"""

    rode = (f"<p style='background:#f5f1e8;padding:12px 14px;border-left:3px solid #c8860a;"
            f"margin:0 0 22px 0'><strong>Rode draad.</strong> {_h(digest['rode_draad'])}</p>"
            if digest.get("rode_draad") else "")

    kern_html = "".join(article_block(a, i) for i, a in enumerate(digest["kern"], 1))
    verr_html = "".join(article_block(a, i) for i, a in enumerate(digest["verrassing"], 1))
    h2 = ("font-size:15px;text-transform:uppercase;letter-spacing:.05em;color:#444;"
          "border-bottom:1px solid #eee;padding-bottom:6px")

    return f"""<!doctype html><html><body style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#1a1a1a;max-width:640px;margin:0 auto;padding:16px">
      <h1 style="font-size:22px;margin:0 0 4px 0">Jouw nieuwsdigest</h1>
      <div style="font-size:13px;color:#888;margin-bottom:20px">{_h(date)} · {_h(meta.get('sources_line') or meta.get('label') or '')} · {meta.get('article_count',0)} artikels gescand</div>
      {rode}
      <h2 style="{h2}">Op maat <span style="color:#999;font-weight:400;text-transform:none;letter-spacing:0">· {_count(len(digest['kern']))}</span></h2>
      {kern_html}
      <h2 style="{h2}">Verrassing <span style="color:#999;font-weight:400;text-transform:none;letter-spacing:0">· {_count(len(digest['verrassing']))}</span></h2>
      <p style="font-size:13px;color:#777;font-style:italic;margin-top:4px">Buiten je opgegeven voorkeuren gekozen, om je geen echokamer in te sturen.</p>
      {verr_html}
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0">
      <p style="font-size:13px;color:#777">Feedback? Zet in <code>_destandaard/data/feedback.md</code> een regel als
      <code>{_h(digest['kern'][0]['handle']) if digest['kern'] else '0626-a1'} + meer van dit</code> of
      <code>{_h(digest['verrassing'][0]['handle']) if digest['verrassing'] else '0626-v1'} -</code>.
      De volgende digest scherpt <strong>Op maat</strong> aan; <strong>Verrassing</strong> blijft gevarieerd.</p>
    </body></html>"""
