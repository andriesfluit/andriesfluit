"""Render output/index.html from data/log.json."""
import html
import json
from datetime import datetime
from pathlib import Path
try:
    from zoneinfo import ZoneInfo
    _BRUSSELS = ZoneInfo("Europe/Brussels")
except ImportError:                 # pragma: no cover
    _BRUSSELS = None

from comparators import COMPARATORS, label_for as comparator_label
from assessor import THRESHOLDS as _ASSESSOR_THRESHOLDS

ROOT = Path(__file__).parent
LOG_FILE = ROOT / "data" / "log.json"
# Write the generated site into the repo-root sibling folder so GitHub Pages
# serves it directly at andriesfluit.be/trumpflood/.
OUTPUT_DIR = ROOT.parent / "trumpflood"


def _build_zones():
    # Zone bands are derived from the composite classifier's share (pct)
    # floors so the chart stays honest when thresholds.json changes. A day
    # whose plotted share lands in a band may still be classified lower
    # because the real classifier also requires breadth, dominance and
    # rank floors to clear; the bands on the chart are a visual reference
    # for the share dimension only.
    puddles_lo  = _ASSESSOR_THRESHOLDS["puddles"]["pct"]
    wet_lo      = _ASSESSOR_THRESHOLDS["wet"]["pct"]
    soaked_lo   = _ASSESSOR_THRESHOLDS["soaked"]["pct"]
    flooding_lo = _ASSESSOR_THRESHOLDS["flooding"]["pct"]
    return [
        (0.0,          puddles_lo,   "dry",      "Dry"),
        (puddles_lo,   wet_lo,       "puddles",  "Puddles"),
        (wet_lo,       soaked_lo,    "wet",      "Wet"),
        (soaked_lo,    flooding_lo,  "soaked",   "Soaked"),
        (flooding_lo,  100.0,        "flooding", "Flooding"),
    ]


# Zone bands as (lower_bound, upper_bound, key, display_name).
# The waterline at percentage P sits in the zone where lower <= P < upper.
ZONES = _build_zones()
ZONE_KEYS = [z[2] for z in ZONES]

# Distinct, saturated color per zone for clear visual jumps.
ZONE_COLORS = {
    # Monochrome blue progression so the editorial beige/ink palette stays
    # intact. FLOODING keeps a red alert tone because it's genuinely the
    # "something's up" band, not a continuation of the same idea.
    "dry":      "#c8b89a",  # warm muted sand
    "puddles":  "#a8c4d8",  # dusty sky
    "wet":      "#4a7fa0",  # mid editorial blue
    "soaked":   "#1e3a5f",  # deep ink-blue
    "flooding": "#b03a2e",  # muted alarm red
}

ZONE_EMOJI = {
    "dry":      "\u2600\ufe0f",       # sun
    "puddles":  "\U0001F326\ufe0f",   # sun behind rain
    "wet":      "\U0001F327\ufe0f",   # cloud with rain
    "soaked":   "\u26C8\ufe0f",       # thundercloud
    "flooding": "\U0001F30A",         # wave
}

# Wave / animation intensity per zone. Higher zones = larger amplitude,
# faster periods, more visible motion. Drops are constant; the water
# itself is what gets more agitated.
ZONE_INTENSITY = {
    # zone:    (back_amp, front_amp, back_dur_s, front_dur_s, ripple_dur_s, bob_amp_px, bob_dur_s)
    "dry":      ( 8,  5, 10.0, 7.0, 4.0,  3, 5.0),
    "puddles":  (14,  9,  7.0, 5.0, 3.0,  5, 4.0),
    "wet":      (22, 14,  5.0, 3.5, 2.2,  8, 3.0),
    "soaked":   (32, 20,  3.5, 2.4, 1.6, 12, 2.2),
    "flooding": (44, 28,  2.2, 1.5, 1.0, 18, 1.5),
}


def _zone_for(pct):
    for lo, hi, key, name in ZONES:
        if lo <= pct < hi:
            return key
    return ZONES[-1][2]


def _zone_color(pct):
    return ZONE_COLORS[_zone_for(pct)]


# Subhead variants per zone. One is picked deterministically from the date so
# the page feels dynamic without flipping every reload.
SUBHEADS = {
    "dry": [
        "Belgium barely noticed.",
        "A quiet day on the wires.",
        "He didn't flood the zone today.",
    ],
    "puddles": [
        "First drips on the front pages.",
        "Just enough to wet the headlines.",
        "A steady drip, nothing more.",
    ],
    "wet": [
        "The floor is getting slippery.",
        "Wet streets in the news cycle.",
        "Showers across the front pages.",
    ],
    "soaked": [
        "Standing water across the press.",
        "He's soaking the cycle.",
        "The cycle is taking on water.",
    ],
    "flooding": [
        "He is flooding the zone.",
        "The dam has broken.",
        "Total inundation.",
    ],
}


def _subhead(pct, date_str):
    zone = _zone_for(pct)
    variants = SUBHEADS[zone]
    seed = sum(ord(c) for c in date_str) if date_str else 0
    return variants[seed % len(variants)]

SOURCE_LABELS = {
    "google_nl":          "Google News BE (NL)",
    "google_fr":          "Google News BE (FR)",
    "google_nl_politics": "GNews BE Politics (NL)",
    "google_nl_world":    "GNews BE World (NL)",
    "google_nl_business": "GNews BE Business (NL)",
    "google_nl_tech":     "GNews BE Tech (NL)",
    "google_nl_sport":    "GNews BE Sports (NL)",
    "google_fr_politics": "GNews BE Politics (FR)",
    "google_fr_world":    "GNews BE World (FR)",
    "google_fr_business": "GNews BE Business (FR)",
    "vrt":                "VRT NWS",
    "standaard":          "De Standaard",
    "hln":                "HLN",
    "demorgen":           "De Morgen",
    "nieuwsblad":         "Het Nieuwsblad",
    "gva":                "Gazet van Antwerpen",
    "hbvl":               "Het Belang van Limburg",
    "knack":              "Knack",
    "sporza":             "Sporza",
    "bruzz":              "Bruzz",
    "rtbf":               "RTBF",
    "lalibre":            "La Libre",
    "lecho":              "L'Echo",
    "dhnet":              "DH.net",
    "septsursept":        "7sur7",
    "bx1":                "BX1",
    "detijd_g":           "De Tijd",
    "lesoir_g":           "Le Soir",
    "sudinfo_g":          "Sudinfo",
    "lavenir_g":          "L'Avenir",
    "rtl_g":              "RTL Info",
    "trends_g":           "Trends",
    "tendances_g":        "Trends-Tendances",
}


def _interp(pct):
    """Smooth gradient (used for the PNG image bar). Site uses _zone_color."""
    start = (0xAE, 0xD6, 0xF1)
    end = (0x1A, 0x52, 0x76)
    t = max(0.0, min(1.0, pct / 100.0))
    rgb = tuple(int(start[i] + (end[i] - start[i]) * t) for i in range(3))
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _wave_uri(color, amp=10):
    """Inline SVG data URI for a tiling wave in the given color.
    `amp` controls visual amplitude (height of crests vs troughs)."""
    h = max(56, amp * 2 + 8)
    mid = h - amp - 4
    crest = mid - amp
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='240' height='{h}' "
        f"viewBox='0 0 240 {h}' preserveAspectRatio='none'>"
        f"<path d='M0,{mid} Q30,{crest} 60,{mid} T120,{mid} T180,{mid} T240,{mid} "
        f"L240,{h} L0,{h} Z' fill='{color}'/></svg>"
    )
    return "url(\"data:image/svg+xml;utf8," + svg.replace("#", "%23") + "\")"


# Weekday / month abbreviations so the timestamp reads naturally regardless
# of system locale.
_WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _format_last_run(iso_ts):
    """Turn an ISO timestamp (e.g. '2026-04-16T08:03:17+02:00') into a short
    human string for the masthead. Falls back to '—' if missing."""
    if not iso_ts:
        return "Last run: &mdash;"
    try:
        dt = datetime.fromisoformat(iso_ts)
    except ValueError:
        return f"Last run: {html.escape(iso_ts)}"

    # Parsed datetime only carries the UTC offset, not the zone name. Re-
    # anchor to Europe/Brussels so we get CET / CEST instead of "UTC+02:00".
    if _BRUSSELS is not None and dt.tzinfo is not None:
        dt = dt.astimezone(_BRUSSELS)

    # Compact Belgian-style read-out: "Wed 16 Apr 2026, 08:03 CEST".
    tz_name = dt.tzname() or ""
    base = (
        f"{_WEEKDAYS[dt.weekday()]} "
        f"{dt.day} {_MONTHS[dt.month - 1]} {dt.year}, "
        f"{dt.hour:02d}:{dt.minute:02d}"
    )
    if tz_name:
        base += f" {tz_name}"
    return f"Last run: {html.escape(base)}"


def _load_log():
    if not LOG_FILE.exists():
        return []
    try:
        data = json.loads(LOG_FILE.read_text())
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
    except json.JSONDecodeError:
        pass
    return []


