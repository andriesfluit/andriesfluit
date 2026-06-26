"""Autonomous capture — fetch today's De Standaard edition WITHOUT login.

The probe (check_public.py) established two facts:
  1. The per-edition Twipe JSON — both the package and the full-text content
     items — is public on the CDN. Only edition *discovery* sits behind the
     Mediahuis SSO.
  2. Edition IDs are sequential: De Standaard's main edition steps +2 per
     calendar day (3303=24 Jun, 3305=25 Jun, 3307=26 Jun), and nearby IDs are
     publicly fetchable by ID.

So we find today's edition by predicting its ID from the last known one and
scanning the numeric neighbourhood, picking the package whose PublicationDate
matches today's Brussels date. No credentials required.
"""

import json
import logging
import urllib.error
import urllib.request
from datetime import date, datetime

try:
    from zoneinfo import ZoneInfo
    _BRUSSELS = ZoneInfo("Europe/Brussels")
except ImportError:  # pragma: no cover
    _BRUSSELS = None

logger = logging.getLogger(__name__)

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
BASE = "https://epaper.standaard.be"

# Anchor used when no state file exists yet: 3307 == 2026-06-26.
SEED_ID = 3307
SEED_DATE = "2026-06-26"

# Bound how many candidate editions we probe, so a missing edition never makes
# the run hammer the CDN.
_MAX_PROBES = 24


def _today():
    now = datetime.now(_BRUSSELS) if _BRUSSELS else datetime.now()
    return now.date().isoformat()


def _get_json(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": BASE + "/"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if r.status != 200:
                return None
            return json.loads(r.read())
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError, TimeoutError):
        return None


def _package(ed):
    url = f"{BASE}/data/{ed}/data/GetContentPackagePublications-{ed}-V3.json"
    return _get_json(url)


def _candidate_ids(last_id, last_date, target_date):
    """Ordered list of edition IDs to probe: prediction first, then a scan."""
    cands = []
    try:
        diff = (date.fromisoformat(target_date) - date.fromisoformat(last_date)).days
        pred = last_id + 2 * diff
        # Prediction plus small offsets to absorb the odd skipped/extra day.
        cands += [pred + o for o in (0, 1, -1, 2, -2, 3, -3, 4, -4)]
    except (ValueError, TypeError):
        pass
    # Fallback: a forward scan from the last known id (editions only grow).
    cands += [last_id + i for i in range(0, 16)]
    seen, ordered = set(), []
    for c in cands:
        if c > 0 and c not in seen:
            seen.add(c)
            ordered.append(c)
    return ordered[:_MAX_PROBES]


def discover_edition(last_id, last_date, target_date):
    """Return (edition_id, package_dict) for target_date, or (None, None)."""
    for ed in _candidate_ids(last_id, last_date, target_date):
        pkg = _package(ed)
        if not pkg:
            continue
        d = (pkg.get("PublicationDate") or "")[:10]
        logger.info("  kandidaat-editie %s -> %s", ed, d or "?")
        if d == target_date:
            return ed, pkg
    return None, None


def fetch_bundle(last_id=None, last_date=None, target_date=None):
    """Fetch the full edition for target_date (default: today, Brussels) and
    return a bundle in the same shape capture/bookmarklet.js produces, or None
    if no edition for that date is published yet."""
    target = target_date or _today()
    last_id = last_id or SEED_ID
    last_date = last_date or SEED_DATE

    logger.info("zoek editie voor %s (vanaf laatst bekende %s/%s)",
                target, last_id, last_date)
    ed, pkg = discover_edition(last_id, last_date, target)
    if not ed:
        logger.warning("geen editie gevonden met datum %s", target)
        return None

    logger.info("editie %s gevonden voor %s", ed, target)
    publications = []
    for p in pkg.get("ContentPackagePublication", []):
        if not p.get("TextAvailable"):
            continue
        pub_id = p.get("PublicationID")
        ci = _get_json(f"{BASE}/data/{ed}/data/GetPublicationContentItems-{pub_id}.json")
        if ci:
            publications.append({"id": pub_id, "name": p.get("PublicationName"), "content": ci})
        else:
            logger.warning("publicatie %s niet opgehaald", pub_id)

    return {
        "edition": str(ed),
        "date": target,
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "package": pkg,
        "publications": publications,
    }
