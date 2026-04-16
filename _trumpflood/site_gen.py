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
from themes import THEMES, label_for as theme_label

ROOT = Path(__file__).parent
LOG_FILE = ROOT / "data" / "log.json"
# Write the generated site into the repo-root sibling folder so GitHub Pages
# serves it directly at andriesfluit.be/trumpflood/.
OUTPUT_DIR = ROOT.parent / "trumpflood"

# Zone bands as (lower_bound, upper_bound, key, display_name).
# The waterline at percentage P sits in the zone where lower <= P < upper.
ZONES = [
    (0, 5, "dry", "Dry"),
    (5, 15, "puddles", "Puddles"),
    (15, 25, "wet", "Wet"),
    (25, 40, "soaked", "Soaked"),
    (40, 100, "flooding", "Flooding"),
]
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
    "google_nl": "Google News BE (NL)",
    "google_fr": "Google News BE (FR)",
    "vrt": "VRT NWS",
    "rtbf": "RTBF",
    "lalibre": "La Libre",
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

    rank_badge = ""
    if method in ("composite", "people") and rank is not None:
        dom_text = ""
        if dominance is not None:
            if dominance >= 1.0:
                dom_text = (
                    f' <span class="rank-dom">\u00b7 outweighs all 9 others '
                    f'combined ({dominance}\u00d7)</span>'
                )
            elif dominance > 0:
                dom_text = (
                    f' <span class="rank-dom">\u00b7 {dominance}\u00d7 the '
                    f'other 9 combined</span>'
                )
        theme_text = ""
        if theme_rank is not None and n_themes is not None:
            theme_text = (
                f' <span class="rank-theme">\u00b7 rank #{theme_rank} of '
                f'{n_themes} when compared to broad themes</span>'
            )
        rank_badge = (
            f'<div class="rank-badge">Rank <strong>#{rank}</strong> of '
            f'{n_people} named people today{dom_text}{theme_text}</div>'
        )
    elif method == "rank" and rank is not None:
        # Legacy path for any older records.
        rank_badge = (
            f'<div class="rank-badge">Rank '
            f'<strong>#{rank}</strong> of {n_themes} subjects today</div>'
        )

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
    {rank_badge}
    <div class="readout-stat">
      <span class="pct" style="color:{color}">{pct}<span class="pct-symbol">%</span></span>
    </div>
    <div class="readout-sub">
      <strong>{matches}</strong> of <strong>{total}</strong> Belgian news
      headlines today reference Trump
    </div>
  </div>
</section>
"""


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
    others_total = sum(v for k, v in comps.items() if k != "trump")
    if others_total:
        ratio = trump_count / others_total
        ratio_txt = f"{ratio:.2f}\u00d7"
        verdict = (
            "more than all 7 others combined" if ratio > 1
            else "less than all 7 others combined" if ratio < 1
            else "exactly equal to all 7 others combined"
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

    themes_block = _themes_panel_inline(latest)
    return f"""
<section class="block">
  <h2>Today vs. the rest</h2>
  <p class="block-intro">Trump against nine other named figures in the same
  {total}-headline core corpus.</p>
  <div class="comparison">{''.join(rows)}</div>
  {vs_block}
  {themes_block}
</section>
"""


def _themes_panel_inline(latest):
    """Themes as a sub-block within the comparison section, no <section> wrapper
    and no big h2 \u2014 just a subheading and the bars."""
    themes = latest.get("themes")
    total = latest.get("total_articles", 0)
    if not themes or not total:
        return ""

    active_zone = latest.get("zone") or "dry"
    if active_zone == "flooded":
        active_zone = "soaked"
    trump_count = (latest.get("comparisons") or {}).get("trump", 0)

    items = []
    for t in THEMES:
        count = themes.get(t["key"], 0)
        items.append((t["label"], count))
    items.sort(key=lambda i: i[1], reverse=True)

    max_count = max((c for _, c in items), default=1) or 1

    def render_row(label, count, is_trump):
        share = round(count / total * 100, 1) if total else 0
        bar_w = (count / max_count) * 100 if max_count else 0
        cls = "theme-row trump" if is_trump else "theme-row"
        color = ZONE_COLORS[active_zone] if is_trump else "#9ba295"
        return (
            f'<div class="{cls}">'
            f'<div class="theme-label">{html.escape(label)}</div>'
            f'<div class="theme-bar-wrap">'
            f'<div class="theme-bar" style="width:{bar_w:.1f}%;background:{color}"></div>'
            f'</div>'
            f'<div class="theme-stat"><strong>{count}</strong>'
            f'<span class="theme-share">{share}%</span></div>'
            f'</div>'
        )

    rows = []
    inserted = False
    for label, count in items:
        if not inserted and count <= trump_count:
            rows.append(render_row("Trump (one person)", trump_count, True))
            inserted = True
        rows.append(render_row(label, count, False))
    if not inserted:
        rows.append(render_row("Trump (one person)", trump_count, True))

    rank = sum(1 for _, c in items if c > trump_count) + 1

    return f"""
  <h3 class="sub-h">Against broad subject themes</h3>
  <p class="block-intro small">A single person will almost never out-rank
  aggregate themes. Trump would rank
  <strong>#{rank}</strong> of {len(items)}.</p>
  <div class="comparison themes-comp">{''.join(rows)}</div>
