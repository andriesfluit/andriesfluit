#!/usr/bin/env python3
"""Generic probe: is a Twipe e-paper source reachable WITHOUT login, and what
is its edition-ID pattern? Run from the open internet (GitHub Actions).

Usage: python check_source.py BASE_URL EDITION_ID
  e.g. python check_source.py https://krant.tijd.be 3330
"""

import json
import sys
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")


def get(base, url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": base + "/"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, (e.read() or b"")
    except Exception as e:  # noqa: BLE001
        return None, str(e).encode()


def main():
    base = sys.argv[1].rstrip("/")
    ed = sys.argv[2]
    print(f"== Probe {base} — editie {ed} ==\n")

    # Package JSON (publication list) without auth.
    pkg_url = f"{base}/data/{ed}/data/GetContentPackagePublications-{ed}-V3.json"
    st, body = get(base, pkg_url)
    print(f"[1] Package JSON -> HTTP {st} · {len(body)} bytes")
    pub_ids = []
    if st == 200:
        try:
            pkg = json.loads(body)
            date = (pkg.get("PublicationDate") or "")[:10]
            pubs = pkg.get("ContentPackagePublication") or []
            pub_ids = [str(p.get("PublicationID")) for p in pubs if p.get("TextAvailable")]
            print(f"    OK · datum={date} · {len(pubs)} publicaties · text-pubs={pub_ids[:6]}")
        except Exception as e:  # noqa: BLE001
            print(f"    onparseerbaar: {e}")

    # Content items (full text) — the decisive test.
    test_pub = pub_ids[0] if pub_ids else ed
    st, body = get(base, f"{base}/data/{ed}/data/GetPublicationContentItems-{test_pub}.json")
    print(f"\n[2] Content items JSON (pub {test_pub}) -> HTTP {st} · {len(body)} bytes")
    if st == 200:
        try:
            items = (json.loads(body).get("Content") or [])
            has_text = any(((c.get("ContentItem") or [{}])[0] or {}).get("HtmlText") for c in items)
            print(f"    OK · {len(items)} items · volledige tekst aanwezig: {has_text}")
        except Exception as e:  # noqa: BLE001
            print(f"    onparseerbaar: {e}")

    # ID-scan to learn the per-day increment.
    base_ed = int(ed)
    print(f"\n[3] ID-scan {base_ed-5}..{base_ed+6} (package-datum per ID):")
    for cand in range(base_ed - 5, base_ed + 7):
        url = f"{base}/data/{cand}/data/GetContentPackagePublications-{cand}-V3.json"
        st, body = get(base, url)
        info = ""
        if st == 200:
            try:
                pkg = json.loads(body)
                info = (f"datum={(pkg.get('PublicationDate') or '')[:10]} "
                        f"naam={(pkg.get('ContentPackagePublication') or [{}])[0].get('PublicationName','?')}")
            except Exception:
                info = "(200, onparseerbaar)"
        print(f"    {cand}: HTTP {st} {info}")


if __name__ == "__main__":
    main()
