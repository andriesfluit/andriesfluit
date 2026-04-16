#!/usr/bin/env python3
"""Probe a batch of additional Belgian RSS feeds to see which still work
when called from a real Python process with a browser-like User-Agent."""
import sys
import time

import feedparser
import requests

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "nl-BE,nl;q=0.9,fr;q=0.8,en;q=0.7",
}

CANDIDATES = [
    # Vlaams
    ("HLN",            "https://www.hln.be/rss.xml"),
    ("De Standaard A", "https://www.standaard.be/rss/section/1f2838d4-99ea-49f0-9102-138784c7ea7c"),
    ("De Morgen",      "https://www.demorgen.be/in-het-nieuws/rss.xml"),
    ("De Tijd",        "https://www.tijd.be/rss"),
    ("Nieuwsblad",     "https://www.nieuwsblad.be/rss"),
    ("GVA",            "https://www.gva.be/rss"),
    ("HBVL",           "https://www.hbvl.be/rss"),
    ("Knack",          "https://www.knack.be/nieuws/feed"),
    ("Sporza",         "https://sporza.be/nl.rss.articles.xml"),
    ("Bruzz",          "https://www.bruzz.be/rss.xml"),
    # Franstalig
    ("Le Soir",        "https://www.lesoir.be/rss2/9/cible_principale"),
    ("L'Echo",         "https://www.lecho.be/rss/top_stories.xml"),
    ("7sur7",          "https://www.7sur7.be/rss.xml"),
    ("Sudinfo",        "https://www.sudinfo.be/rss"),
    ("DH",             "https://www.dhnet.be/arc/outboundfeeds/rss/?outputType=xml"),
    ("L'Avenir",       "https://www.lavenir.net/rss"),
    ("RTL",            "https://www.rtl.be/info/rss"),
    ("BX1",            "https://bx1.be/feed/"),
    # Google News topic feeds (broader coverage)
    ("Goog NL Politics","https://news.google.com/rss/headlines/section/topic/POLITICS?hl=nl-BE&gl=BE&ceid=BE:nl"),
    ("Goog NL World",  "https://news.google.com/rss/headlines/section/topic/WORLD?hl=nl-BE&gl=BE&ceid=BE:nl"),
    ("Goog NL Business","https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=nl-BE&gl=BE&ceid=BE:nl"),
    ("Goog NL Tech",   "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=nl-BE&gl=BE&ceid=BE:nl"),
    ("Goog NL Sport",  "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=nl-BE&gl=BE&ceid=BE:nl"),
    ("Goog FR Politics","https://news.google.com/rss/headlines/section/topic/POLITICS?hl=fr-BE&gl=BE&ceid=BE:fr"),
    ("Goog FR World",  "https://news.google.com/rss/headlines/section/topic/WORLD?hl=fr-BE&gl=BE&ceid=BE:fr"),
    ("Goog FR Business","https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=fr-BE&gl=BE&ceid=BE:fr"),
]


def main():
    print(f"{'Feed':<20} {'Status':<8} {'Items':>6} {'Note'}")
    print("-" * 70)
    for label, url in CANDIDATES:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
            status = str(r.status_code)
            n = 0
            note = ""
            if r.status_code == 200:
                parsed = feedparser.parse(r.content)
                n = len(parsed.entries or [])
                if n == 0:
                    note = "(parsed but no entries)"
            else:
                note = r.reason
        except Exception as e:
            status = "ERR"
            n = 0
            note = e.__class__.__name__
        print(f"{label:<20} {status:<8} {n:>6}  {note}")
        time.sleep(0.5)


if __name__ == "__main__":
    main()
