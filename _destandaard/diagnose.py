"""One-shot diagnostic for the e-paper capture (run in CI, never scheduled).

Why this exists: since 2026-08-12 the De Standaard capture finds the edition
but fails to fetch its publication content, so main.py drops the whole title
and the digest silently ships with De Tijd only. capture._get_json swallows
every exception into None, so the run log cannot tell us whether that is a
403, a 404 or something else.

This script makes the failure legible. It repeats the exact capture steps
without hiding anything, and prints for each request the real HTTP status.
De Tijd runs as a control: the same code path works there, so a difference
between the two points straight at what changed on the standaard.be side.

Prints only. Sends no mail, writes no files, commits nothing.
"""

import json
import sys
import urllib.error
import urllib.request
from datetime import date, datetime

try:
    from zoneinfo import ZoneInfo
    _BRUSSELS = ZoneInfo("Europe/Brussels")
except ImportError:  # pragma: no cover
    _BRUSSELS = None

from capture import _candidate_ids
from sources import SOURCES

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")


def _today():
    now = datetime.now(_BRUSSELS) if _BRUSSELS else datetime.now()
    return now.date().isoformat()


def probe(base, url, timeout=30):
    """Return (status, note, payload). Unlike capture._get_json this reports
    the actual HTTP status instead of collapsing everything to None."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": base + "/"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            try:
                return r.status, f"{len(raw)} bytes", json.loads(raw)
            except ValueError:
                return r.status, f"{len(raw)} bytes, GEEN geldige JSON: {raw[:120]!r}", None
    except urllib.error.HTTPError as e:
        body = b""
        try:
            body = e.read()[:200]
        except Exception:
            pass
        return f"HTTP {e.code}", f"{e.reason} | body={body!r}", None
    except urllib.error.URLError as e:
        return "URLError", str(e.reason)[:160], None
    except Exception as e:
        return type(e).__name__, str(e)[:160], None


def state_for(key):
    try:
        p = f"data/{key}_last_edition.json"
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def diagnose(key, target):
    cfg = SOURCES[key]
    base = cfg["base"]
    st = state_for(key)
    print(f"\n{'='*72}\n{cfg['label']}  ({base})")
    print(f"state: editie {st.get('id')} van {st.get('date')}   doel: {target}")

    weekday = date.fromisoformat(target).weekday()
    if weekday not in cfg["days"]:
        print(f"LET OP: {cfg['label']} verschijnt niet op weekdag {weekday}; "
              f"vandaag zou sowieso overgeslagen worden.")

    # --- step 1: find the edition -------------------------------------
    ed, pkg = None, None
    if not st.get("id"):
        print("geen state-bestand met een editie-ID; kan niet voorspellen.")
        return
    for cand in _candidate_ids(st.get("id"), st.get("date"), target):
        status, note, data = probe(base, f"{base}/data/{cand}/data/"
                                         f"GetContentPackagePublications-{cand}-V3.json")
        if not isinstance(data, dict):
            print(f"  editie {cand}: {status} ({note})")
            continue
        d = (data.get("PublicationDate") or "")[:10]
        print(f"  editie {cand}: {status}, PublicationDate={d}")
        if d == target:
            ed, pkg = cand, data
            break

    if not pkg:
        print("GEEN editie met de juiste datum gevonden. Stopt hier.")
        return

    # --- step 2: what does the package promise? -----------------------
    pubs = pkg.get("ContentPackagePublication") or []
    print(f"\neditie {ed} gevonden. {len(pubs)} publicatie(s) in het pakket:")
    for p in pubs:
        print(f"  - PublicationID={p.get('PublicationID')} "
              f"TextAvailable={p.get('TextAvailable')} "
              f"naam={p.get('PublicationName')!r}")
    top = sorted(k for k in pkg.keys())
    print(f"  pakket-velden: {top}")

    # --- step 3: the step that actually fails -------------------------
    print("\ninhoud per publicatie (dit is de stap die faalt):")
    for p in pubs:
        if not p.get("TextAvailable"):
            continue
        pid = p.get("PublicationID")
        url = f"{base}/data/{ed}/data/GetPublicationContentItems-{pid}.json"
        status, note, data = probe(base, url)
        print(f"  [{status}] {url}\n        {note}")
        if isinstance(data, dict):
            print(f"        OK, top-level velden: {sorted(data.keys())[:8]}")
            continue

        # Only on failure: try nearby patterns so one run tells us whether the
        # endpoint moved or genuinely needs auth. Purely informational.
        for label, alt in [
            ("V3-suffix",   f"{base}/data/{ed}/data/GetPublicationContentItems-{pid}-V3.json"),
            ("editie-scope", f"{base}/data/{ed}/data/GetPublicationContentItems-{ed}-{pid}.json"),
            ("zonder /data", f"{base}/data/{ed}/GetPublicationContentItems-{pid}.json"),
        ]:
            s2, n2, d2 = probe(base, alt)
            flag = "  <-- WERKT" if isinstance(d2, dict) else ""
            print(f"        alt {label}: [{s2}] {n2[:80]}{flag}")


def main():
    # The workflow always passes an argument; it is empty for "today".
    target = (sys.argv[1].strip() if len(sys.argv) > 1 else "") or _today()
    print(f"diagnose voor {target} (Brussel)")
    for key in ("destandaard", "detijd"):
        try:
            diagnose(key, target)
        except Exception as e:
            print(f"[{key}] diagnose zelf gefaald: {type(e).__name__}: {e}")
    print(f"\n{'='*72}\nklaar.")


if __name__ == "__main__":
    main()
