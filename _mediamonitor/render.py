"""HTML + plain-text email body for the daily briefing.

Designed for inbox readability: generous whitespace, clear hierarchy, no
visual clutter. Inline styles only — most mail clients strip <style> blocks
in <head>, so critical styling is doubled inline where it matters.
"""

import html

_DEFAULT_TITLE = "Mediamonitor"
_DEFAULT_FOOTER = (
    "Automatisch gegenereerd door _mediamonitor. "
    "Bronnen: Belgische pers (NL+FR) + sectorpers. "
    "Topic-filtering en samenvatting door Claude, strikt uit de artikeltekst."
)


# Inline-style helpers keep the markup readable below.
_STY = {
    "body":      "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;"
                 "color:#1a1a1a;max-width:680px;margin:0 auto;padding:32px 24px;line-height:1.5;",
    "h1":        "font-size:24px;font-weight:600;margin:0 0 8px 0;letter-spacing:-0.01em;",
    "lede":      "color:#666;font-size:13px;margin:0 0 36px 0;",
    "section":   "margin:40px 0 0 0;",
    "h2":        "font-size:15px;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;"
                 "color:#0a4ea5;margin:0 0 4px 0;",
    "count":     "font-size:13px;font-weight:400;color:#999;text-transform:none;letter-spacing:0;",
    "h2_rule":   "border:0;border-top:2px solid #0a4ea5;width:32px;margin:0 0 16px 0;",
    "empty":     "color:#999;font-style:italic;font-size:13px;margin:0;",
    "item":      "margin:0 0 22px 0;padding:0;",
    "topic":     "display:inline-block;background:#eef3f9;color:#0a4ea5;font-size:10px;"
                 "font-weight:600;text-transform:uppercase;letter-spacing:0.04em;"
                 "padding:2px 8px;border-radius:3px;margin-right:8px;vertical-align:middle;",
    "title":     "font-size:15px;font-weight:600;color:#1a1a1a;text-decoration:none;line-height:1.35;",
    "summary":   "color:#333;font-size:14px;margin:6px 0 0 0;line-height:1.55;",
    "actie":     "color:#0a4ea5;font-size:13px;margin:6px 0 0 0;line-height:1.5;"
                 "background:#f1f6fc;padding:6px 10px;border-radius:4px;",
    "meta":      "color:#888;font-size:12px;margin:6px 0 0 0;",
    "meta_link": "color:#888;text-decoration:none;",
    "tag_pwall": "display:inline-block;background:#fbe9e9;color:#a13b3b;font-size:10px;"
                 "font-weight:600;padding:1px 6px;border-radius:3px;margin-left:6px;",
    "tag_snip":  "display:inline-block;background:#f3f3f3;color:#777;font-size:10px;"
                 "font-weight:600;padding:1px 6px;border-radius:3px;margin-left:6px;",
    "foot":      "margin-top:48px;padding-top:16px;border-top:1px solid #eee;"
                 "color:#aaa;font-size:11px;line-height:1.5;",
}


def _source_tag(status):
    """Small badge next to the summary to flag where the text comes from."""
    if status == "rss_snippet_paywall":
        return f"<span style=\"{_STY['tag_pwall']}\">achter betaalmuur</span>"
    if status in ("rss_snippet_fail", "rss_snippet_thin", "rss_snippet_parsefail", "rss_snippet_noenrich"):
        return f"<span style=\"{_STY['tag_snip']}\">enkel snippet</span>"
    return ""


def render_html(today_str, by_company, stats, companies,
                title=_DEFAULT_TITLE, footer=_DEFAULT_FOOTER, show_action=False):
    out = []
    out.append("<!doctype html><html><head><meta charset='utf-8'></head>")
    out.append(f"<body style=\"{_STY['body']}\">")

    out.append(f"<h1 style=\"{_STY['h1']}\">{html.escape(title)}</h1>")
    lookback = stats.get("lookback_hours")
    window = f"laatste {lookback}u" if lookback else "vandaag"
    out.append(
        f"<div style=\"{_STY['lede']}\">"
        f"{html.escape(today_str)} &middot; {window} &middot; "
        f"{stats.get('articles_deduped', stats['articles_total'])} unieke artikels uit "
        f"{stats['feeds_total']} bronnen &middot; {stats['hits_post']} relevant"
        f"</div>"
    )

    for key, cfg in companies.items():
        items = by_company.get(key) or []
        out.append(f"<section style=\"{_STY['section']}\">")
        out.append(
            f"<h2 style=\"{_STY['h2']}\">{html.escape(cfg['label'])} "
            f"<span style=\"{_STY['count']}\">&middot; {len(items)}</span></h2>"
        )
        out.append(f"<hr style=\"{_STY['h2_rule']}\">")
        if not items:
            out.append(f"<p style=\"{_STY['empty']}\">Geen relevante berichtgeving vandaag.</p>")
            out.append("</section>")
            continue
        for art in items:
            title    = html.escape(art["title"])
            link     = html.escape(art["link"])
            src      = html.escape(art["source"])
            topic    = html.escape(art.get("topic", ""))
            # Alleen de feitelijke samenvatting. `nut` (waarom dit de lezer
            # raakt) wordt bewust niet getoond; het dient enkel als interne
            # motivering bij het relevantie-oordeel van de filter.
            summary  = html.escape(art.get("summary_long") or "")
            srctag   = _source_tag(art.get("summary_source", ""))
            topic_html = f"<span style=\"{_STY['topic']}\">{topic}</span>" if topic else ""

            out.append(f"<div style=\"{_STY['item']}\">")
            out.append(
                f"<div>{topic_html}"
                f"<a href=\"{link}\" style=\"{_STY['title']}\">{title}</a></div>"
            )
            if summary:
                out.append(f"<p style=\"{_STY['summary']}\">{summary}{srctag}</p>")
            actie = html.escape(art.get("actie") or "") if show_action else ""
            if actie:
                out.append(
                    f"<p style=\"{_STY['actie']}\"><strong>Actie:</strong> {actie}</p>"
                )
            out.append(
                f"<div style=\"{_STY['meta']}\">"
                f"<a href=\"{link}\" style=\"{_STY['meta_link']}\">{src} &rsaquo;</a>"
                f"</div>"
            )
            out.append("</div>")
        out.append("</section>")

    out.append(f"<div style=\"{_STY['foot']}\">{html.escape(footer)}</div>")
    out.append("</body></html>")
    return "".join(out)


def render_text(today_str, by_company, companies, title=_DEFAULT_TITLE,
                show_action=False):
    lines = [f"{title} - {today_str}", ""]
    for key, cfg in companies.items():
        items = by_company.get(key) or []
        header = f"{cfg['label']} ({len(items)})"
        lines.append(header)
        lines.append("=" * len(header))
        if not items:
            lines.append("(geen relevante berichtgeving)")
        else:
            for art in items:
                tag = f"[{art['topic']}] " if art.get("topic") else ""
                lines.append(f"\n* {tag}{art['title']}")
                summary = art.get("summary_long") or ""
                if summary:
                    lines.append(f"  {summary}")
                if show_action and art.get("actie"):
                    lines.append(f"  ACTIE: {art['actie']}")
                src_status = art.get("summary_source", "")
                marker = ""
                if src_status == "rss_snippet_paywall":
                    marker = " [achter betaalmuur]"
                elif src_status.startswith("rss_snippet"):
                    marker = " [enkel snippet]"
                lines.append(f"  bron: {art['source']}{marker}")
                lines.append(f"  {art['link']}")
        lines.append("")
    return "\n".join(lines)
