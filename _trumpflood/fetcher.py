import logging
from datetime import date, datetime, timezone

import feedparser
import requests

try:
    from zoneinfo import ZoneInfo          # Python 3.9+
    _BRUSSELS = ZoneInfo("Europe/Brussels")
except ImportError:                         # pragma: no cover
    _BRUSSELS = None

try:
    import cloudscraper
    _SCRAPER = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "darwin", "mobile": False}
    )
except ImportError:
    _SCRAPER = None

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

FEEDS = {
    # Aggregator feeds (broad)
    "google_nl":         "https://news.google.com/rss?hl=nl-BE&gl=BE&ceid=BE:nl",
    "google_fr":         "https://news.google.com/rss?hl=fr-BE&gl=BE&ceid=BE:fr",
    # Google News BE topic feeds (cover sport, tech, business so denominator
    # isn't politics-heavy)
    "google_nl_politics":"https://news.google.com/rss/headlines/section/topic/POLITICS?hl=nl-BE&gl=BE&ceid=BE:nl",
    "google_nl_world":   "https://news.google.com/rss/headlines/section/topic/WORLD?hl=nl-BE&gl=BE&ceid=BE:nl",
    "google_nl_business":"https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=nl-BE&gl=BE&ceid=BE:nl",
    "google_nl_tech":    "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=nl-BE&gl=BE&ceid=BE:nl",
    "google_nl_sport":   "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=nl-BE&gl=BE&ceid=BE:nl",
    "google_fr_politics":"https://news.google.com/rss/headlines/section/topic/POLITICS?hl=fr-BE&gl=BE&ceid=BE:fr",
    "google_fr_world":   "https://news.google.com/rss/headlines/section/topic/WORLD?hl=fr-BE&gl=BE&ceid=BE:fr",
    "google_fr_business":"https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=fr-BE&gl=BE&ceid=BE:fr",
    # Vlaams direct (mainstream)
    "vrt":       "https://www.vrt.be/vrtnws/nl.rss.articles.xml",
    "standaard": "https://www.standaard.be/rss/section/1f2838d4-99ea-49f0-9102-138784c7ea7c",
    "hln":       "https://www.hln.be/rss.xml",
    "demorgen":  "https://www.demorgen.be/in-het-nieuws/rss.xml",
    "nieuwsblad":"https://www.nieuwsblad.be/rss/",
    "gva":       "https://www.gva.be/rss/",
    "hbvl":      "https://www.hbvl.be/rss/",
    "knack":     "https://news.google.com/rss/search?q=site:knack.be+when:2d&hl=nl-BE&gl=BE&ceid=BE:nl",
    "sporza":    "https://sporza.be/nl.rss.articles.xml",
    "bruzz":     "https://www.bruzz.be/rss.xml",
    # Franstalig direct (mainstream)
    "rtbf":      "https://rss.rtbf.be/article/rss/highlight_rtbf_info.xml?source=internal",
    "lalibre":   "https://www.lalibre.be/arc/outboundfeeds/rss/?outputType=xml",
    "lecho":     "https://news.google.com/rss/search?q=site:lecho.be+when:2d&hl=fr-BE&gl=BE&ceid=BE:fr",
    "dhnet":     "https://www.dhnet.be/arc/outboundfeeds/rss/?outputType=xml",
    "septsursept":"https://www.7sur7.be/rss.xml",
    "bx1":       "https://bx1.be/feed/",
    # Outlets that block direct RSS access (Cloudflare 403). Google indexes
    # them anyway because Cloudflare lets Googlebot through; we fetch via
    # Google News' site: search RSS as a workaround. Titles include the
    # publisher name (e.g. " - Le Soir") which still match Trump regex fine.
    "detijd_g":    "https://news.google.com/rss/search?q=site:tijd.be+when:2d&hl=nl-BE&gl=BE&ceid=BE:nl",
    "lesoir_g":    "https://news.google.com/rss/search?q=site:lesoir.be+when:2d&hl=fr-BE&gl=BE&ceid=BE:fr",
    "sudinfo_g":   "https://news.google.com/rss/search?q=site:sudinfo.be+when:2d&hl=fr-BE&gl=BE&ceid=BE:fr",
    "lavenir_g":   "https://news.google.com/rss/search?q=site:lavenir.net+when:2d&hl=fr-BE&gl=BE&ceid=BE:fr",
    "rtl_g":       "https://news.google.com/rss/search?q=site:rtl.be+when:2d&hl=fr-BE&gl=BE&ceid=BE:fr",
    # Additional outlets missing from original set
    "trends_g":    "https://news.google.com/rss/search?q=site:trends.knack.be+when:2d&hl=nl-BE&gl=BE&ceid=BE:nl",
    "tendances_g": "https://news.google.com/rss/search?q=site:trends.levif.be+when:2d&hl=fr-BE&gl=BE&ceid=BE:fr",
}