def _hero(latest):
    pct = latest.get("percentage", 0.0)
    label = latest.get("label", "No data")
    total = latest.get("total_articles", 0)
    matches = latest.get("trump_articles", 0)
    # Secondary (expanded-detector) count: name + "White House", "US
    # president", etc. Missing on pre-transition records, so fall back to
    # trump_articles / percentage (same number, just labelled as expanded).
    matches_expanded = latest.get("trump_articles_expanded", matches)
    pct_expanded = latest.get("core_percentage_expanded", pct)
    indirect = latest.get("indirect_references", matches_expanded - matches)
    date_str = latest.get("date", "")
    rank = latest.get("rank")
    n_people = latest.get("n_people")
    n_themes = latest.get("n_themes")
    theme_rank = latest.get("theme_rank")
    dominance = latest.get("dominance")
    smoothed_pct = latest.get("smoothed_pct")
    wide_pct = latest.get("wide_percentage")
    method = latest.get("assessment_method", "pct")
    # Prefer stored zone; fall back to recomputing from pct (legacy records).
    active_zone = latest.get("zone") or _zone_for(pct)
    # Backwards compat: old records may have zone key "flooded".
    if active_zone == "flooded":
        active_zone = "soaked"
    color = ZONE_COLORS[active_zone]
    emoji = ZONE_EMOJI[active_zone]
    # Water rises to the TOP of the active zone band (visual escalation
    # matched to dramatic narrative). Actual % stays in the readout.
    try:
        zone_idx = ZONE_KEYS.index(active_zone)
    except ValueError:
        zone_idx = 0
    water_target = (zone_idx + 1) * (100 / len(ZONE_KEYS))
    subhead = latest.get("narrative") or _subhead(pct, date_str)

    # Build the vertical zone scale (bottom-up).
    # Layout: 5 equal-height bands (rank-based zones), bottom = DRY, top = FLOODING.
    # Water level is independent and shows the actual % share.
    band_share = 100 / len(ZONES)
    bands = []
    for i, (_, _, key, name) in enumerate(ZONES):
        is_active = (key == active_zone)
        band_color = ZONE_COLORS[key]
        cls = "band active" if is_active else "band"
        bottom = i * band_share
        bands.append(
            f'<div class="{cls}" style="bottom:{bottom:.2f}%;height:{band_share:.2f}%;'
            f'--band-color:{band_color}">'
            f'<span class="band-name">{name}</span>'
            f'</div>'
        )

    # Facts block (third tier of the readout). Built from the composite
    # signals so the hero is a single, self-contained summary: a reader
    # who scans only the hero gets zone, share, rank, outlet breadth and
    # the runner-up in one pass.
    breadth = latest.get("breadth")
    core_outlets_active = latest.get("core_outlets_active") or 0
    comps = latest.get("comparisons") or {}
    n_others = (n_people - 1) if n_people else 0

    facts = []
    if method in ("composite", "people") and rank is not None and n_people:
        dom_tail = ""
        if dominance is not None and dominance > 0:
            dom_tail = f" \u00b7 {dominance}\u00d7 vs. the other {n_others} combined"
        facts.append(
            f'<div class="fact">Rank <strong>#{rank}</strong> of '
            f'{n_people} named figures{dom_tail}</div>'
        )
    elif method == "rank" and rank is not None:
        facts.append(
            f'<div class="fact">Rank <strong>#{rank}</strong> of '
            f'{n_themes} subjects</div>'
        )

    if breadth is not None and core_outlets_active:
        outlets_with_trump = int(round(breadth * core_outlets_active))
        facts.append(
            f'<div class="fact">In <strong>{outlets_with_trump} of '
            f'{core_outlets_active}</strong> national outlets</div>'
        )
    elif breadth is not None:
        facts.append(
            f'<div class="fact">In <strong>{int(round(breadth * 100))}%</strong> '
            f'of outlets</div>'
        )

    # Runner-up (most-mentioned comparator other than Trump, if any).
    trump_count = comps.get("trump", matches)
    others_sorted = sorted(
        ((k, v) for k, v in comps.items() if k != "trump"),
        key=lambda kv: kv[1], reverse=True,
    )
    if others_sorted and others_sorted[0][1] > 0:
        rival_k, rival_v = others_sorted[0]
        facts.append(
            f'<div class="fact">Next up: '
            f'<strong>{html.escape(comparator_label(rival_k))}</strong> ({rival_v})</div>'
        )

    facts_html = (
        f'<div class="readout-facts">{"".join(facts)}</div>' if facts else ""
    )

    # Indirect-references sub-line. Only shown when there are indirect
    # references today AND we have the expanded figure (new-format records).
    if indirect and indirect > 0:
        indirect_line = (
            f'<div class="readout-indirect">'
            f'+ <strong>{indirect}</strong> more mention the White House, '
            f'&ldquo;US president&rdquo; or similar '
            f'(expanded: <strong>{matches_expanded}</strong> = '
            f'<strong>{pct_expanded}%</strong>)'
            f'</div>'
        )
    else:
        indirect_line = ""

    return f"""
<section class="hero">
  <div class="portrait-wrap">
    <div class="portrait" data-water-color="{color}" data-water-target="{water_target:.0f}" style="--water-color:{color};--water-target:{water_target:.0f}%">
      <img src="trump.jpg" alt="Donald Trump">
      <canvas class="water-canvas" aria-hidden="true"></canvas>
    </div>
    <div class="scale" aria-label="Flood zone scale">
      {''.join(bands)}
    </div>
  </div>
  <div class="readout">
    <div class="readout-label">{html.escape(label)}</div>
    <hr class="readout-sep" />
    <div class="readout-stat">
      <span class="pct" style="color:{color}">{pct}<span class="pct-symbol">%</span></span>
    </div>
    <div class="readout-sub">
      <strong>{matches}</strong> of <strong>{total}</strong> Belgian core-tier
      headlines name Trump
    </div>
    <hr class="readout-sep" />
    {facts_html}
    {indirect_line}
  </div>
</section>
"""


def _zone_definitions_block(latest):
    """Render each zone's definition as a card showing, gate by gate, what
    today's signals read and whether each gate cleared. Replaces the old
    static threshold matrix; lets a reader see at a glance which zone
    today lands in and which gates would need to flip for the next zone
    up to trigger."""
    from assessor import THRESHOLDS as _T

    pct = latest.get("percentage")
    rank = latest.get("rank")
    dominance = latest.get("dominance")
    breadth = latest.get("breadth")
    today_zone = latest.get("zone") or "dry"

    def _fmt_pct(v):
        return "\u2014" if v is None else f"{v}%"

    def _fmt_x(v):
        return "\u2014" if v is None else f"{v}\u00d7"

    def _fmt_breadth(v):
        return "\u2014" if v is None else f"{int(round(v * 100))}%"

    def _fmt_rank(v):
        return "\u2014" if v is None else f"#{v}"

    def _gate(pass_flag, label_text):
        if pass_flag is None:
            return (
                f'<li class="gate gate-na">'
                f'<span class="gate-mark">\u25CB</span> {label_text} '
                f'<span class="gate-note">(not gated for this zone)</span></li>'
            )
        mark = "\u2713" if pass_flag else "\u2717"
        cls = "gate-ok" if pass_flag else "gate-fail"
        return f'<li class="gate {cls}"><span class="gate-mark">{mark}</span> {label_text}</li>'

    def _zone_card(key, display):
        t = _T[key]
        share_floor = t.get("pct")
        dom_floor = t.get("dominance")
        breadth_floor = t.get("breadth")
        rank_ceil = t.get("rank_max")

        share_pass = (
            True if share_floor is None
            else (pct is not None and pct >= share_floor)
        )
        dom_pass = (
            None if dom_floor is None
            else (dominance is not None and dominance >= dom_floor)
        )
        breadth_pass = (
            None if breadth_floor is None
            else (breadth is None or breadth >= breadth_floor)
        )
        rank_pass = (
            True if rank_ceil is None
            else (rank is not None and rank <= rank_ceil)
        )

        all_pass = all(
            p is not False
            for p in (share_pass, dom_pass, breadth_pass, rank_pass)
        )
        card_cls = "zone-card"
        if all_pass:
            card_cls += " zone-card-cleared"
        if key == today_zone:
            card_cls += " zone-card-active"

        gates_html = []
        share_label = (
            f"Share &ge; <strong>{share_floor}%</strong> "
            f"(today: {_fmt_pct(pct)})"
            if share_floor is not None else
            f"Share not gated (today: {_fmt_pct(pct)})"
        )
        gates_html.append(_gate(share_pass, share_label))

        if dom_floor is not None:
            dom_label = (
                f"Dominance &ge; <strong>{dom_floor}\u00d7</strong> "
                f"(today: {_fmt_x(dominance)})"
            )
            gates_html.append(_gate(dom_pass, dom_label))
        else:
            gates_html.append(_gate(None, "Dominance"))

        if breadth_floor is not None:
            breadth_label = (
                f"Breadth &ge; <strong>{int(round(breadth_floor * 100))}%</strong> "
                f"of outlets (today: {_fmt_breadth(breadth)})"
            )
            gates_html.append(_gate(breadth_pass, breadth_label))
        else:
            gates_html.append(_gate(None, "Breadth"))

        if rank_ceil is not None:
            rank_label = (
                f"Rank \u2264 <strong>#{rank_ceil}</strong> "
                f"(today: {_fmt_rank(rank)})"
            )
            gates_html.append(_gate(rank_pass, rank_label))
        else:
            gates_html.append(_gate(None, "Rank"))

        badge = ""
        if key == today_zone:
            badge = '<span class="zone-card-badge">today</span>'
        elif all_pass:
            badge = '<span class="zone-card-badge subtle">all gates clear</span>'

        return (
            f'<div class="{card_cls}">'
            f'<div class="zone-card-head">'
            f'<span class="zone-card-swatch" style="background:{ZONE_COLORS[key]}"></span>'
            f'<span class="zone-card-name">{display}</span>'
            f'{badge}'
            f'</div>'
            f'<ul class="zone-gates">{"".join(gates_html)}</ul>'
            f'</div>'
        )

    zones_rendered = [
        _zone_card("flooding", "Flooding"),
        _zone_card("soaked",   "Soaked"),
        _zone_card("wet",      "Wet"),
        _zone_card("puddles",  "Puddles"),
    ]
    dry_note = (
        '<div class="zone-card zone-card-dry'
        + (' zone-card-active' if today_zone == "dry" else '')
        + '"><div class="zone-card-head">'
        f'<span class="zone-card-swatch" style="background:{ZONE_COLORS["dry"]}"></span>'
        '<span class="zone-card-name">Dry</span>'
        + ('<span class="zone-card-badge">today</span>' if today_zone == "dry" else '')
        + '</div><p class="zone-card-dry-note">Assigned when no zone above '
        'clears all of its gates.</p></div>'
    )
    return "".join(zones_rendered) + dry_note


def _comparison_panel(latest):
    comps = latest.get("comparisons")
    total = latest.get("total_articles", 0)
    if not comps or not total:
        return ""

    active_zone = latest.get("zone") or "dry"
    if active_zone == "flooded":
        active_zone = "soaked"

    items = sorted(comps.items(), key=lambda kv: kv[1], reverse=True)
    max_count = max((c for _, c in items), default=1) or 1

    rows = []
    for key, count in items:
        label = comparator_label(key)
        share = round(count / total * 100, 1)
        bar_w = (count / max_count) * 100
        is_trump = (key == "trump")
        cls = "comp-row trump" if is_trump else "comp-row"
        zone_color = ZONE_COLORS[active_zone] if is_trump else "#b8b1a0"
        rows.append(
            f'<div class="{cls}">'
            f'<div class="comp-label">{html.escape(label)}</div>'
            f'<div class="comp-bar-wrap">'
            f'<div class="comp-bar" style="width:{bar_w:.1f}%;background:{zone_color}"></div>'
            f'</div>'
            f'<div class="comp-stat"><strong>{count}</strong>'
            f'<span class="comp-share">{share}%</span></div>'
            f'</div>'
        )

    trump_count = comps.get("trump", 0)
    n_others = max(len(comps) - 1, 0)
    others_total = sum(v for k, v in comps.items() if k != "trump")
    if others_total:
        ratio = trump_count / others_total
        ratio_txt = f"{ratio:.2f}\u00d7"
        verdict = (
            f"more than all {n_others} others combined" if ratio > 1
            else f"less than all {n_others} others combined" if ratio < 1
            else f"exactly equal to all {n_others} others combined"
        )
    else:
        ratio_txt = "\u2014"
        verdict = "no other people mentioned today"

    vs_block = (
        f'<div class="vs-others">'
        f'<div class="vs-line"><strong>{trump_count}</strong> Trump '
        f'<span class="vs-vs">vs</span> '
        f'<strong>{others_total}</strong> all other people combined '
        f'<span class="vs-ratio">({ratio_txt})</span></div>'
        f'<div class="vs-verdict">Trump alone is {verdict}.</div>'
        f'</div>'
    )

    return f"""
<section class="block">
  <h2>Today vs. the rest</h2>
  <p class="block-intro">Trump against {n_others} other named figures in the same
  {total}-headline core corpus.</p>
  <div class="comparison">{''.join(rows)}</div>
  {vs_block}
</section>
"""


def _today_mentions(latest):
    matches = latest.get("matches") or []
    if not matches:
        return (
            '<section class="block"><h2>Today&rsquo;s mentions</h2>'
            '<p class="empty">No headlines mentioned Trump today.</p></section>'
        )
    # Sort name-only mentions first, indirect references last. Keeps the
    # primary set (what drives the zone) at the top.
    def _sort_key(m):
        return (0 if m.get("name_only", True) else 1,)
    sorted_matches = sorted(matches, key=_sort_key)

    items = []
    for m in sorted_matches:
        src = SOURCE_LABELS.get(m.get("source"), m.get("source", ""))
        url = html.escape(m.get("url", "#"), quote=True)
        title = html.escape(m.get("title", ""))
        # Tag indirect references so the reader can see which headlines
        # are included only because of the expanded detector.
        tag = ""
        if m.get("name_only") is False:
            tag = ' <span class="indirect-tag" title="Matched only via indirect reference (White House, US president, ...)">indirect</span>'
        items.append(
            f'<li><a href="{url}" target="_blank" rel="noopener">{title}</a>'
            f'{tag}<span class="src">{html.escape(src)}</span></li>'
        )
    return (
        '<section class="block"><h2>Today&rsquo;s mentions</h2>'
        '<p class="block-intro">Name mentions first; indirect references '
        '(&ldquo;White House&rdquo;, &ldquo;US president&rdquo;, ...) are '
        'tagged and listed after.</p>'
        f'<ul class="mentions">{"".join(items)}</ul></section>'
    )