"""


# Legacy _themes_panel removed \u2014 themes are now rendered inline inside the
# comparison panel via _themes_panel_inline().


def _today_mentions(latest):
    matches = latest.get("matches") or []
    if not matches:
        return (
            '<section class="block"><h2>Today&rsquo;s mentions</h2>'
            '<p class="empty">No headlines mentioned Trump today.</p></section>'
        )
    items = []
    for m in matches:
        src = SOURCE_LABELS.get(m.get("source"), m.get("source", ""))
        url = html.escape(m.get("url", "#"), quote=True)
        title = html.escape(m.get("title", ""))
        items.append(
            f'<li><a href="{url}" target="_blank" rel="noopener">{title}</a>'
            f'<span class="src">{html.escape(src)}</span></li>'
        )
    return (
        '<section class="block"><h2>Today&rsquo;s mentions</h2>'
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

    W, H = 800, 260
    PAD_L, PAD_R, PAD_T, PAD_B = 44, 12, 16, 32
    chart_w = W - PAD_L - PAD_R
    chart_h = H - PAD_T - PAD_B

    max_pct = max((r.get("percentage", 0) for r in log_sorted_asc), default=0)
    y_max = max(50.0, max_pct * 1.25)

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

    # Threshold lines + labels on the y axis.
    grid_lines = []
    y_ticks = [0, 5, 15, 25, 40]
    y_ticks = [t for t in y_ticks if t <= y_max]
    if y_max not in y_ticks:
        y_ticks.append(int(y_max))
    for t in y_ticks:
        yp = y(t)
        grid_lines.append(
            f'<line x1="{PAD_L}" x2="{W - PAD_R}" y1="{yp:.1f}" y2="{yp:.1f}" '
            f'stroke="#cfc8b8" stroke-dasharray="2 4" stroke-width="1"/>'
        )
        grid_lines.append(
            f'<text x="{PAD_L - 8}" y="{yp + 4:.1f}" text-anchor="end" '
            f'font-size="11" fill="#8a8170" font-family="Inter, sans-serif">{t}%</text>'
        )

    # Bars per day.
    bars = []
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
        bars.append(
            f'<rect x="{x:.1f}" y="{bar_top:.1f}" width="{bar_w:.1f}" '
            f'height="{max(bar_h, 2):.1f}" rx="2" fill="{color}" '
            f'opacity="{opacity}"{stroke}>'
            f'<title>{html.escape(date_str)}: {pct}% '
            f'({r.get("trump_articles", 0)}/{r.get("total_articles", 0)}){source_note}</title>'
            f'</rect>'
        )
        if i in label_indices:
            # Show MM-DD only.
            short = date_str[5:] if len(date_str) >= 10 else date_str
            x_labels.append(
                f'<text x="{x_center:.1f}" y="{H - 10}" text-anchor="middle" '
                f'font-size="11" fill="#8a8170" font-family="Inter, sans-serif">'
                f'{html.escape(short)}</text>'
            )

    legend = " ".join(
        f'<span class="legend-item"><span class="legend-swatch" '
        f'style="background:{ZONE_COLORS[key]}"></span>'
        f'{ZONE_EMOJI[key]} {name} <small>{lo}\u2013{hi}%</small></span>'
        for lo, hi, key, name in ZONES
    )

    context_block = _timeline_context(log_sorted_asc)

    return f"""
