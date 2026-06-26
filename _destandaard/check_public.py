#!/usr/bin/env python3
"""One-off probe: are De Standaard's Twipe JSON endpoints reachable WITHOUT a
logged-in session? Run from the open internet (GitHub Actions), no cookies.

Decides whether a 2 a.m. cron can scrape unauthenticated (option 1) or whether
we need automated login / a manual capture step. Stdlib only — no pip install.
"""

import json
import re
import sys
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
BASE = "https://epaper.standaard.be"


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": BASE + "/"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.geturl(), r.read()
    except urllib.error.HTTPError as e:
        return e.code, url, (e.read() or b"")
    except Exception as e:  # noqa: BLE001 — report any network failure verbatim
        return None, url, str(e).encode()


def main():
    ed = sys.argv[1] if len(sys.argv) > 1 else "3307"
    print(f"== Probe De Standaard e-paper (geen login) — editie {ed} ==\n")

    # 1. Landing page: status + any edition-id-like patterns in the HTML/JS.
    st, final, body = get(BASE + "/")
    print(f"[1] GET / -> HTTP {st} · final={final} · {len(body)} bytes")
    ids = sorted(set(re.findall(r"/data/(\d{3,6})/", body.decode("utf-8", "ignore"))))
    print(f"    editie-achtige id's in body: {ids[:10] or 'geen'}")

    # 2. Package JSON (list of publications) without auth.
    pkg_url = f"{BASE}/data/{ed}/data/GetContentPackagePublications-{ed}-V3.json"
    st, _, body = get(pkg_url)
    print(f"\n[2] Package JSON -> HTTP {st} · {len(body)} bytes")
    pub_ids = []
    if st == 200:
        try:
            pkg = json.loads(body)
            date = (pkg.get("PublicationDate") or "")[:10]
            pubs = pkg.get("ContentPackagePublication") or []
            pub_ids = [str(p.get("PublicationID")) for p in pubs if p.get("TextAvailable")]
            print(f"    OK · datum={date} · {len(pubs)} publicaties · text-pubs={pub_ids[:6]}")
        except Exception as e:  # noqa: BLE001
            print(f"    kon niet parsen: {e}")

    # 3. Content items JSON (the FULL article text) — the decisive test.
    test_pub = pub_ids[0] if pub_ids else "7552"
    ci_url = f"{BASE}/data/{ed}/data/GetPublicationContentItems-{test_pub}.json"
    st, _, body = get(ci_url)
    print(f"\n[3] Content items JSON (pub {test_pub}) -> HTTP {st} · {len(body)} bytes")
    if st == 200:
        try:
            ci = json.loads(body)
            items = ci.get("Content") or []
            has_text = any(((c.get("ContentItem") or [{}])[0] or {}).get("HtmlText")
                           for c in items)
            print(f"    OK · {len(items)} items · volledige tekst aanwezig: {has_text}")
        except Exception as e:  # noqa: BLE001
            print(f"    kon niet parsen: {e}")

    print("\n== Conclusie ==")
    print("Als [2] én [3] HTTP 200 geven mét volledige tekst -> endpoints zijn")
    print("publiek; een 2u-cron kan zonder login scrapen (mits we het editie-ID")
    print("per dag kunnen afleiden). Geven ze 401/403 -> login is vereist.")


if __name__ == "__main__":
    main()
