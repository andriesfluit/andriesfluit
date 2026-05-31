"""RSS feed catalogue for the mediamonitor.

The Belgian generalist set is the same as _trumpflood/fetcher.py (kept in
sync manually — they're independent apps but the press landscape is shared).
The sector set adds outlets specific to our portfolio companies' worlds:
retail (IKEA), HR/uitzendwerk (Accent, NowJobs), filantropie (Helios) and
wegenbouw/asfalt (BVA/ABPE). Sector outlets that don't expose stable RSS
are reached via Google News' site: filter, which is how _trumpflood already
handles Cloudflare-gated outlets like Tijd and Le Soir.
"""

# ---- Belgische generalist (NL + FR) -----------------------------------
BELGIAN_PRESS = {
    "vrt":         "https://www.vrt.be/vrtnws/nl.rss.articles.xml",
    "standaard":   "https://www.standaard.be/rss/section/1f2838d4-99ea-49f0-9102-138784c7ea7c",
    "hln":         "https://www.hln.be/rss.xml",
    "demorgen":    "https://www.demorgen.be/in-het-nieuws/rss.xml",
    "nieuwsblad":  "https://www.nieuwsblad.be/rss/",
    "gva":         "https://www.gva.be/rss/",
    "hbvl":        "https://www.hbvl.be/rss/",
    "knack":       "https://news.google.com/rss/search?q=site:knack.be+when:2d&hl=nl-BE&gl=BE&ceid=BE:nl",
    "bruzz":       "https://www.bruzz.be/rss.xml",
    "rtbf":        "https://rss.rtbf.be/article/rss/highlight_rtbf_info.xml?source=internal",
    "lalibre":     "https://www.lalibre.be/arc/outboundfeeds/rss/?outputType=xml",
    "lecho":       "https://news.google.com/rss/search?q=site:lecho.be+when:2d&hl=fr-BE&gl=BE&ceid=BE:fr",
    "dhnet":       "https://www.dhnet.be/arc/outboundfeeds/rss/?outputType=xml",
    "septsursept": "https://www.7sur7.be/rss.xml",
    "bx1":         "https://bx1.be/feed/",
    "detijd":      "https://news.google.com/rss/search?q=site:tijd.be+when:2d&hl=nl-BE&gl=BE&ceid=BE:nl",
    "lesoir":      "https://news.google.com/rss/search?q=site:lesoir.be+when:2d&hl=fr-BE&gl=BE&ceid=BE:fr",
    "sudinfo":     "https://news.google.com/rss/search?q=site:sudinfo.be+when:2d&hl=fr-BE&gl=BE&ceid=BE:fr",
    "lavenir":     "https://news.google.com/rss/search?q=site:lavenir.net+when:2d&hl=fr-BE&gl=BE&ceid=BE:fr",
    "rtl":         "https://news.google.com/rss/search?q=site:rtl.be+when:2d&hl=fr-BE&gl=BE&ceid=BE:fr",
    "trends":      "https://news.google.com/rss/search?q=site:trends.knack.be+when:2d&hl=nl-BE&gl=BE&ceid=BE:nl",
    "tendances":   "https://news.google.com/rss/search?q=site:trends.levif.be+when:2d&hl=fr-BE&gl=BE&ceid=BE:fr",
}