def _timeline_context(log_sorted_asc):
    """Small contextual readout above the chart: where today sits in the series."""
    if not log_sorted_asc or len(log_sorted_asc) < 2:
        return ""

    today = log_sorted_asc[-1]
    history = log_sorted_asc[:-1]  # everything except today
    today_pct = today.get("percentage", 0) or 0
    history_pcts = [r.get("percentage", 0) or 0 for r in history]
    n_hist = len(history_pcts)

    avg = sum(history_pcts) / n_hist
    hi = max(history_pcts)
    lo = min(history_pcts)
    hi_date = history[history_pcts.index(hi)].get("date", "")
    lo_date = history[history_pcts.index(lo)].get("date", "")

    # Rank today against ALL days (today included). 1 = highest.
    all_pcts_sorted = sorted(
        [r.get("percentage", 0) or 0 for r in log_sorted_asc], reverse=True
    )
    rank = all_pcts_sorted.index(today_pct) + 1
    n_all = len(all_pcts_sorted)

    yesterday = history[-1]
    y_pct = yesterday.get("percentage", 0) or 0
    delta_y = today_pct - y_pct
    delta_avg = today_pct - avg

    def _arrow(d):
        if d > 0.05:
            return f"\u25b2 +{d:.1f}pt"
        if d < -0.05:
            return f"\u25bc {d:.1f}pt"
        return "\u25cf flat"

    def _md(iso):
        return iso[5:] if len(iso) >= 10 else iso

    bf_note = (
        " <small class=\"ctx-note\">(some historical days are GDELT-derived "
        "and use a different corpus, see methodology)</small>"
        if any(r.get("backfilled") for r in history) else ""
    )

    return f"""
<div class="timeline-context">
  <div class="ctx-row">
    <div class="ctx-cell">
      <div class="ctx-label">Today</div>
      <div class="ctx-value"><strong>{today_pct}%</strong></div>
    </div>
    <div class="ctx-cell">
      <div class="ctx-label">vs. yesterday ({_md(yesterday.get("date",""))})</div>
      <div class="ctx-value">{_arrow(delta_y)}</div>
    </div>
    <div class="ctx-cell">
      <div class="ctx-label">vs. {n_hist}-day average ({avg:.1f}%)</div>
      <div class="ctx-value">{_arrow(delta_avg)}</div>
    </div>
    <div class="ctx-cell">
      <div class="ctx-label">Rank in the series</div>
      <div class="ctx-value"><strong>#{rank}</strong> of {n_all} days</div>
    </div>
    <div class="ctx-cell ctx-range">
      <div class="ctx-label">Range over {n_hist} prior days</div>
      <div class="ctx-value">
        low <strong>{lo}%</strong> ({_md(lo_date)})
        \u00b7 high <strong>{hi}%</strong> ({_md(hi_date)})
      </div>
    </div>
  </div>
  <p class="ctx-foot">Today's bar is outlined in the chart below.{bf_note}</p>
</div>
"""


