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
        out[k] = {"url": v, "tier": "press"}
    for k, v in SECTOR_PRESS.items():
        out[k] = {"url": v, "tier": "sector"}
    return out