# ---- Sectorpers (NL + FR) ---------------------------------------------
# Strategy: where a stable RSS exists, use it. Otherwise fall back to a
# Google News site: query (when:2d so the LLM filter doesn't see stale
# headlines; the per-day filter in fetcher.py then keeps only today).
SECTOR_PRESS = {
    # Retail (IKEA)
    "retaildetail_nl": "https://news.google.com/rss/search?q=site:retaildetail.be+when:2d&hl=nl-BE&gl=BE&ceid=BE:nl",
    "retaildetail_fr": "https://news.google.com/rss/search?q=site:retaildetail.eu+when:2d&hl=fr-BE&gl=BE&ceid=BE:fr",
    "gondola":         "https://news.google.com/rss/search?q=site:gondola.be+when:2d&hl=nl-BE&gl=BE&ceid=BE:nl",

    # HR / uitzendwerk (Accent, NowJobs)
    "hrsquare":   "https://news.google.com/rss/search?q=site:hrsquare.be+when:2d&hl=nl-BE&gl=BE&ceid=BE:nl",
    "hrmagazine": "https://news.google.com/rss/search?q=site:hrmagazine.be+when:2d&hl=nl-BE&gl=BE&ceid=BE:nl",
    "jobat":      "https://news.google.com/rss/search?q=site:jobat.be+when:2d&hl=nl-BE&gl=BE&ceid=BE:nl",
    "references": "https://news.google.com/rss/search?q=site:references.lesoir.be+when:2d&hl=fr-BE&gl=BE&ceid=BE:fr",

    # Wegenbouw / asfalt (BVA / ABPE)
    "bouwkroniek":     "https://news.google.com/rss/search?q=site:bouwkroniek.be+when:2d&hl=nl-BE&gl=BE&ceid=BE:nl",
    "construction_be": "https://news.google.com/rss/search?q=site:cstc.be+when:2d&hl=fr-BE&gl=BE&ceid=BE:fr",

    # Filantropie / non-profit (Helios)
    "alter_echos": "https://news.google.com/rss/search?q=site:alterechos.be+when:2d&hl=fr-BE&gl=BE&ceid=BE:fr",
}

# Outlets behind Cloudflare that need cloudscraper to bypass the JS challenge.
# Same set as _trumpflood; keep in sync.
CLOUDSCRAPER_FEEDS = {"standaard"}

CLOUDSCRAPER_FALLBACKS = {
    "standaard": "https://news.google.com/rss/search?q=site:standaard.be+when:1d&hl=nl-BE&gl=BE&ceid=BE:nl",
}


def all_feeds():
    """Return the combined feed catalogue with a `tier` annotation per entry."""
    out = {}
    for k, v in BELGIAN_PRESS.items():
        out[k] = {"url": v, "tier": "press", "company_key": None}
    for k, v in SECTOR_PRESS.items():
        out[k] = {"url": v, "tier": "sector", "company_key": None}
    return out


# -----------------------------------------------------------------------
# Per-company Google News SEARCH feeds.
# Outlet-wide feeds above only see what scrolls past the homepage. To catch
# every mention of a brand, named competitor or policy term across the whole
# Belgian press, we additionally query Google News' search index for each
# term in nl-BE and fr-BE locales. Quoted "..." forces exact-phrase match,
# which is the difference between catching "Accent Jobs" and drowning in
# every article that mentions an accent grave.

from urllib.parse import quote_plus


def _gnews_search_url(term, locale, when_hours):
    """Build a Google News RSS search URL for an exact-phrase term."""
    quoted = f'"{term}"'
    q = quote_plus(f"{quoted} when:{when_hours}h")
    if locale == "nl":
        return f"https://news.google.com/rss/search?q={q}&hl=nl-BE&gl=BE&ceid=BE:nl"
    return f"https://news.google.com/rss/search?q={q}&hl=fr-BE&gl=BE&ceid=BE:fr"


def search_feeds_for(company_key, company_cfg, when_hours):
    """Return dict {feed_name: {url, tier, company_key}} for one company's
    search terms. Each term expands to a nl-BE and a fr-BE Google News
    search. when_hours should be sized roughly to the lookback window
    plus some margin so Google's own date-filter doesn't pre-truncate."""
    search_terms = company_cfg.get("search_terms") or {}
    out = {}
    for category, terms in search_terms.items():
        for term in terms:
            slug = _slugify(term)
            for locale in ("nl", "fr"):
                key = f"search_{company_key}_{category}_{slug}_{locale}"
                out[key] = {
                    "url": _gnews_search_url(term, locale, when_hours),
                    "tier": "search",
                    "company_key": company_key,
                }
    return out


def _slugify(term):
    return "".join(c.lower() if c.isalnum() else "_" for c in term).strip("_")[:48]


def all_feeds_with_searches(companies, when_hours):
    """Combine outlet-wide feeds with per-company search feeds."""
    out = all_feeds()
    for key, cfg in companies.items():
        out.update(search_feeds_for(key, cfg, when_hours))
    return out