<section class="block">
  <h2>Timeline</h2>
  {context_block}
  <div class="chart-wrap">
    <svg class="chart" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet">
      {''.join(band_rects)}
      {''.join(grid_lines)}
      {''.join(bars)}
      {''.join(x_labels)}
    </svg>
  </div>
  <div class="legend">{legend}</div>
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
        body = f"<table>{table_head}<tbody>{first_rows}</tbody></table>"
    else:
        rest_rows = "".join(_row(r) for r in rest)
        body = (
            f"<table>{table_head}<tbody>{first_rows}</tbody></table>"
            f"<details class=\"history-more\">"
            f"<summary>Show full history ({len(rest)} earlier {'day' if len(rest)==1 else 'days'})</summary>"
            f"<table>{table_head}<tbody>{rest_rows}</tbody></table>"
            f"</details>"
        )

    return f"""
<section class="block">
  <h2>Daily log</h2>
  {body}
</section>
"""


def _methodology(latest):
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
                f"<strong>{wide_trump} Trump matches = {wide_pct}%</strong> "
                f"({sign}{delta}pt vs. core). "
                f"The cross-check exists so we can spot a day where the two "
                f"tiers diverge sharply, which usually signals an aggregator "
                f"artefact rather than a real shift."
            )
        else:
            compare_line = (
                f"Today the wide corpus ({wide_total} headlines, "
                f"{wide_trump} matches) lands on the same "
                f"<strong>{wide_pct}%</strong> as the core tier, so the "
                f"tier choice doesn\u2019t change the read."
            )
        if smoothed_pct is not None:
            compare_line += (
                f" The 7-day rolling average of the core share is "
                f"<strong>{smoothed_pct}%</strong>."
            )
        wide_p = f"<p>{compare_line}</p>"
    dom_txt = (
        f" Dominance ratio today: <strong>{dominance}\u00d7</strong> the "
        f"other nine combined." if dominance is not None else ""
    )
    breadth_txt = (
        f" Breadth: <strong>{int(round(breadth * 100))}%</strong> of core "
        f"outlets ran a Trump story."
        if breadth is not None else ""
    )
    deviation_txt = (
        f" Deviation: <strong>{deviation}\u00d7</strong> the 14-day median "
        f"core share."
        if deviation is not None else
        " Deviation vs. baseline: not enough core-tier history yet."
    )
    smooth_txt = (
        f" 7-day rolling average: <strong>{smoothed_pct}%</strong>."
        if smoothed_pct is not None else
        " 7-day average: not enough core-tier history yet."
    )
    theme_txt = (
        f" For context, Trump is <strong>#{theme_rank} of {n_themes}</strong> "
        f"when compared to broad themes (war, crime, EU politics, ...) \u2014 "
        f"but note themes bundle dozens of stories, so a single person will "
        f"almost never out-rank them. That is why theme rank is "
        f"<em>context</em>, not the zone driver."
        if theme_rank is not None else ""
    )

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
      <p>Three times a day &mdash; 08:00, 14:00 and 20:00 Belgian local time &mdash;
      a script fetches headlines from 31 Belgian RSS feeds:
      Google News BE (Dutch &amp; French general), 8 Google News BE topic feeds
      (politics, world, business, tech, sport in NL; politics, world, business in FR),
      and 21 direct outlet feeds spanning VRT NWS, HLN, De Standaard, De Morgen,
      Het Nieuwsblad, GVA, HBVL, Knack, Sporza, Bruzz on the Dutch side,
      plus RTBF, La Libre, L'Echo, DH, 7sur7, BX1 directly, and De Tijd, Le Soir,
      Sudinfo, L'Avenir and RTL through Google News' <code>site:</code> filter (their
      direct feeds sit behind Cloudflare). De Standaard's direct feed is reached through
      the <code>cloudscraper</code> library to handle the basic Cloudflare JS challenge.
      Articles whose <code>pubDate</code> is today (Belgian local date) are kept;
      duplicates across feeds are removed by URL.</p>

      <h3>Core vs. wide tier</h3>
      <p>Not every feed is equal. Brussels-only outlets (BX1, Bruzz), sport-only
      outlets (Sporza), and the Google News aggregator feeds (which repackage
      content we already pull directly) structurally dilute the denominator with
      stories that are local, single-subject, or duplicated. To avoid that skew,
      the headline number on this page uses a <strong>core</strong> tier:
      national and regional-generalist outlets only &mdash; VRT, RTBF,
      De Standaard, De Morgen, HLN, Het Nieuwsblad, GVA, HBVL, Knack, La Libre,
      L'Echo, DHnet, 7sur7, plus De Tijd, Le Soir, Sudinfo, L'Avenir and RTL
      (reached via Google News' <code>site:</code> filter because their direct
      RSS is Cloudflare-gated). The full <strong>wide</strong> corpus is still
      computed and stored in <code>data/log.json</code> as a cross-check.
      Today\u2019s core corpus: <strong>{core_total} headlines</strong>,
      <strong>{core_trump} Trump matches = {core_pct}%</strong>.</p>
      {wide_p}

      <h3>Trump match</h3>
      <p>Each headline title is scanned for Trump references in three
      languages (Dutch, French, English), case-insensitive, whole words only.
      That means both the literal name and the common indirect references
      Belgian outlets use to refer to the current US administration:</p>
      <ul class="meth-rules">
        <li><strong>Direct name</strong> &mdash; <code>trump</code>
        (matches &ldquo;Donald Trump&rdquo;, &ldquo;Trump Jr.&rdquo;, etc.).</li>
        <li><strong>The White House</strong> &mdash; <code>white house</code>,
        <code>witte huis</code>, <code>maison blanche</code> /
        <code>maison-blanche</code>; plus <code>oval office</code> and
        <code>bureau ovale</code>.</li>
        <li><strong>The US / American president</strong> &mdash;
        <code>US president</code>, <code>American president</code>,
        <code>Amerikaans(e) president</code>,
        <code>president van de VS</code>,
        <code>pr\u00e9sident(e) am\u00e9ricain(e)</code>,
        <code>pr\u00e9sident(e) des \u00c9tats-Unis</code> (accents optional).</li>
      </ul>
      <p>A headline like &ldquo;Het Witte Huis waarschuwt Europa&rdquo; counts
      even though the word &ldquo;Trump&rdquo; does not appear in it. This
      closes the largest honest gap in the old literal-name-only detector.
      The <em>comparator</em> counts used for dominance and rank are a
      separate mechanism and still match people by name only \u2014 expanding
      Trump\u2019s pattern while the other nine figures stay name-only would
      bias the rank. No fuzzy matching, no body text (titles only).</p>

      <h3>Comparators &amp; themes</h3>
      <p>The same headlines are scanned for nine other people (Putin, Macron,
      De Wever, Bouchez, Orb&aacute;n, Meloni, Netanyahu, Zelensky, Musk
      &mdash; with Trump as the tenth reference entry) and for fourteen broad
      subject categories (war, crime, EU politics, Belgian government, etc.)
      using multi-language regex (NL + FR + EN keywords) so &ldquo;klimaat&rdquo;
      and &ldquo;climat&rdquo; both count as Climate.</p>

      <h3>Zone assessment</h3>
      <p>The zone is decided by a <strong>composite</strong> of four signals, not
      rank alone. &ldquo;Flooding the zone&rdquo; should be a genuine outlier: Trump
      has to take an outsized share of volume, out-compete other figures by a
      clear margin, show up <em>across</em> outlets rather than at a single paper,
      and stand out against the recent baseline. All four floors must clear for
      the top zone.</p>
      <p>Today: Trump is rank <strong>#{rank}</strong> of <strong>{n_people}</strong>
      named people.{dom_txt}{breadth_txt}{deviation_txt}{smooth_txt}{theme_txt}</p>
      <ul class="meth-rules">
        <li><strong>Flooding</strong> &mdash; rank #1 AND dominance &ge; 2.0
        (Trump alone out-mentions the other nine combined by 2&times;) AND
        &ge;5.0% of core headlines AND breadth &ge;60% of core outlets AND
        deviation &ge;1.5&times; the 14-day baseline (skipped until enough history).</li>
        <li><strong>Soaked</strong> &mdash; rank #1 AND dominance &ge; 1.2
        AND &ge;3.5% share AND breadth &ge;45%.</li>
        <li><strong>Wet</strong> &mdash; rank &le;2 AND &ge;2.0% share
        AND breadth &ge;30%.</li>
        <li><strong>Puddles</strong> &mdash; rank &le;4 AND &ge;0.8% share.</li>
        <li><strong>Dry</strong> &mdash; otherwise.</li>
      </ul>
      <p>Why four signals rather than one: a single-metric gate keeps getting
      fooled. Pure percentage treats 5% on a slow Sunday the same as 5% during
      a Ukraine offensive. Pure rank calls Trump #1 on any day nobody else is
      in the news. Dominance alone doesn\u2019t know whether coverage is wide or
      concentrated at one paper. Breadth without volume just measures how many
      outlets chase Trump at all. Requiring all four together is what makes
      &ldquo;flooding&rdquo; mean something.</p>

      <h3>Caveats &amp; limits</h3>
      <ul class="meth-rules">
        <li><strong>Title-only matching.</strong> Titles are scanned, not
        article bodies. Indirect references that the expanded detector does
        not cover (&ldquo;the administration&rdquo;, &ldquo;Washington&rdquo;,
        &ldquo;POTUS&rdquo;) are still missed. Smaller undercount than before
        the NL / FR / EN expansion, but non-zero.</li>
        <li><strong>Trump-the-family.</strong> The regex also matches
        &ldquo;Trump Jr.&rdquo;, &ldquo;Eric Trump&rdquo;, &ldquo;Trump
        Tower&rdquo;. Usually &le;2% noise but it\u2019s there.</li>
        <li><strong>Time-of-day bias.</strong> Fetch runs three times a day
        (08:00 / 14:00 / 20:00 local). Each run overwrites today&rsquo;s
        record, so the number you see is always the most recent snapshot
        &mdash; the morning view until 14:00, the afternoon view until 20:00,
        the evening view until the next morning. Late-breaking afternoon or
        evening stories are therefore captured on the same day, mitigating
        most of the old &ldquo;we miss the second half of the news cycle&rdquo;
        problem.</li>
        <li><strong>Wire-story amplification.</strong> The same Reuters / AFP
        Trump story republished across five outlets counts as five matches.
        De-dup is by URL, which differs between outlets.</li>
        <li><strong>Aggregator overlap.</strong> The Google News feeds (only
        used in the wide tier, not core) republish outlets we already pull
        directly; URLs differ from the direct ones so some duplication leaks
        in on the wide number.</li>
        <li><strong>Belgian press covers world.</strong> The denominator is
        heavy with international news that Belgian outlets choose to publish.
        This measures &ldquo;share of the news Belgians read&rdquo; &mdash; not
        &ldquo;what Belgian society is discussing internally&rdquo;.</li>
        <li><strong>Stale comparator list.</strong> The ten-person comparator
        set is fixed. If a new Belgian political figure surges in coverage,
        Trump\u2019s rank against this list will look artificially high.
        Periodic review needed.</li>
        <li><strong>Arbitrary absolute thresholds.</strong> The 5.0% / 3.5% /
        2.0% / 0.8% cutoffs plus the 2.0&times; / 1.2&times; dominance and
        60% / 45% / 30% breadth floors are chosen rather than calibrated
        against historical distributions. As the archive of live days grows,
        these should be re-expressed as percentiles of Trump\u2019s own
        history.</li>
        <li><strong>Theme overlap.</strong> A headline can match multiple
        themes (a Gaza article counts for War and for EU politics if Macron is
        quoted). Themes are not mutually exclusive.</li>
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


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Is Trump flooding the zone?</title>
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
  html, body {{ margin: 0; padding: 0; }}
  body {{
    font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    background: var(--paper);
    color: var(--ink);
    -webkit-font-smoothing: antialiased;
    line-height: 1.5;
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
    .portrait-wrap {{ max-width: 360px; margin: 0 auto; }}
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
    margin-bottom: 20px;
  }}
  .rank-badge {{
    display: block;
    font-size: 12px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--muted);
    border-top: 1px solid var(--rule);
    border-bottom: 1px solid var(--rule);
    padding: 10px 0;
    margin: 0 0 24px;
  }}
  .rank-badge strong {{
    color: var(--ink);
    font-weight: 700;
    font-size: 14px;
    margin: 0 2px;
  }}
  .rank-dom, .rank-theme {{
    text-transform: none;
    letter-spacing: 0;
    color: var(--muted);
  }}
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
  .meth-body p {{ margin: 0 0 10px; }}
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

  {mentions}

  {history}

  {methodology}

  <footer>
    Sources: 31 Belgian RSS feeds, measured three times a day (08:00 / 14:00 / 20:00 local).
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
        hero=_hero(latest),
        comparison=_comparison_panel(latest),
        mentions=_today_mentions(latest),
        history=_history_table(log_sorted_desc),
        methodology=_methodology(latest),
        last_run=_format_last_run(latest.get("generated_at")),
    )
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "index.html").write_text(html_out, encoding="utf-8")


if __name__ == "__main__":
    render()
