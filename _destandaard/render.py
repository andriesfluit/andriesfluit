"""Render the digest to Markdown (the file Andries keeps / drops in a project)
and to HTML (the email body). Both show the feedback handles so he can react."""

import html as _html


def _stars(score):
    return "★" * int(score) + "☆" * (5 - int(score))


def render_markdown(meta, digest):
    date = meta.get("date", "")
    edition = meta.get("edition", "")
    out = [f"# De Standaard — digest", ""]
    out.append(f"**{date}** · editie {edition} · {meta.get('article_count', 0)} artikels in de editie")
    out.append("")
    if digest.get("rode_draad"):
        out.append(f"> **Rode draad.** {digest['rode_draad']}")
        out.append("")

    out.append("## Op maat")
    out.append("")
    for a in digest["kern"]:
        out.append(f"### `{a['handle']}` · {a['title']}")
        meta_line = f"*p{a.get('page')} · {a['rubriek']}*"
        if a.get("author"):
            meta_line = f"*p{a.get('page')} · {a['rubriek']} · {a['author']}*"
        out.append(f"{meta_line} · {_stars(a.get('score', 3))}")
        out.append("")
        if a.get("waarom"):
            out.append(f"_{a['waarom']}_")
            out.append("")
        out.append(a.get("samenvatting", ""))
        out.append("")

    out.append("## Verrassing — buiten je bubbel")
    out.append("")
    out.append("_Bewust gekozen buiten je opgegeven voorkeuren, om je geen "
               "echokamer in te sturen._")
    out.append("")
    for a in digest["verrassing"]:
        out.append(f"### `{a['handle']}` · {a['title']}")
        meta_line = f"*p{a.get('page')} · {a['rubriek']}*"
        if a.get("author"):
            meta_line = f"*p{a.get('page')} · {a['rubriek']} · {a['author']}*"
        out.append(meta_line)
        out.append("")
        if a.get("waarom"):
            out.append(f"_{a['waarom']}_")
            out.append("")
        out.append(a.get("samenvatting", ""))
        out.append("")

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

    def article_block(a, show_score):
        author = f" · {_h(a['author'])}" if a.get("author") else ""
        score = f" · <span style='color:#c8860a'>{_stars(a.get('score', 3))}</span>" if show_score else ""
        why = (f"<p style='margin:4px 0;color:#555;font-style:italic'>{_h(a['waarom'])}</p>"
               if a.get("waarom") else "")
        return f"""
        <div style="margin:0 0 22px 0">
          <div style="font-size:12px;color:#999;font-family:monospace">{_h(a['handle'])}</div>
          <h3 style="margin:2px 0 2px 0;font-size:17px;line-height:1.3">{_h(a['title'])}</h3>
          <div style="font-size:12px;color:#888">p{_h(str(a.get('page')))} · {_h(a['rubriek'])}{author}{score}</div>
          {why}
          <p style="margin:6px 0;line-height:1.5">{_h(a.get('samenvatting',''))}</p>
        </div>"""

    rode = (f"<p style='background:#f5f1e8;padding:12px 14px;border-left:3px solid #c8860a;"
            f"margin:0 0 22px 0'><strong>Rode draad.</strong> {_h(digest['rode_draad'])}</p>"
            if digest.get("rode_draad") else "")

    kern_html = "".join(article_block(a, True) for a in digest["kern"])
    verr_html = "".join(article_block(a, False) for a in digest["verrassing"])

    return f"""<!doctype html><html><body style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#1a1a1a;max-width:640px;margin:0 auto;padding:16px">
      <h1 style="font-size:22px;margin:0 0 4px 0">De Standaard — digest</h1>
      <div style="font-size:13px;color:#888;margin-bottom:20px">{_h(date)} · editie {_h(edition)} · {meta.get('article_count',0)} artikels in de editie</div>
      {rode}
      <h2 style="font-size:15px;text-transform:uppercase;letter-spacing:.05em;color:#444;border-bottom:1px solid #eee;padding-bottom:6px">Op maat</h2>
      {kern_html}
      <h2 style="font-size:15px;text-transform:uppercase;letter-spacing:.05em;color:#444;border-bottom:1px solid #eee;padding-bottom:6px">Verrassing — buiten je bubbel</h2>
      <p style="font-size:13px;color:#777;font-style:italic;margin-top:4px">Bewust gekozen buiten je opgegeven voorkeuren, om je geen echokamer in te sturen.</p>
      {verr_html}
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0">
      <p style="font-size:13px;color:#777">Feedback? Zet in <code>_destandaard/data/feedback.md</code> een regel als
      <code>{_h(digest['kern'][0]['handle']) if digest['kern'] else '0626-a1'} + meer van dit</code> of
      <code>{_h(digest['verrassing'][0]['handle']) if digest['verrassing'] else '0626-v1'} -</code>.
      De volgende digest scherpt <strong>Op maat</strong> aan; <strong>Verrassing</strong> blijft gevarieerd.</p>
    </body></html>"""