def _entry_date(entry):
    """Return the entry's publication date as a Belgian local date.

    feedparser populates `published_parsed` / `updated_parsed` as UTC
    struct_time values regardless of the feed's timezone declaration. We
    convert to Europe/Brussels before taking the calendar date so the
    "today in Belgian local date" filter matches what a reader in Belgium
    would call "today".
    """
    for key in ("published_parsed", "updated_parsed"):
        val = entry.get(key)
        if val:
            utc_dt = datetime(
                val.tm_year, val.tm_mon, val.tm_mday,
                val.tm_hour, val.tm_min, val.tm_sec,
                tzinfo=timezone.utc,
            )
            if _BRUSSELS is not None:
                return utc_dt.astimezone(_BRUSSELS).date()
            return utc_dt.date()
    return None


_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "nl-BE,nl;q=0.9,fr;q=0.8,en;q=0.7",
}

# Feeds whose origin sits behind Cloudflare and need cloudscraper to bypass
# the basic JS challenge. Works on residential IPs; GitHub Actions' datacenter
# IPs are blocked by Cloudflare even with cloudscraper, so each entry here
# has a fallback URL used automatically when the primary fetch fails.
_CLOUDSCRAPER_FEEDS = {"standaard"}

_CLOUDSCRAPER_FALLBACKS = {
    "standaard": "https://news.google.com/rss/search?q=site:standaard.be+when:1d&hl=nl-BE&gl=BE&ceid=BE:nl",
}


# "Core" tier: national + regional-generalist outlets, i.e. outlets whose
# editorial scope is "general Belgian/international news" with broad national
# reach. Excluded from core (but still in the full corpus):
#   - Sporza                     (sport-only)
#   - Bruzz, BX1                 (Brussels-only hyperlocal)
#   - google_nl / google_fr      (general aggregators; overlap with direct feeds)
#   - google_*_topic feeds       (topic aggregators; overlap)
# De Tijd / Le Soir / Sudinfo / L'Avenir / RTL are reached via Google News'
# site: filter (their direct feeds are Cloudflare-gated); they stand in for
# the actual outlets and count as core.
CORE_FEED_KEYS = {
    # Direct Vlaams national + regional generalist
    "vrt", "standaard", "hln", "demorgen", "nieuwsblad", "hbvl", "knack",
    # Direct Franstalig national + regional generalist
    "rtbf", "lalibre", "lecho", "dhnet", "septsursept",
    # Via Google site: filter (direct RSS blocked or abandoned)
    "detijd_g", "lesoir_g", "sudinfo_g", "lavenir_g", "rtl_g",
    "trends_g", "tendances_g",
}


def _get(name, url):
    if _SCRAPER is not None and name in _CLOUDSCRAPER_FEEDS:
        return _SCRAPER.get(url, timeout=30)
    return requests.get(url, headers=_HEADERS, timeout=20)


def fetch_one(name, url, today):
    try:
        resp = _get(name, url)
        resp.raise_for_status()
    except Exception as e:
        fallback = _CLOUDSCRAPER_FALLBACKS.get(name)
        if fallback:
            logger.warning("fetch failed for %s (%s), trying fallback: %s", name, e, fallback)
            try:
                resp = requests.get(fallback, headers=_HEADERS, timeout=20)
                resp.raise_for_status()
                url = fallback
            except Exception as e2:
                logger.warning("fallback also failed for %s: %s", name, e2)
                return {"fetched": 0, "articles": []}
        else:
            logger.warning("fetch failed for %s: %s", name, e)
            return {"fetched": 0, "articles": []}

    parsed = feedparser.parse(resp.content)
    entries = parsed.entries or []
    fetched = len(entries)

    articles = []
    for entry in entries:
        d = _entry_date(entry)
        if d != today:
            continue
        link = entry.get("link")
        title = (entry.get("title") or "").strip()
        if not link or not title:
            continue
        articles.append((link, title))

    return {"fetched": fetched, "articles": articles}


def fetch_all(today):
    out = {}
    for name, url in FEEDS.items():
        out[name] = fetch_one(name, url, today)
    return out
