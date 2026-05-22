"""HTML email body for the daily briefing."""

import html

from companies import COMPANIES


_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
       color: #1a1a1a; max-width: 720px; margin: 0 auto; padding: 24px; }
h1 { font-size: 22px; margin: 0 0 4px 0; }
.lede { color: #555; font-size: 13px; margin-bottom: 24px; }
h2 { font-size: 16px; margin: 28px 0 8px 0; padding-bottom: 4px;
     border-bottom: 1px solid #e0e0e0; }
.empty { color: #888; font-style: italic; font-size: 13px; }
.item { margin: 12px 0; }
.item a { color: #0a4ea5; text-decoration: none; font-weight: 500; }
.item a:hover { text-decoration: underline; }
.meta { color: #777; font-size: 12px; margin-top: 2px; }
.nut { color: #333; font-size: 13px; margin-top: 2px; }
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
        parts.append(f"<h2>{html.escape(cfg['label'])}</h2>")
        items = by_company.get(key) or []
        if not items:
            parts.append("<div class='empty'>Geen relevante berichtgeving vandaag.</div>")
            continue
        for art in items:
            title = html.escape(art["title"])
            link = html.escape(art["link"])
            src = html.escape(art["source"])
            nut = html.escape(art.get("nut", ""))
            parts.append(
                f"<div class='item'>"
                f"<a href='{link}'>{title}</a>"
                f"<div class='meta'>{src}</div>"
                + (f"<div class='nut'>{nut}</div>" if nut else "")
                + "</div>"
            )

    parts.append(
        "<div class='foot'>Automatisch gegenereerd door _mediamonitor. "
        "Bronnen: Belgische pers (NL+FR) + sectorpers via RSS/Google News.</div>"
    )
    parts.append("</body></html>")
    return "".join(parts)


def render_text(today_str, by_company):
    """Plain-text fallback for mail clients that prefer it."""
    lines = [f"Mediamonitor — {today_str}", ""]
    for key, cfg in COMPANIES.items():
        lines.append(cfg["label"])
        lines.append("-" * len(cfg["label"]))
        items = by_company.get(key) or []
        if not items:
            lines.append("(geen relevante berichtgeving)")
        else:
            for art in items:
                lines.append(f"- {art['title']}")
                lines.append(f"  {art['link']}")
                if art.get("nut"):
                    lines.append(f"  → {art['nut']}")
                lines.append(f"  bron: {art['source']}")
        lines.append("")
    return "\n".join(lines)
