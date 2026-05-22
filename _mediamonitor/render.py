"""HTML + plain-text email body for the daily briefing."""

import html

from companies import COMPANIES


_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
       color: #1a1a1a; max-width: 760px; margin: 0 auto; padding: 24px; }
h1 { font-size: 22px; margin: 0 0 4px 0; }
.lede { color: #555; font-size: 13px; margin-bottom: 24px; }
h2 { font-size: 16px; margin: 28px 0 4px 0; padding-bottom: 4px;
     border-bottom: 1px solid #e0e0e0; }
.brief { color: #888; font-size: 12px; font-style: italic; margin-bottom: 8px; }
.empty { color: #888; font-style: italic; font-size: 13px; }
.item { margin: 14px 0; }
.item a { color: #0a4ea5; text-decoration: none; font-weight: 500; }
.item a:hover { text-decoration: underline; }
.topic { display: inline-block; background: #eef3f9; color: #0a4ea5;
         font-size: 11px; font-weight: 600; padding: 1px 6px; border-radius: 3px;
         margin-right: 6px; vertical-align: middle; }
.meta { color: #777; font-size: 12px; margin-top: 2px; }
.nut  { color: #333; font-size: 13px; margin-top: 2px; }
.foot { margin-top: 32px; padding-top: 12px; border-top: 1px solid #eee;
        color: #999; font-size: 11px; }
"""


def render_html(today_str, by_company, stats):
    parts = [f"<!doctype html><html><head><meta charset='utf-8'><style>{_CSS}</style></head><body>"]
    parts.append(f"<h1>Mediamonitor — {html.escape(today_str)}</h1>")
    parts.append(
        f"<div class='lede'>"
        f"{stats['articles_total']} artikels gescand uit {stats['feeds_total']} bronnen, "
        f"{stats['hits_pre']} ruwe hits, {stats['hits_post']} relevant na filter."
        f"</div>"
    )

    for key, cfg in COMPANIES.items():
        items = by_company.get(key) or []
        parts.append(f"<h2>{html.escape(cfg['label'])} <span style='color:#999;font-weight:normal;font-size:12px;'>({len(items)})</span></h2>")
        if not items:
            parts.append("<div class='empty'>Geen relevante berichtgeving vandaag.</div>")
            continue
        for art in items:
            title = html.escape(art["title"])
            link  = html.escape(art["link"])
            src   = html.escape(art["source"])
            topic = html.escape(art.get("topic", ""))
            nut   = html.escape(art.get("nut", ""))
            topic_html = f"<span class='topic'>{topic}</span>" if topic else ""
            parts.append(
                f"<div class='item'>"
                f"{topic_html}<a href='{link}'>{title}</a>"
                f"<div class='meta'>{src}</div>"
                + (f"<div class='nut'>{nut}</div>" if nut else "")
                + "</div>"
            )

    parts.append(
        "<div class='foot'>Automatisch gegenereerd door _mediamonitor. "
        "Bronnen: Belgische pers (NL+FR) + sectorpers. Topic-filtering door Claude.</div>"
    )
    parts.append("</body></html>")
    return "".join(parts)


def render_text(today_str, by_company):
    lines = [f"Mediamonitor — {today_str}", ""]
    for key, cfg in COMPANIES.items():
        items = by_company.get(key) or []
        header = f"{cfg['label']} ({len(items)})"
        lines.append(header)
        lines.append("-" * len(header))
        if not items:
            lines.append("(geen relevante berichtgeving)")
        else:
            for art in items:
                tag = f"[{art['topic']}] " if art.get("topic") else ""
                lines.append(f"- {tag}{art['title']}")
                lines.append(f"  {art['link']}")
                if art.get("nut"):
                    lines.append(f"  → {art['nut']}")
                lines.append(f"  bron: {art['source']}")
        lines.append("")
    return "\n".join(lines)