def _timeline(log_sorted_asc):
    if not log_sorted_asc:
        return ""

    # Chart renders at most the last 90 days, so a long archive doesn't
    # squash the bars beyond readability.
    log_sorted_asc = log_sorted_asc[-90:]

    W, H = 800, 260
    PAD_L, PAD_R, PAD_T, PAD_B = 44, 12, 16, 32
    chart_w = W - PAD_L - PAD_R
    chart_h = H - PAD_T - PAD_B

    max_pct = max((r.get("percentage", 0) for r in log_sorted_asc), default=0)
    # Floor at 5% so the Flooding band (>= 4% share) stays visible on a
    # string of quiet days; headroom above the highest bar so a peak day
    # isn't flush with the top edge.
    y_max = max(5.0, max_pct * 1.25)

    def y(p):
        return PAD_T + chart_h * (1 - p / y_max)

    n = len(log_sorted_asc)
    slot_w = chart_w / max(n, 1)
    bar_w = slot_w * 0.66

    # Background zone bands (only the part within the visible y range).
    band_rects = []
    for lo, hi, key, name in ZONES:
        if lo >= y_max:
            continue
        hi_clip = min(hi, y_max)
        y_top = y(hi_clip)
        y_bot = y(lo)
        band_rects.append(
            f'<rect x="{PAD_L}" y="{y_top:.1f}" width="{chart_w}" '
            f'height="{(y_bot - y_top):.1f}" fill="{ZONE_COLORS[key]}" opacity="0.10"/>'
        )

    # Threshold lines + labels on the y axis. Ticks sit on the composite
    # classifier's share floors so the chart reads as "which zone's share
    # floor did today clear", not "which percent bucket fell the bar into".
    grid_lines = []
    y_ticks = [0.0] + [lo for lo, _, _, _ in ZONES if 0 < lo <= y_max]
    for t in y_ticks:
        yp = y(t)
        grid_lines.append(
            f'<line x1="{PAD_L}" x2="{W - PAD_R}" y1="{yp:.1f}" y2="{yp:.1f}" '
            f'stroke="#cfc8b8" stroke-dasharray="2 4" stroke-width="1"/>'
        )
        label = f"{t:g}%"
        grid_lines.append(
            f'<text x="{PAD_L - 8}" y="{yp + 4:.1f}" text-anchor="end" '
            f'font-size="11" fill="#8a8170" font-family="Inter, sans-serif">{label}</text>'
        )

    # Bars per day.
    bars = []
    annotations = []
    weekend_shades = []
    x_labels = []
    today = log_sorted_asc[-1].get("date") if log_sorted_asc else None

    # Sparse x-axis labels: first, last, and a few in between.
    if n <= 12:
        label_indices = set(range(n))
    else:
        step = max(1, n // 6)
        label_indices = set(range(0, n, step)) | {n - 1}

    for i, r in enumerate(log_sorted_asc):
        pct = r.get("percentage", 0)
        date_str = r.get("date", "")
        x_center = PAD_L + slot_w * (i + 0.5)
        x = x_center - bar_w / 2
        bar_top = y(pct)
        bar_h = (PAD_T + chart_h) - bar_top
        zone = r.get("zone") or _zone_for(pct)
        if zone == "flooded":
            zone = "soaked"
        color = ZONE_COLORS.get(zone, ZONE_COLORS["dry"])
        is_today = (date_str == today)
        is_backfilled = bool(r.get("backfilled"))
        opacity = "1" if is_today else ("0.55" if is_backfilled else "0.85")
        stroke = ' stroke="#0a1929" stroke-width="2"' if is_today else ""
        source_note = " · GDELT" if is_backfilled else ""

        # Weekend column shading (Sa = 5, Su = 6).
        try:
            from datetime import date as _date
            _dow = _date.fromisoformat(date_str).weekday()
            if _dow >= 5:
                slot_x = PAD_L + slot_w * i
                weekend_shades.append(
                    f'<rect x="{slot_x:.1f}" y="{PAD_T}" '
                    f'width="{slot_w:.1f}" height="{chart_h}" '
                    f'fill="#0a1929" opacity="0.05"/>'
                )
        except (ValueError, TypeError):
            pass

        note = r.get("note", "")
        note_suffix = f" — {html.escape(note)}" if note else ""
        bars.append(
            f'<rect x="{x:.1f}" y="{bar_top:.1f}" width="{bar_w:.1f}" '
            f'height="{max(bar_h, 2):.1f}" rx="2" fill="{color}" '
            f'opacity="{opacity}"{stroke}>'
            f'<title>{html.escape(date_str)}: {pct}% '
            f'({r.get("trump_articles", 0)}/{r.get("total_articles", 0)}){source_note}{note_suffix}</title>'
            f'</rect>'
        )
        if note:
            dot_y = bar_top - 10
            annotations.append(
                f'<g>'
                f'<circle cx="{x_center:.1f}" cy="{dot_y:.1f}" r="5" '
                f'fill="#0a1929" opacity="0.75"/>'
                f'<text x="{x_center:.1f}" y="{dot_y + 4:.1f}" text-anchor="middle" '
                f'font-size="8" fill="white" font-family="Inter, sans-serif" '
                f'font-weight="bold">!</text>'
                f'<title>{html.escape(note)}</title>'
                f'</g>'
            )
        if i in label_indices:
            # Show DD/MM (European format).
            short = (date_str[8:10] + "/" + date_str[5:7]) if len(date_str) >= 10 else date_str
            x_labels.append(
                f'<text x="{x_center:.1f}" y="{H - 10}" text-anchor="middle" '
                f'font-size="11" fill="#8a8170" font-family="Inter, sans-serif">'
                f'{html.escape(short)}</text>'
            )

    def _fmt_band(lo, hi):
        if hi >= 100:
            return f"\u2265 {lo:g}%"
        return f"{lo:g}\u2013{hi:g}%"

    weekend_legend = (
        '<span class="legend-item">'
        '<span class="legend-swatch legend-swatch--weekend"></span>'
        'Weekend</span>'
    )
    legend = " ".join(
        f'<span class="legend-item"><span class="legend-swatch" '
        f'style="background:{ZONE_COLORS[key]}"></span>'
        f'{name} <small>{_fmt_band(lo, hi)}</small></span>'
        for lo, hi, key, name in ZONES
    ) + " " + weekend_legend

    annotated_days = [
        r for r in log_sorted_asc if r.get("note")
    ]
    annotation_html = ""
    if annotated_days:
        items = []
        for r in annotated_days:
            d = r.get("date", "")
            short = (d[8:10] + "/" + d[5:7]) if len(d) >= 10 else d
            items.append(
                f'<li><strong>{short}</strong> — {html.escape(r["note"])}</li>'
            )
        annotation_html = f'<ul class="annotation-list">{"".join(items)}</ul>'

    context_block = _timeline_context(log_sorted_asc)

    return f"""
<section class="block">
  <h2>Timeline</h2>
  {context_block}
  <div class="chart-wrap">
    <svg class="chart" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet">
      {''.join(band_rects)}
      {''.join(weekend_shades)}
      {''.join(grid_lines)}
      {''.join(bars)}
      {''.join(annotations)}
      {''.join(x_labels)}
    </svg>
  </div>
  <div class="legend">{legend}</div>
  <p class="legend-note">Bar colour reflects the assessed zone (percentage + rank + dominance + breadth). Background bands show the percentage thresholds only.</p>
  {annotation_html}
</section>
"""


def _history_table(log_sorted_desc):
    if not log_sorted_desc:
        return ""

    def _row(r):
        pct = r.get("percentage", 0)
        bar_w = max(1, int(pct * 2.5))
        color = _zone_color(pct)
        date_cell = html.escape(r["date"])
        if r.get("backfilled"):
            date_cell += ' <span class="backfilled" title="Reconstructed from GDELT (different corpus, see methodology)">~</span>'
        return (
            "<tr>"
            f"<td>{date_cell}</td>"
            f"<td class='label-cell'>{html.escape(r.get('label',''))}</td>"
            f"<td class='num'>{r.get('trump_articles',0)}/{r.get('total_articles',0)}</td>"
            f"<td class='num'>{pct}%"
            f"<span class='inline-bar' style='width:{bar_w}px;background:{color}'></span></td>"
            "</tr>"
        )

    VISIBLE = 7
    first = log_sorted_desc[:VISIBLE]
    rest = log_sorted_desc[VISIBLE:]
    first_rows = "".join(_row(r) for r in first)

    table_head = "<thead><tr><th>Date</th><th>Label</th><th>Matches</th><th>Share</th></tr></thead>"

    if not rest:
        body = f"<table class=\"log-table\">{table_head}<tbody>{first_rows}</tbody></table>"
    else:
        rest_rows = "".join(_row(r) for r in rest)
        body = (
            f"<table class=\"log-table\">{table_head}<tbody>{first_rows}</tbody></table>"
            f"<details class=\"history-more\">"
            f"<summary>Show full history ({len(rest)} earlier {'day' if len(rest)==1 else 'days'})</summary>"
            f"<table class=\"log-table\">{table_head}<tbody>{rest_rows}</tbody></table>"
            f"</details>"
        )

    return f"""
<section class="block">
  <h2>Daily log</h2>
  {body}
</section>
"""


def _methodology(latest):
    from assessor import THRESHOLDS_VERSION as thresholds_version
    zone_cards = _zone_definitions_block(latest)
    core_total = latest.get("total_articles", 0)
    core_trump = latest.get("trump_articles", 0)
    core_pct = latest.get("percentage", 0)
    wide_total = latest.get("wide_total_articles")
    wide_trump = latest.get("wide_trump_articles")
    wide_pct = latest.get("wide_percentage")
    rank = latest.get("rank")
    n_people = latest.get("n_people")
    theme_rank = latest.get("theme_rank")
    n_themes = latest.get("n_themes")
    dominance = latest.get("dominance")
    breadth = latest.get("breadth")
    deviation = latest.get("deviation")
    smoothed_pct = latest.get("smoothed_pct")
    core_outlets_total = latest.get("core_outlets_total")
    core_outlets_active = latest.get("core_outlets_active")
    cross_outlet_dup_rate = latest.get("cross_outlet_dup_rate")
    cross_outlet_dup_groups = latest.get("cross_outlet_dup_groups")
    cross_outlet_dup_headlines = latest.get("cross_outlet_dup_headlines")

    wide_p = ""
    if wide_total is not None and wide_pct is not None:
        if wide_pct != core_pct:
            delta = round(wide_pct - core_pct, 1)
            sign = "+" if delta > 0 else ""
            compare_line = (
                f"Including every feed we fetch \u2014 Brussels-local "
                f"(BX1, Bruzz), sport-only (Sporza), and the Google News "
                f"aggregators that repackage outlets we already pull directly "
                f"\u2014 the full <strong>wide</strong> corpus is "
                f"<strong>{wide_total} headlines</strong> with "
                f"<strong>{wide_trump} by-name Trump matches = {wide_pct}%</strong> "
                f"({sign}{delta}pt vs. core). "
                f"The cross-check exists so we can spot a day where the two "
                f"tiers diverge sharply, which usually signals an aggregator "
                f"artefact rather than a real shift."
            )
        else:
            compare_line = (
                f"Today the wide corpus ({wide_total} headlines, "
                f"{wide_trump} by-name matches) lands on the same "
                f"<strong>{wide_pct}%</strong> as the core tier, so the "
                f"tier choice doesn\u2019t change the read."
            )
        if smoothed_pct is not None:
            compare_line += (
                f" The 7-day rolling average of the core share is "
                f"<strong>{smoothed_pct}%</strong>."
            )
        wide_p = f"<p>{compare_line}</p>"
    # Signal displays used inline inside the methodology signal-by-signal
    # breakdown. Each falls back to an em-dash when the value is missing.
    dom_display = (f"{dominance}\u00d7" if dominance is not None else "\u2014")
    breadth_display = (
        f"{int(round(breadth * 100))}% of core outlets ran a Trump story"
        if breadth is not None else "\u2014"
    )
    # Count days with expanded data for the "baseline building" progress display.
    expanded_days = sum(
        1 for r in _load_log() if r.get("core_percentage_expanded") is not None
    )
    if deviation is not None:
        deviation_display = f"{deviation}\u00d7 the 14-day median"
    elif expanded_days < 7:
        deviation_display = (
            f"\u2014 (baseline building: "
            f"{expanded_days} of 7 days recorded)"
        )
    else:
        deviation_display = (
            f"\u2014 (median was 0 over the last {min(expanded_days, 14)} days)"
        )
    smooth_inline = (
        f"The 7-day rolling average of the core share is <strong>{smoothed_pct}%</strong>."
        if smoothed_pct is not None else
        "The rolling baseline needs a few more runs before it settles."
    )

    # Weekend note: lower total volume on Sa/Su depresses share and breadth
    # independently of Trump's actual prominence. Flag this transparently.
    weekend_note = ""
    try:
        from datetime import date as _date
        _latest_date = _date.fromisoformat(latest.get("date", ""))
        if _latest_date.weekday() >= 5:          # 5 = Sat, 6 = Sun
            day_name = "Saturday" if _latest_date.weekday() == 5 else "Sunday"
            weekend_note = (
                f'<p class="corpus-diag"><strong>Weekend ({day_name}).</strong> '
                f"Belgian news output is substantially lower on weekends — "
                f"fewer articles in the denominator means share and breadth "
                f"figures are not directly comparable to weekday readings. "
                f"A low zone score today may reflect reduced total volume "
                f"rather than reduced Trump prominence.</p>"
            )
    except (ValueError, TypeError):
        pass

    # Denominator-control diagnostics. These don't change the zone, but they
    # expose two ways the denominator can move independently of Trump
    # coverage: (1) fewer outlets publishing today, (2) more of today's
    # kept headlines being the same wire story running in multiple outlets.
    diag_parts = []
    if core_outlets_active is not None and core_outlets_total:
        diag_parts.append(
            f"<strong>{core_outlets_active} of {core_outlets_total}</strong> "
            f"core outlets active (\u2265 5 kept headlines)"
        )
    if cross_outlet_dup_rate is not None and cross_outlet_dup_groups is not None:
        diag_parts.append(
            f"<strong>{cross_outlet_dup_rate}%</strong> of the kept core "
            f"corpus ({cross_outlet_dup_headlines} headlines across "
            f"{cross_outlet_dup_groups} wire-copy groups) runs verbatim in "
            f"\u2265 2 outlets"
        )
    corpus_diag_p = (
        f"<p class=\"corpus-diag\">Corpus diagnostics: "
        + "; ".join(diag_parts)
        + ". These don\u2019t change the zone; they make denominator drift "
        + "visible. A shrinking outlet count or a spike in wire-copy rate "
        + "can move share and breadth independently of any real change in "
        + "Trump coverage.</p>"
    ) if diag_parts else ""
    theme_txt = ""

    # Source breakdown table, embedded inside the methodology <details>.
    sources = latest.get("sources", {})
    if sources:
        src_rows = []
        for key, payload in sources.items():
            src_rows.append(
                "<tr>"
                f"<td>{html.escape(SOURCE_LABELS.get(key, key))}</td>"
                f"<td class='num'>{payload.get('fetched', 0)}</td>"
                f"<td class='num'>{payload.get('today', 0)}</td>"
                "</tr>"
            )
        sources_block = (
            "<h3>Source breakdown</h3>"
            "<p>Per-feed counts for today\u2019s run. "
            "<em>Fetched</em> is the raw feed size; <em>From today</em> is "
            "items whose <code>pubDate</code> falls on today\u2019s Belgian "
            "local date.</p>"
            "<table>"
            "<thead><tr><th>Source</th><th>Fetched</th><th>From today</th></tr></thead>"
            f"<tbody>{''.join(src_rows)}</tbody>"
            "</table>"
        )
    else:
        sources_block = ""

    return f"""
<section class="block methodology">
  <h2>Methodology</h2>
  <details>
    <summary>How the zone is decided, where the data comes from, and what to be skeptical about.</summary>
    <div class="meth-body">

      <h3>Daily collection</h3>
      <p>Three times a day &mdash; 06:00, 12:00 and 18:00 UTC, which is
      08:00 / 14:00 / 20:00 Belgian local in summer (CEST) and
      07:00 / 13:00 / 19:00 in winter (CET) &mdash;
      a script fetches headlines from 33 Belgian RSS feeds:
      Google News BE (Dutch &amp; French general), 8 Google News BE topic feeds
      (politics, world, business, tech, sport in NL; politics, world, business in FR),
      and 23 outlet feeds spanning VRT NWS, HLN, De Morgen,
      Het Nieuwsblad, HBVL, Knack, Sporza, Bruzz on the Dutch side,
      plus RTBF, La Libre, L'Echo, DH, 7sur7, BX1 directly, and De Standaard,
      De Tijd, Le Soir, Sudinfo, L'Avenir, RTL, Trends and Trends-Tendances
      through Google News&rsquo; <code>site:</code> filter or
      <code>cloudscraper</code> (outlets whose direct RSS feeds are
      Cloudflare-gated; De Standaard uses cloudscraper to preserve full
      paywall-headline coverage).
      Articles whose <code>pubDate</code> is today (Belgian local date)
      are kept; URL duplicates are collapsed globally, and near-identical
      titles inside a single outlet&rsquo;s own feed are collapsed too
      (full rules under &ldquo;Dedup policy&rdquo; in the caveats).</p>

      <h3>Core vs. wide tier</h3>
      <p>Not every feed is equal. Brussels-only outlets (BX1, Bruzz), sport-only
      outlets (Sporza), and the Google News aggregator feeds (which repackage
      content we already pull directly) structurally dilute the denominator with
      stories that are local, single-subject, or duplicated. To avoid that skew,
      the headline number on this page uses a <strong>core</strong> tier:
      national and regional-generalist outlets only &mdash; VRT, RTBF,
      De Standaard, De Morgen, HLN, Het Nieuwsblad, HBVL, Knack, La Libre,
      L'Echo, DHnet, 7sur7, plus De Tijd, Le Soir, Sudinfo, L'Avenir, RTL,
      Trends and Trends-Tendances (reached via Google News&rsquo;
      <code>site:</code> filter or cloudscraper because their direct RSS is
      Cloudflare-gated). GVA is fetched but kept in the wide tier only, as
      its national content largely overlaps with Het Nieuwsblad (same group).
      The full <strong>wide</strong> corpus is still
      computed and stored in <code>data/log.json</code> as a cross-check.
      Today\u2019s core corpus: <strong>{core_total} headlines</strong>,
      <strong>{core_trump} by-name Trump matches = {core_pct}%</strong>
      (this is the share the zone uses; see the &ldquo;Trump match&rdquo;
      section below for how indirect references are handled separately).</p>
      {weekend_note}
      {corpus_diag_p}
      {wide_p}

      <h3>Trump match</h3>
      <p>A headline is a Trump headline if its title matches the regex
      <code>\\btrump\\b</code> (whole word, case-insensitive). All four
      zone signals (share, breadth, dominance, rank) run on this single
      name-only definition, so Trump is measured on the same yardstick
      as the other sixteen named figures in the comparator list.
      Titles only; no body text, no fuzzy matching.</p>
      <p>As a secondary readout we also count headlines that refer to
      Trump indirectly, by role or location rather than by name:
      <code>white house</code> / <code>witte huis</code> /
      <code>maison blanche</code>, <code>oval office</code> /
      <code>bureau ovale</code>, and
      <code>US president</code> / <code>Amerikaans(e) president</code> /
      <code>pr\u00e9sident(e) am\u00e9ricain(e)</code> /
      <code>pr\u00e9sident(e) des \u00c9tats-Unis</code> /
      <code>president van de VS</code>. This count is reported as
      &ldquo;indirect references&rdquo; in the daily record and does
      <em>not</em> drive the zone; it only flags days when Belgian
      quality press is writing about the administration without naming
      Trump directly.</p>

      <h3>Comparators</h3>
      <p>The same headlines are scanned for seventeen named people in
      total. The set is split 7 international / 10 Belgian:</p>
      <ul class="meth-rules">
        <li><strong>International (7, including Trump).</strong> Trump,
        Putin, Macron, Netanyahu, Zelensky, Rutte (NATO Secretary
        General), Von der Leyen (EU Commission President). Heads of
        state, government, or major international institutions whose
        actions recurringly drive Belgian front-page news. Trump sits
        inside this group for rank and dominance; he is measured by the
        same name-only regex as the other six.</li>
        <li><strong>Belgian (10).</strong> De Wever, Bouchez, Magnette,
        Pr&eacute;vot, Rousseau, Francken, Crevits, Jambon, Van
        Peteghem, Verlinden. Sitting federal PM, party presidents of the
        main federal-coalition and opposition parties, and ministers who
        are recurrently named in Belgian headlines.</li>
      </ul>
      <p><strong>Admission rule.</strong> The list is reviewed manually
      each quarter. A figure is in the list if they (a) hold a current
      senior political office in Belgium (federal PM, federal minister,
      major party president) or (b) lead a country or major
      international institution whose actions make recurring Belgian
      front-page news. Removed in the most recent review: Orb&aacute;n,
      Meloni and Musk (intermittent day-to-day Belgian salience); De
      Croo (left government February 2025). Added: Rutte, Von der
      Leyen, Jambon. Once the live archive is 90+ days, this editorial
      rule can be replaced by &ldquo;anyone with &ge; N name mentions in
      the trailing 90-day core corpus&rdquo;, which would make the list
      self-maintaining.</p>
      <p>Fourteen broad subject themes (war, crime, EU politics, Belgian
      government, etc.) are still counted on every run and stored in
      <code>data/log.json</code> as background context, but they are no
      longer shown on the page and no longer compared to Trump. Mixing
      a single person with aggregate themes is a category error: themes
      bundle dozens of stories and a person almost never out-ranks an
      aggregate, which produced visually dramatic but structurally
      meaningless &ldquo;Trump beats Sports&rdquo; lines.</p>

      <h3>Zone assessment</h3>
      <p>No single number can honestly say &ldquo;Trump is flooding Belgian
      news today&rdquo;. The zone combines four signals, each answering a
      different question. Every zone above Dry requires several of them to
      clear a floor simultaneously &mdash; a single-signal spike is never
      enough.</p>

      <h4 class="signal-h">1. Share &mdash; &ldquo;How much of the news is about Trump?&rdquo;</h4>
      <p>The percentage of today&rsquo;s Belgian core-tier headlines
      that name Trump. Computed as
      <code>Trump-by-name headlines &divide; total core headlines &times; 100</code>.</p>
      <p class="signal-today">Today: <strong>{core_trump}/{core_total} = {core_pct}%</strong>.
      A low number means Trump is not prominent in the news today,
      regardless of what other signals say.</p>

      <h4 class="signal-h">2. Dominance &mdash; &ldquo;Is he THE figure of the day?&rdquo;</h4>
      <p>Trump&rsquo;s name-only mentions divided by the sum of mentions
      of the other sixteen named figures we track (6 international + 10
      Belgian; see the Comparators list). A value above 1.0&times;
      means Trump alone out-mentions the other sixteen
      <em>combined</em>.</p>
      <p class="signal-today">Today: <strong>{dom_display}</strong>. This
      catches the &ldquo;slow domestic day&rdquo; case where Trump scoops
      up all named-figure attention even when coverage volume is modest.</p>

      <h4 class="signal-h">3. Breadth &mdash; &ldquo;Is it everywhere, or one paper?&rdquo;</h4>
      <p>The fraction of core outlets that published at least one
      Trump-by-name headline today. Only outlets with &ge; 5 post-dedup
      headlines count toward the denominator so a near-empty feed
      doesn&rsquo;t skew the ratio.</p>
      <p class="signal-today">Today: <strong>{breadth_display}</strong>.
      A high dominance combined with low breadth means one outlet is
      obsessing; a high breadth means Belgian newsrooms collectively
      decided Trump deserves a spot today.</p>

      <h4 class="signal-h">4. Rank &mdash; &ldquo;Is he on top at all?&rdquo;</h4>
      <p>Trump&rsquo;s position among the seventeen named figures, by
      name-only mention count (the same yardstick used for share,
      dominance and breadth). Acts as a veto: higher zones require
      Trump to be #1 or #2. Ties favour Trump &mdash; if Trump and
      Macron both hit 5 mentions, Trump is called #1, not #2. If
      he&rsquo;s #5 on a day everyone is talking about Macron, no zone
      upgrade follows.</p>
      <p class="signal-today">Today: rank <strong>#{rank}</strong> of
      {n_people}.{theme_txt}</p>

      <h4 class="signal-h">Deviation (annotation only)</h4>
      <p>Today&rsquo;s name-only core share divided by the 14-day
      median of the same series. <strong>This is not a zone gate.</strong>
      It is reported next to the zone so a reader can see whether today
      is unusual for Belgium&rsquo;s own baseline, but it does not
      decide the classification: an earlier version included deviation
      as a gate on Flooding and it never actually filtered anything,
      because any day that cleared the other four Flooding floors
      always cleared the deviation floor as well. Requires at least 7
      prior days of data, which the archive builds up gradually.</p>
      <p class="signal-today">Today: <strong>{deviation_display}</strong>.
      {smooth_inline}</p>

      <h4 class="signal-h">Today against each zone</h4>
      <p>Each zone has a set of gates its day has to clear simultaneously.
      The cards below read top-down from most extreme to least; the first
      one whose gates all show a check mark is today&rsquo;s zone. A
      hollow circle means the gate is not used for that zone. Dry is the
      fall-through when nothing above it clears.</p>
      <div class="zone-cards">
        {zone_cards}
      </div>
      <p>Thresholds in use today: version
      <code>{thresholds_version}</code>. The initial version
      (<code>v0-eyeballed</code>) uses absolute floors picked by eye,
      not calibrated against any distribution. The only defence for
      them is that a day clearing several at once is, empirically, a
      day when Trump visibly dominates Belgian headlines. After 30+
      days of live name-only history these absolutes get replaced by
      percentiles of Trump&rsquo;s own distribution (&ldquo;Flooding
      = top 5&percnt; day, Soaked = top 15&percnt;, ...&rdquo;) via
      <code>calibrate.py</code>, which is the only truly
      self-calibrated version. Until that runs, treat the zone names
      as ordinal labels, not statistical claims.</p>

      <h3>Caveats &amp; limits</h3>
      <ul class="meth-rules">
        <li><strong>Title-only matching, name-only for the zone.</strong>
        Titles are scanned, not article bodies. Only the literal name
        <em>trump</em> drives the zone, so a day of coverage that
        reaches for &ldquo;the White House&rdquo;, &ldquo;the
        administration&rdquo;, &ldquo;Washington&rdquo; or
        &ldquo;POTUS&rdquo; without saying his name reads as
        Dry-leaning even if the expanded detector catches some of it.
        That tradeoff is deliberate: it keeps Trump on the same
        yardstick as the other sixteen figures. The expanded count is
        published next to the headline number so you can see, on any
        given day, how much coverage an indirect-only readout would
        have added.</li>
        <li><strong>Trump-the-family.</strong> The regex also matches
        &ldquo;Trump Jr.&rdquo;, &ldquo;Eric Trump&rdquo;, &ldquo;Trump
        Tower&rdquo;. Usually &le;2% noise but it\u2019s there.</li>
        <li><strong>Time-of-day sampling &amp; peak-of-day rule.</strong>
        Fetches run three times a day at fixed UTC slots
        (06:00 / 12:00 / 18:00), which shifts by an hour between CEST
        and CET. RSS feeds only expose the latest N items, so an
        afternoon fetch may show fewer Trump headlines than the morning
        one because earlier pieces have scrolled off. To avoid
        understating a Trump-heavy day, we keep the <em>peak</em>
        name-only share for each day: if a later run sees a lower
        name-only share than the one already stored, we keep the
        earlier record and only update the &ldquo;last checked&rdquo;
        timestamp. Later runs still replace the record when they see a
        <em>higher</em> name-only share, so a late-breaking Trump surge
        is captured.</li>
        <li><strong>Dedup policy.</strong> URL duplicates (same article
        reached via two feeds, e.g. Google News republishing an HLN link)
        collapse to one globally. Title duplicates only collapse
        <em>within the same outlet</em> &mdash; a normalised title
        (lower-case, accent-stripped, editorial prefixes like
        &ldquo;VIDEO.&rdquo; removed, first 80 chars compared) that
        repeats inside one publisher&rsquo;s feed becomes one. Titles
        shorter than 12 characters after normalisation are not deduped
        (generic short strings like &ldquo;update&rdquo; can collide on
        unrelated stories). But if HLN, Nieuwsblad and GVA all run the
        same Reuters headline, those are three editorial decisions and
        all three count. That is what &ldquo;breadth&rdquo; measures:
        publishing choices, not unique authored stories.</li>
        <li><strong>Aggregator overlap.</strong> The Google News feeds (only
        used in the wide tier, not core) republish outlets we already pull
        directly; URLs differ from the direct ones so some duplication leaks
        in on the wide number.</li>
        <li><strong>Belgian press covers world.</strong> The denominator is
        heavy with international news that Belgian outlets choose to publish.
        This measures &ldquo;share of the news Belgians read&rdquo; &mdash; not
        &ldquo;what Belgian society is discussing internally&rdquo;.</li>
        <li><strong>Comparator list maintenance.</strong> The seventeen-
        person comparator set is reviewed editorially each quarter under
        the admission rule above. Between reviews, a newly-prominent
        Belgian figure who is <em>not</em> on the list inflates
        Trump\u2019s rank until they are added. Once the live archive
        reaches 90+ days, the list can be replaced by a data-driven rule
        (&ldquo;anyone with &ge; N name mentions in the trailing 90
        days&rdquo;) and the manual review falls away.</li>
      </ul>

      {sources_block}

    </div>
  </details>
</section>
"""


def _sources_panel(latest):
    src = latest.get("sources", {})
    if not src:
        return ""
    rows = []
    for key, payload in src.items():
        rows.append(
            "<tr>"
            f"<td>{html.escape(SOURCE_LABELS.get(key, key))}</td>"
            f"<td class='num'>{payload.get('fetched', 0)}</td>"
            f"<td class='num'>{payload.get('today', 0)}</td>"
            "</tr>"
        )
    return f"""
<section class="block">
  <h2>Source breakdown</h2>
  <table>
    <thead><tr><th>Source</th><th>Fetched</th><th>From today</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</section>
"""


BASE_URL = "https://andriesfluit.be/trumpflood"


def _og_meta(latest):
    date_str = latest.get("date", "")
    label    = latest.get("label", "Is Trump flooding the zone?")
    pct      = latest.get("percentage", 0)
    img_url  = f"{BASE_URL}/{date_str}.png"
    desc     = f"{label} · {pct}% of Belgian headlines name Trump today."
    title    = f"Is Trump flooding the zone? — {date_str}"
    return (
        f'<meta property="og:type"        content="website">\n'
        f'<meta property="og:url"         content="{BASE_URL}/">\n'
        f'<meta property="og:title"       content="{html.escape(title)}">\n'
        f'<meta property="og:description" content="{html.escape(desc)}">\n'
        f'<meta property="og:image"       content="{img_url}">\n'
        f'<meta property="og:image:width" content="1200">\n'
        f'<meta property="og:image:height" content="628">\n'
        f'<meta name="twitter:card"       content="summary_large_image">\n'
        f'<meta name="twitter:image"      content="{img_url}">\n'
        f'<meta name="twitter:title"      content="{html.escape(title)}">\n'
        f'<meta name="twitter:description" content="{html.escape(desc)}">'
    )


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Is Trump flooding the zone?</title>
{og_meta}
<style>
  :root {{
    --ink: #0a1929;
    --paper: #f5f3ee;
    --rule: #d8d3c5;
    --muted: #6b6356;
    --accent: #1A5276;
    color-scheme: light;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{
    margin: 0;
    padding: 0;
    /* Prevent any child from creating horizontal overflow that sidescrolls
       the whole page on mobile. Individual scroll containers (tables in
       methodology, etc.) opt back in via overflow-x:auto. */
    overflow-x: hidden;
    max-width: 100vw;
  }}
  /* Long words (Dutch compounds, URLs in titles) should wrap instead of
     pushing their container wider on narrow screens. */
  h1, h2, h3, h4, p, a, li, td, th {{
    overflow-wrap: break-word;
    word-wrap: break-word;
    word-break: break-word;
  }}
  body {{
    font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    background: var(--paper);
    color: var(--ink);
    -webkit-font-smoothing: antialiased;
    line-height: 1.5;
    /* Safety net: if any nested element (a chart, a wide table, a
       miscalculated flex child) overflows the viewport horizontally,
       don't let the whole page scroll sideways on mobile. Vertical
       scroll is unaffected. */
    overflow-x: hidden;
  }}
  .wrap {{ max-width: 1100px; margin: 0 auto; padding: 56px 32px 96px; }}

  /* Masthead */
  .masthead {{
    border-bottom: 1px solid var(--ink);
    padding-bottom: 14px;
    margin-bottom: 56px;
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 24px;
    flex-wrap: wrap;
  }}
  .brand {{
    font-family: "Playfair Display", "Times New Roman", Georgia, serif;
    font-size: 56px;
    font-weight: 900;
    letter-spacing: -0.02em;
    line-height: 1;
    margin: 4px 0 0;
  }}
  .brand-eyebrow {{
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--muted);
    font-weight: 600;
  }}
  .brand-sub {{
    font-size: 12px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--muted);
  }}

  /* Hero */
  .hero {{
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 56px;
    align-items: center;
    margin-bottom: 72px;
  }}
  @media (max-width: 760px) {{
    .hero {{ grid-template-columns: 1fr; gap: 32px; }}
    /* CSS Grid gives each cell an implicit min-width: auto equal to the
       content's intrinsic size. With a 320px-intrinsic canvas inside
       .portrait-wrap, that pushes the grid column wider than the viewport.
       min-width:0 on the grid children is the standard fix. */
    .hero > * {{ min-width: 0; }}
    .portrait-wrap {{ max-width: 360px; margin: 0 auto; }}
  }}

  /* Phones: tighter margins, smaller display type, scrollable wide tables.
     Targets iPhone SE (320px) through large-phone portrait (520px). */
  @media (max-width: 520px) {{
    .wrap {{ padding: 32px 18px 64px; }}

    .masthead {{
      flex-direction: column;
      align-items: flex-start;
      gap: 6px;
      padding-bottom: 12px;
      margin-bottom: 40px;
    }}
    .brand {{ font-size: 36px; letter-spacing: -0.015em; }}
    .brand-eyebrow {{ font-size: 10px; }}
    .brand-sub {{ font-size: 10px; }}

    /* Hero: portrait + scale must fit inside .wrap content-width (screen
       minus 36px horizontal padding). Critical: grid children need
       min-width:0 to shrink below intrinsic content size, and the
       portrait canvas+image need explicit max-width to actually shrink. */
    .hero {{ gap: 24px; margin-bottom: 48px; }}
    .portrait-wrap {{
      width: 100%;
      max-width: 100%;
      min-width: 0;
      gap: 8px;
    }}
    .portrait {{
      width: auto;
      min-width: 0;
      flex: 1 1 0;
      max-width: none;
    }}
    .portrait img,
    .portrait canvas {{
      max-width: 100%;
    }}
    .scale {{
      width: 88px;
      flex: 0 0 88px;
      min-width: 0;
    }}
    .band {{ overflow: hidden; padding: 6px 8px; }}
    .band-name {{ font-size: 10px; letter-spacing: 0.04em; }}

    /* Readout: large type scales down more aggressively than at 760px.
       "The zone is getting wet" is 23 characters; at 32px it fits on
       a 390px iPhone viewport with 36px of wrap padding. */
    .readout {{ min-width: 0; }}
    .readout-label {{
      font-size: 32px;
      line-height: 1.05;
      margin-bottom: 14px;
    }}
    .pct {{ font-size: 64px; }}
    .pct-symbol {{ font-size: 32px; }}
    .readout-facts {{ font-size: 13px; gap: 4px; }}
    .readout-sep {{ margin: 14px 0; }}

    /* Methodology: big tables need horizontal scroll */
    .zone-thresholds {{ font-size: 12px; }}
    .zone-thresholds th, .zone-thresholds td {{ padding: 6px 6px; }}
    .meth-body {{ overflow-x: auto; }}
    .meth-body h4.signal-h {{ font-size: 16px; }}

    /* Source table also wants to scroll rather than squish */
    table {{ min-width: 0; }}

    /* Comparison bars: keep labels on their own line if tight */
    .comp-label {{ font-size: 13px; }}
    .comp-stat {{ font-size: 13px; }}
    .theme-label {{ font-size: 13px; }}

    /* Block headings */
    .block h2 {{ font-size: 11px; }}

    /* Daily log: hide the "label" column on very narrow phones so the
       date + share stay visible without horizontal scroll. Scoped to
       .log-table so the threshold table (which has "Share" as its 2nd
       column) isn't hit too. */
    .log-table thead th:nth-child(2),
    .log-table tbody td:nth-child(2) {{ display: none; }}

    /* Today's mentions: stack the title above the source label. Default
       (desktop) is a flex row, but 18px title + nowrap source creates
       horizontal overflow on narrow screens. */
    .mentions li {{
      flex-direction: column;
      align-items: flex-start;
      gap: 6px;
      padding: 12px 0;
    }}
    .mentions a {{ font-size: 16px; }}
    .mentions .src {{ font-size: 10px; }}

    /* Compare rows + theme rows: default grid is 130px/1fr/110px which
       eats all the mobile width. Collapse to 2 rows: label full-width
       on top, bar + stat below it. */
    .comp-row,
    .themes-comp .theme-row {{
      grid-template-columns: 1fr auto;
      grid-template-rows: auto auto;
      gap: 4px 12px;
      padding: 6px 0;
    }}
    .comp-label, .theme-label {{
      grid-column: 1 / -1;
      font-size: 13px;
    }}
    .comp-bar-wrap, .theme-bar-wrap {{
      grid-column: 1 / 2;
    }}
    .comp-stat, .theme-stat {{
      grid-column: 2 / 3;
      font-size: 13px;
    }}

  }}

  /* Small phones (iPhone 13 mini at 375, iPhone SE at 320).
     Constraint: at 52px/9px the band-name overflowed because "FLOODING"
     needs ~48px of text width plus padding. Widen the scale to 64px,
     tighten band padding to 6px, drop letter-spacing. That gives roughly
     52px of horizontal runway inside each band, enough for every label
     at 9px including the longest ("FLOODING"). */
  @media (max-width: 380px) {{
    .brand {{ font-size: 30px; }}
    .readout-label {{ font-size: 26px; }}
    .pct {{ font-size: 56px; }}
    .pct-symbol {{ font-size: 28px; }}
    .scale {{ width: 64px; flex: 0 0 64px; }}
    .band {{ padding: 6px 6px; }}
    .band-name {{ font-size: 9px; letter-spacing: 0.02em; }}
  }}

  .portrait-wrap {{
    display: flex;
    align-items: stretch;
    gap: 12px;
  }}
  .portrait {{
    position: relative;
    width: 320px;
    aspect-ratio: 800 / 1013;
    overflow: hidden;
    background: #eee;
    border: 1px solid var(--rule);
  }}
  .portrait img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    filter: grayscale(100%) contrast(1.05);
  }}
  /* Water is painted on a canvas that covers the whole portrait.
     JavaScript reads --water-target and --water-color and animates two
     sine waves with alpha, plus a shimmer and bubbles. */
  .water-canvas {{
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    display: block;
    pointer-events: none;
    z-index: 1;
  }}

  @media (prefers-reduced-motion: reduce) {{
    /* The canvas animation loop also respects this: see the water-canvas
       init script, which falls back to a single static paint. */
  }}
  /* Vertical zone scale next to portrait */
  .scale {{
    position: relative;
    width: 132px;
    border: 1px solid var(--rule);
    background: white;
  }}
  .band {{
    position: absolute;
    left: 0;
    right: 0;
    border-top: 1px solid var(--rule);
    padding: 6px 10px;
    overflow: hidden;
    background: color-mix(in srgb, var(--band-color) 14%, white);
    transition: background 0.3s, color 0.3s;
  }}
  .band:first-child {{ border-top: none; }}
  .band-name {{
    display: block;
    font-size: 11px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--ink);
    font-weight: 700;
    line-height: 1.1;
  }}
  .band-range {{
    display: block;
    font-size: 10px;
    color: var(--muted);
    font-variant-numeric: tabular-nums;
    margin-top: 2px;
  }}
  .band.active {{
    background: var(--band-color);
    color: white;
    box-shadow: 0 0 0 2px var(--ink);
    z-index: 2;
    overflow: hidden;
    position: absolute;
  }}
  .band.active .band-name {{ color: white; position: relative; z-index: 2; }}
  .band.active .band-range {{ color: rgba(255,255,255,0.8); }}
  .band-pct {{
    display: block;
    font-family: "Playfair Display", "Times New Roman", Georgia, serif;
    font-size: 22px;
    font-weight: 800;
    color: white;
    margin-top: 4px;
    line-height: 1;
    font-variant-numeric: tabular-nums;
  }}

  .readout-label {{
    font-family: "Playfair Display", "Times New Roman", Georgia, serif;
    font-size: 80px;
    line-height: 0.95;
    font-weight: 900;
    letter-spacing: -0.025em;
    margin: 0 0 4px;
  }}
  /* Thin horizontal rule between the three readout blocks (label, metric,
     facts). Uses the same --rule color as block separators on the rest
     of the page so the hero reads as one cohesive panel. */
  .readout-sep {{
    border: 0;
    border-top: 1px solid var(--rule);
    margin: 18px 0;
    max-width: 520px;
  }}
  /* Third block: compact fact lines. One per row, tabular numerals so
     numbers line up. Replaces the old upper-case "RANK #1 OF 15 ..."
     badge and the separate white-frame lead paragraph. */
  .readout-facts {{
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 15px;
    color: var(--muted);
    font-variant-numeric: tabular-nums;
    max-width: 520px;
  }}
  .readout-facts .fact strong {{
    color: var(--ink);
    font-weight: 700;
  }}
  .readout-indirect {{
    margin-top: 14px;
    font-size: 13px;
    color: var(--muted);
    font-style: italic;
    max-width: 520px;
  }}
  .readout-indirect strong {{ color: var(--ink); font-style: normal; }}
  .macro-stat {{
    margin-top: 8px;
    font-size: 12px;
    color: var(--muted);
    cursor: help;
  }}
  .macro-stat strong {{
    color: var(--ink);
    font-weight: 700;
    font-size: 13px;
  }}
  .macro-delta {{ color: #aaa; margin-left: 4px; font-size: 11px; }}
  .readout-stat {{
    display: flex;
    align-items: baseline;
    gap: 16px;
    margin-bottom: 12px;
  }}
  .pct {{
    font-size: 96px;
    font-weight: 800;
    line-height: 1;
    color: var(--accent);
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.03em;
  }}
  .pct-symbol {{ font-size: 56px; color: var(--muted); margin-left: 4px; }}
  .readout-sub {{
    font-size: 16px;
    color: var(--muted);
    max-width: 520px;
  }}
  .readout-sub strong {{ color: var(--ink); }}
  .indirect-tag {{
    display: inline-block;
    margin: 0 8px 0 6px;
    padding: 1px 6px;
    font-size: 10px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    border: 1px solid var(--muted);
    border-radius: 2px;
    color: var(--muted);
    vertical-align: middle;
  }}
  .sep {{ margin: 0 8px; }}

  @media (max-width: 760px) {{
    .readout-label {{ font-size: 56px; }}
    .pct {{ font-size: 72px; }}
    .pct-symbol {{ font-size: 40px; }}
  }}

  /* Blocks */
  .block {{ margin-top: 56px; }}
  .block h2 {{
    font-size: 12px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--muted);
    border-bottom: 1px solid var(--rule);
    padding-bottom: 8px;
    margin: 0 0 20px;
    font-weight: 600;
  }}

  .mentions {{ list-style: none; padding: 0; margin: 0; }}
  .mentions li {{
    padding: 16px 0;
    border-bottom: 1px solid var(--rule);
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 24px;
  }}
  .mentions li:last-child {{ border-bottom: none; }}
  .mentions a {{
    color: var(--ink);
    text-decoration: none;
    font-size: 18px;
    line-height: 1.4;
    flex: 1;
  }}
  .mentions a:hover {{ color: var(--accent); text-decoration: underline; }}
  .mentions .src {{
    font-size: 11px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--muted);
    white-space: nowrap;
  }}
  .empty {{ color: var(--muted); font-style: italic; }}

  /* Timeline context block */
  .timeline-context {{
    background: white;
    border: 1px solid var(--rule);
    border-radius: 4px;
    padding: 14px 16px;
    margin-bottom: 12px;
  }}
  .ctx-row {{
    display: grid;
    grid-template-columns: repeat(4, 1fr) 1.4fr;
    gap: 16px;
  }}
  @media (max-width: 720px) {{
    .ctx-row {{ grid-template-columns: repeat(2, 1fr); }}
    .ctx-range {{ grid-column: 1 / -1; }}
  }}
  .ctx-cell {{ display: flex; flex-direction: column; gap: 2px; }}
  .ctx-label {{
    font-size: 11px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }}
  .ctx-value {{
    font-size: 14px;
    font-variant-numeric: tabular-nums;
  }}
  .ctx-value strong {{ font-size: 16px; }}
  .ctx-foot {{
    margin: 10px 0 0;
    font-size: 11px;
    color: var(--muted);
  }}
  .ctx-note {{ display: block; margin-top: 2px; }}

  /* Timeline chart */
  .chart-wrap {{
    background: white;
    border: 1px solid var(--rule);
    border-radius: 4px;
    padding: 16px;
    margin-bottom: 16px;
  }}
  .chart {{ width: 100%; height: auto; display: block; }}
  .legend {{
    display: flex;
    flex-wrap: wrap;
    gap: 14px 22px;
    margin-bottom: 32px;
    font-size: 12px;
    color: var(--muted);
  }}
  .legend-item {{ display: inline-flex; align-items: center; gap: 6px; }}
  .legend-swatch {{
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 2px;
  }}
  .legend small {{ color: #aaa; font-variant-numeric: tabular-nums; }}
  .legend-note {{ font-size: 11px; color: var(--muted); margin: 4px 0 0; }}
  .annotation-list {{
    list-style: none;
    padding: 0;
    margin: 12px 0 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }}
  .annotation-list li {{
    font-size: 12px;
    color: var(--muted);
    padding-left: 18px;
    position: relative;
  }}
  .annotation-list li::before {{
    content: "!";
    position: absolute;
    left: 0;
    width: 14px;
    height: 14px;
    line-height: 14px;
    text-align: center;
    background: #0a1929;
    color: white;
    border-radius: 50%;
    font-size: 9px;
    font-weight: bold;
    top: 1px;
  }}
  .legend-swatch--weekend {{
    background: rgba(10,25,41,0.08);
    border: 1px solid rgba(10,25,41,0.15);
  }}
  .backfilled {{
    color: var(--muted);
    font-size: 11px;
    cursor: help;
    margin-left: 4px;
  }}

  /* Comparison panel */
  .block-intro {{
    color: var(--muted);
    font-size: 13px;
    margin: -8px 0 20px;
    max-width: 700px;
  }}
  .block-intro.small {{ font-size: 12px; margin: -4px 0 14px; }}
  .sub-h {{
    font-family: "Playfair Display", "Times New Roman", Georgia, serif;
    font-size: 20px;
    font-weight: 700;
    margin: 40px 0 4px;
    letter-spacing: -0.005em;
  }}
  .history-more {{ margin-top: 12px; }}
  .history-more > summary {{
    font-size: 12px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--muted);
    cursor: pointer;
    padding: 8px 0;
    list-style: none;
  }}
  .history-more > summary::-webkit-details-marker {{ display: none; }}
  .history-more > summary:hover {{ color: var(--ink); }}
  .history-more[open] > summary::after {{ content: ""; }}
  .history-more > summary::before {{
    content: "+ ";
    color: var(--ink);
  }}
  .history-more[open] > summary::before {{ content: "\u2212 "; }}
  .comparison {{
    display: flex;
    flex-direction: column;
    gap: 10px;
    background: white;
    border: 1px solid var(--rule);
    border-radius: 4px;
    padding: 20px 24px;
  }}
  .comp-row {{
    display: grid;
    grid-template-columns: 130px 1fr 110px;
    align-items: center;
    gap: 16px;
  }}
  .comp-label {{
    font-size: 14px;
    font-weight: 500;
    color: var(--ink);
  }}
  .comp-row.trump .comp-label {{
    font-weight: 800;
    font-size: 15px;
  }}
  .comp-bar-wrap {{
    background: #f0ebdf;
    height: 22px;
    border-radius: 3px;
    overflow: hidden;
    position: relative;
  }}
  .comp-bar {{
    height: 100%;
    border-radius: 3px;
    transition: width 0.7s cubic-bezier(.2,.8,.2,1);
  }}
  .comp-row.trump .comp-bar-wrap {{
    box-shadow: 0 0 0 1px var(--ink);
  }}
  .comp-stat {{
    text-align: right;
    font-variant-numeric: tabular-nums;
    font-size: 14px;
    color: var(--muted);
  }}
  .comp-stat strong {{ color: var(--ink); font-weight: 700; }}
  .comp-share {{ color: #aaa; margin-left: 6px; font-size: 12px; }}

  .vs-others {{
    margin-top: 16px;
    padding-top: 14px;
    border-top: 1px dashed var(--rule);
  }}
  .vs-line {{
    font-size: 16px;
    color: var(--ink);
  }}
  .vs-line strong {{
    font-family: "Playfair Display", serif;
    font-size: 22px;
    font-weight: 800;
    color: var(--accent);
    margin: 0 4px;
  }}
  .vs-vs {{
    font-style: italic;
    color: var(--muted);
    margin: 0 4px;
  }}
  .vs-ratio {{
    font-variant-numeric: tabular-nums;
    color: var(--muted);
    margin-left: 6px;
  }}
  .vs-verdict {{
    margin-top: 4px;
    font-size: 13px;
    color: var(--muted);
    font-style: italic;
  }}

  /* Themes panel: same shape as comparison but with theme rows. */
  .themes-comp .theme-row {{
    display: grid;
    grid-template-columns: 160px 1fr 110px;
    align-items: center;
    gap: 16px;
  }}
  .theme-label {{
    font-size: 14px;
    font-weight: 500;
    color: var(--ink);
  }}
  .theme-row.trump .theme-label {{
    font-weight: 800;
    font-style: italic;
    color: var(--accent);
  }}
  .theme-bar-wrap {{
    background: #efeadd;
    height: 22px;
    border-radius: 3px;
    overflow: hidden;
  }}
  .theme-row.trump .theme-bar-wrap {{
    box-shadow: 0 0 0 1px var(--ink);
  }}
  .theme-bar {{
    height: 100%;
    border-radius: 3px;
    transition: width 0.7s cubic-bezier(.2,.8,.2,1);
  }}
  .theme-stat {{
    text-align: right;
    font-variant-numeric: tabular-nums;
    font-size: 14px;
    color: var(--muted);
  }}
  .theme-stat strong {{ color: var(--ink); font-weight: 700; }}
  .theme-share {{ color: #aaa; margin-left: 6px; font-size: 12px; }}

  /* Methodology */
  .methodology details {{
    background: white;
    border: 1px solid var(--rule);
    border-radius: 4px;
    padding: 0;
  }}
  .methodology summary {{
    cursor: pointer;
    padding: 18px 24px;
    font-size: 14px;
    color: var(--ink);
    list-style: none;
    position: relative;
    user-select: none;
  }}
  .methodology summary::-webkit-details-marker {{ display: none; }}
  .methodology summary::after {{
    content: "+";
    position: absolute;
    right: 24px;
    top: 18px;
    font-size: 20px;
    color: var(--muted);
    line-height: 1;
    transition: transform 0.2s;
  }}
  .methodology details[open] summary::after {{ content: "\u2212"; }}
  .meth-body {{
    padding: 4px 24px 24px;
    border-top: 1px solid var(--rule);
    color: var(--ink);
    font-size: 14px;
    line-height: 1.6;
    max-width: 760px;
  }}
  .meth-body h3 {{
    font-size: 12px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--muted);
    font-weight: 600;
    margin: 24px 0 8px;
  }}
  .meth-body h4.signal-h {{
    font-family: "Playfair Display", "Times New Roman", Georgia, serif;
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -0.005em;
    color: var(--ink);
    text-transform: none;
    margin: 22px 0 6px;
  }}
  .meth-body p.signal-today {{
    color: var(--muted);
    font-size: 13px;
    margin: 4px 0 12px;
  }}
  .meth-body p.signal-today strong {{ color: var(--ink); }}
  .meth-body p {{ margin: 0 0 10px; }}
  .zone-thresholds {{
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0 20px;
    font-variant-numeric: tabular-nums;
    font-size: 13px;
  }}
  .zone-thresholds th,
  .zone-thresholds td {{
    border-bottom: 1px solid var(--rule);
    padding: 8px 10px;
    text-align: left;
  }}
  .zone-thresholds th {{
    font-size: 10px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--muted);
    font-weight: 600;
  }}
  .zone-thresholds td.num, .zone-thresholds th.num {{
    text-align: right;
  }}
  .zone-thresholds tr:last-child td {{ border-bottom: none; }}
  .zone-thresholds td strong {{ font-weight: 700; }}

  /* Per-zone cards showing today's readings against each gate. Replaces
     the old threshold matrix; every reader can see which gates cleared
     for each zone today without mentally cross-referencing a table. */
  .zone-cards {{
    display: grid;
    grid-template-columns: 1fr;
    gap: 10px;
    margin: 12px 0 20px;
  }}
  .zone-card {{
    border: 1px solid var(--rule);
    border-left: 4px solid var(--rule);
    border-radius: 3px;
    padding: 10px 14px;
    background: white;
  }}
  .zone-card-active {{
    border-left-width: 4px;
    border-left-color: var(--ink);
    box-shadow: 0 0 0 1px var(--ink) inset, 0 1px 3px rgba(10, 25, 41, 0.06);
  }}
  .zone-card-cleared:not(.zone-card-active) {{
    border-left-color: #6b9062;
  }}
  .zone-card-head {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 6px;
  }}
  .zone-card-swatch {{
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 2px;
    flex: 0 0 12px;
  }}
  .zone-card-name {{
    font-weight: 700;
    font-size: 14px;
    letter-spacing: 0.02em;
  }}
  .zone-card-badge {{
    font-size: 10px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 2px;
    background: var(--ink);
    color: var(--paper);
  }}
  .zone-card-badge.subtle {{
    background: #eee6d4;
    color: var(--muted);
    font-weight: 600;
  }}
  .zone-gates {{
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px 18px;
    font-size: 13px;
    font-variant-numeric: tabular-nums;
  }}
  @media (max-width: 560px) {{
    .zone-gates {{ grid-template-columns: 1fr; }}
  }}
  .gate {{ display: flex; gap: 8px; align-items: baseline; }}
  .gate-mark {{
    font-family: Menlo, Consolas, monospace;
    font-weight: 700;
    width: 14px;
    text-align: center;
    flex: 0 0 14px;
  }}
  .gate-ok .gate-mark {{ color: #4a7a3e; }}
  .gate-fail .gate-mark {{ color: #a8523c; }}
  .gate-na {{ color: var(--muted); }}
  .gate-na .gate-mark {{ color: var(--rule); }}
  .gate-note {{ color: var(--muted); font-size: 12px; }}
  .zone-card-dry-note {{
    margin: 2px 0 0;
    font-size: 13px;
    color: var(--muted);
  }}

  .meth-body code {{
    background: #f5f0e2;
    padding: 1px 5px;
    border-radius: 2px;
    font-size: 13px;
    font-family: Menlo, Consolas, monospace;
  }}
  .meth-rules {{
    margin: 8px 0 16px;
    padding-left: 20px;
  }}
  .meth-rules li {{ margin-bottom: 4px; }}
  .meth-rules em {{ color: var(--muted); font-style: italic; }}
  .corpus-diag {{
    margin: 4px 0 12px;
    padding: 8px 12px;
    background: var(--card);
    border-left: 3px solid var(--rule);
    font-size: 13px;
    color: var(--muted);
  }}
  .corpus-diag strong {{ color: var(--text); }}

  /* Tables */
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{
    padding: 10px 12px;
    text-align: left;
    border-bottom: 1px solid var(--rule);
    font-size: 14px;
  }}
  th {{
    font-weight: 600;
    color: var(--muted);
    font-size: 11px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }}
  tr:last-child td {{ border-bottom: none; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .inline-bar {{
    display: inline-block;
    height: 6px;
    border-radius: 2px;
    vertical-align: middle;
    margin-left: 10px;
  }}
  .label-cell {{ font-weight: 500; }}

  footer {{
    margin-top: 80px;
    padding-top: 24px;
    border-top: 1px solid var(--rule);
    color: var(--muted);
    font-size: 12px;
    line-height: 1.6;
  }}
  footer a {{ color: var(--accent); }}

  /* Responsive overrides live AT THE END so they win the cascade. Earlier
     in this stylesheet the base .band-name / .scale / .portrait rules
     come AFTER the first set of @media blocks, which silently cancelled
     their mobile sizes. These trailing blocks restate the mobile sizes
     so they actually stick. */
  @media (max-width: 520px) {{
    .scale {{ width: 88px; flex: 0 0 88px; min-width: 0; }}
    .band {{ padding: 6px 8px; overflow: hidden; }}
    .band-name {{ font-size: 10px; letter-spacing: 0.04em; }}
    .portrait {{ width: auto; min-width: 0; flex: 1 1 0; max-width: none; }}
    .portrait img, .portrait canvas {{ max-width: 100%; }}
  }}
  @media (max-width: 380px) {{
    .scale {{ width: 64px; flex: 0 0 64px; }}
    .band {{ padding: 6px 6px; }}
    .band-name {{ font-size: 9px; letter-spacing: 0.02em; }}
  }}
</style>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@800;900&display=swap" rel="stylesheet">
</head>
<body>
<div class="wrap">
  <header class="masthead">
    <div>
      <div class="brand-eyebrow">trumpflood &middot; Belgian news monitor</div>
      <h1 class="brand">Is Trump flooding the zone?</h1>
    </div>
    <div class="brand-sub">{last_run}</div>
  </header>

  {hero}

  {comparison}

  {timeline}

  {mentions}

  {history}

  {methodology}

  <footer>
    Sources: 31 Belgian RSS feeds, measured three times a day (06:00 / 12:00 / 18:00 UTC,
    which is 08:00 / 14:00 / 20:00 Belgian local in summer and 07:00 / 13:00 / 19:00 in winter).
    Core tier (drives the headline number): VRT NWS, RTBF, De Standaard,
    De Morgen, HLN, Het Nieuwsblad, GVA, HBVL, Knack, La Libre, L&rsquo;Echo,
    DHnet, 7sur7, plus De Tijd, Le Soir, Sudinfo, L&rsquo;Avenir and RTL via
    Google News&rsquo; <code>site:</code> filter.
    Headline match: any case-insensitive whole-word occurrence of <em>trump</em>
    in the article title (Dutch, French and English).
    Portrait: official White House photo by Shealah Craighead, public domain.
    See the Methodology section above for the composite zone definitions and
    the full list of caveats.
  </footer>
</div>

<script>
// Water canvas animation: two sine wave layers with alpha, shimmer crest, and
// bubbles. Reads water level and color from the nearest .portrait via
// data-water-target (percent 0-100) and data-water-color (hex).
(function () {{
  const portraits = document.querySelectorAll(".portrait");
  const reduceMotion = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function hexToRgb(h) {{
    h = (h || "").trim().replace(/^#/, "");
    if (h.length === 3) h = h.split("").map(function (c) {{ return c + c; }}).join("");
    return {{
      r: parseInt(h.substr(0, 2), 16) || 0,
      g: parseInt(h.substr(2, 2), 16) || 0,
      b: parseInt(h.substr(4, 2), 16) || 0
    }};
  }}
  function lighten(c, amt) {{
    return {{
      r: Math.min(255, c.r + (255 - c.r) * amt),
      g: Math.min(255, c.g + (255 - c.g) * amt),
      b: Math.min(255, c.b + (255 - c.b) * amt)
    }};
  }}
  function rgba(c, a) {{ return "rgba(" + c.r + "," + c.g + "," + c.b + "," + a + ")"; }}

  portraits.forEach(function (portrait) {{
    const canvas = portrait.querySelector(".water-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    const target  = parseFloat(portrait.getAttribute("data-water-target")) || 0;
    const hex     = portrait.getAttribute("data-water-color") || "#0ea5e9";
    const wcol    = hexToRgb(hex);
    const wcolBk  = lighten(wcol, 0.18);

    let cssW = 0, cssH = 0;
    function resize() {{
      const rect = canvas.getBoundingClientRect();
      cssW = rect.width; cssH = rect.height;
      const dpr = window.devicePixelRatio || 1;
      canvas.width  = Math.max(1, Math.floor(cssW * dpr));
      canvas.height = Math.max(1, Math.floor(cssH * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }}
    resize();
    window.addEventListener("resize", resize);

    // Bubble pool
    const bubbles = [];
    function spawnBubble() {{
      bubbles.push({{
        x: 8 + Math.random() * (cssW - 16),
        y: cssH + 4,
        r: 1 + Math.random() * 3.2,
        vy: 0.35 + Math.random() * 0.9,
        drift: (Math.random() - 0.5) * 0.3,
        alpha: 0.25 + Math.random() * 0.35
      }});
    }}

    function drawWaveFill(top, amp, freq, phase, color) {{
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.moveTo(0, cssH);
      ctx.lineTo(0, top);
      for (let x = 0; x <= cssW; x += 3) {{
        const y = top + Math.sin(x * freq + phase) * amp;
        ctx.lineTo(x, y);
      }}
      ctx.lineTo(cssW, cssH);
      ctx.closePath();
      ctx.fill();
    }}

    function paint(level, time) {{
      ctx.clearRect(0, 0, cssW, cssH);
      const waterTop = cssH * (1 - level);
      const baseAmp  = 1.2 + Math.min(level * 22, 18);

      // Back wave: larger, slower, lighter
      drawWaveFill(waterTop - 2, baseAmp, 0.022, time * 0.9,
                   rgba(wcolBk, 0.42));
      // Front wave: tighter, faster, darker (main body)
      drawWaveFill(waterTop + 3, baseAmp * 0.75, 0.034,
                   time * 1.6 + Math.PI / 1.3,
                   rgba(wcol, 0.60));

      // Shimmer along front crest
      ctx.strokeStyle = "rgba(255,255,255,0.55)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let x = 0; x <= cssW; x += 3) {{
        const y = (waterTop + 3) + Math.sin(
          x * 0.034 + time * 1.6 + Math.PI / 1.3
        ) * baseAmp * 0.75;
        if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }}
      ctx.stroke();

      return waterTop;
    }}

    // Reduced-motion: paint once, no loop.
    if (reduceMotion) {{
      paint(target / 100, 0);
      return;
    }}

    // Animated loop with ease-in from 0 to target.
    let tPrev = 0;
    let bubbleTimer = 0;
    let displayLevel = 0;

    function frame(tMs) {{
      if (!tPrev) tPrev = tMs;
      const dt = Math.min(0.05, (tMs - tPrev) / 1000);
      tPrev = tMs;

      const easing = 1 - Math.pow(0.02, dt);
      displayLevel += (target - displayLevel) * easing;

      const level = displayLevel / 100;
      const time  = tMs / 1000;
      const waterTop = paint(level, time);

      // Bubbles when there's meaningful water
      if (displayLevel > 10) {{
        bubbleTimer += dt;
        const spawnEvery = 0.06 + 0.4 / Math.max(10, displayLevel);
        while (bubbleTimer >= spawnEvery) {{
          bubbleTimer -= spawnEvery;
          spawnBubble();
        }}
      }} else {{
        bubbleTimer = 0;
      }}
      ctx.fillStyle = "rgba(255,255,255,0.75)";
      for (let i = bubbles.length - 1; i >= 0; i--) {{
        const b = bubbles[i];
        b.y -= b.vy;
        b.x += b.drift;
        if (b.y <= waterTop + 2 || b.x < -4 || b.x > cssW + 4) {{
          bubbles.splice(i, 1);
          continue;
        }}
        ctx.globalAlpha = b.alpha;
        ctx.beginPath();
        ctx.arc(b.x, b.y, b.r, 0, Math.PI * 2);
        ctx.fill();
      }}
      ctx.globalAlpha = 1;

      requestAnimationFrame(frame);
    }}

    requestAnimationFrame(frame);
  }});
}})();
</script>
</body>
</html>
"""


def render():
    log = _load_log()
    # Only show records produced by our own methodology (live RSS fetch with
    # core-tier composite assessment). GDELT-backfilled rows measured a
    # different corpus with different rules, so they are excluded from the
    # visible site. They remain in data/log.json for historical reference.
    log = [r for r in log if not r.get("backfilled")]
    if not log:
        latest = {"date": "—", "label": "No data", "percentage": 0,
                  "total_articles": 0, "trump_articles": 0, "matches": [], "sources": {}}
        log_sorted_desc = []
        log_sorted_asc = []
    else:
        log_sorted_desc = sorted(log, key=lambda r: r.get("date", ""), reverse=True)
        log_sorted_asc = list(reversed(log_sorted_desc))
        latest = log_sorted_desc[0]

    html_out = PAGE.format(
        og_meta=_og_meta(latest),
        hero=_hero(latest),
        comparison=_comparison_panel(latest),
        timeline=_timeline(log_sorted_asc),
        mentions=_today_mentions(latest),
        history=_history_table(log_sorted_desc),
        methodology=_methodology(latest),
        last_run=_format_last_run(
            latest.get("last_checked_at") or latest.get("generated_at")
        ),
    )
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "index.html").write_text(html_out, encoding="utf-8")


if __name__ == "__main__":
    render()
