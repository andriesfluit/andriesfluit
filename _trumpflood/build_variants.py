"""Build three hero-layout variants as standalone preview pages so the
visual difference can be compared side-by-side. Outputs to
trumpflood/_variants/ which is .gitignored. Each page contains the
title block + hero only; the rest of the canonical page (history table,
methodology, comparator chart, etc.) is omitted because the layout
question is hero-only.

Run:
    cd _trumpflood && python3 build_variants.py
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from site_gen import (
    ZONES, ZONE_KEYS, ZONE_COLORS,
    _hero_gates_panel,
)

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data" / "log.json"
OUT_DIR = ROOT.parent / "trumpflood" / "_variants"
PORTRAIT_SRC = ROOT.parent / "trumpflood" / "trump.jpg"


def _latest():
    log = json.loads(DATA_FILE.read_text())
    live = [r for r in log if not r.get("backfilled")]
    return live[-1] if live else log[-1]


def _full_log():
    return json.loads(DATA_FILE.read_text())


SHARED_CSS = """
:root {
  --ink: #0a1929;
  --bg: #efeadc;
  --rule: #d8d3c5;
  --muted: #6b6356;
  --accent: #1A5276;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  line-height: 1.5;
}
.wrap {
  max-width: 1240px;
  margin: 0 auto;
  padding: 28px 32px 120px;
}
.preview-bar {
  background: var(--ink);
  color: var(--bg);
  padding: 8px 16px;
  font-size: 12px;
  letter-spacing: 0.04em;
  display: flex;
  gap: 18px;
  align-items: center;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.preview-bar a {
  color: var(--bg);
  text-decoration: none;
  opacity: 0.6;
  text-transform: uppercase;
}
.preview-bar a:hover { opacity: 1; }
.preview-bar a.active { opacity: 1; font-weight: 700; border-bottom: 2px solid var(--bg); }
.preview-bar .name { font-weight: 700; margin-right: auto; }

.kicker {
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted);
  margin: 0 0 8px;
}
.title {
  font-family: "Playfair Display", "Times New Roman", Georgia, serif;
  font-size: 38px;
  line-height: 1.05;
  font-weight: 800;
  letter-spacing: -0.02em;
  margin: 0 0 8px;
}
.last-run {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
  border-bottom: 1px solid var(--rule);
  padding-bottom: 18px;
  margin-bottom: 28px;
}

/* Gates panel (shared across all variants) */
.gates-panel { margin-top: 4px; }
.gates-header {
  display: flex; align-items: baseline; justify-content: space-between;
  gap: 12px; margin-bottom: 12px; font-variant-numeric: tabular-nums;
}
.gates-zone-name {
  font-family: "Playfair Display", "Times New Roman", Georgia, serif;
  font-size: 22px; font-weight: 900; letter-spacing: 0.04em;
  text-transform: uppercase; line-height: 1;
}
.gates-cleared-count {
  font-size: 11px; color: var(--muted); text-transform: uppercase;
  letter-spacing: 0.08em;
}
.gates-grid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;
}
.gate-card {
  position: relative; display: flex; flex-direction: column;
  background: rgba(255,255,255,0.55); border: 1px solid var(--rule);
  padding: 10px 10px 0; min-height: 130px;
}
.gate-card-label {
  font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em;
  color: var(--muted); margin-bottom: 8px;
}
.gate-card-value {
  font-size: 28px; font-weight: 800; font-variant-numeric: tabular-nums;
  color: var(--ink); line-height: 1; letter-spacing: -0.02em;
}
.gate-card-hint {
  margin-top: 4px; font-size: 10.5px; line-height: 1.25;
  color: var(--muted); font-style: italic; flex: 1;
}
.gate-card-na .gate-card-hint { opacity: 0.7; }
.gate-card-bar { margin-top: 12px; height: 5px; background: var(--rule); }
.gate-card-pass .gate-card-bar { background: var(--zone-color); }
.gate-card-na .gate-card-bar {
  background: repeating-linear-gradient(45deg, var(--rule), var(--rule) 3px,
    transparent 3px, transparent 6px);
}
.gate-card-na .gate-card-value { color: var(--muted); }
.gate-card-fail .gate-card-bar { opacity: 0.4; }
.gate-card-status {
  margin-top: 6px; margin-bottom: 8px; font-size: 9px;
  text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted);
}
.gate-card-pass .gate-card-status {
  color: var(--zone-color); font-weight: 700;
}

@media (max-width: 600px) {
  .gates-grid { grid-template-columns: repeat(2, 1fr); gap: 6px; }
  .gate-card { min-height: 118px; }
  .gate-card-value { font-size: 24px; }
  .gate-card-hint { font-size: 10px; }
}
"""


def _nav(active_letter: str) -> str:
    items = [
        ("/", "current 50/50"),
        ("/_variants/A.html", "A · jumbo"),
        ("/_variants/B.html", "B · refined 50/50"),
        ("/_variants/C.html", "C · centered editorial"),
        ("/_variants/D-halftone.html", "D · halftone"),
        ("/_variants/D-strip.html", "D · 5-strip"),
        ("/_variants/D-typo.html", "D · typographic"),
        ("/_variants/E.html", "E · data-first duotone"),
    ]
    links = []
    for href, label in items:
        # Active when label exactly matches the passed identifier, OR when
        # the legacy single-letter form ("A", "B", "C") is the prefix of
        # the label, OR when active_letter is "—" (current canonical page).
        is_active = (
            (active_letter == "—" and href == "/") or
            label == active_letter or
            (len(active_letter) == 1 and label.startswith(active_letter + " "))
        )
        cls = "active" if is_active else ""
        links.append(f'<a class="{cls}" href="{href}">{label}</a>')
    return (
        '<div class="preview-bar">'
        '<span class="name">Trumpflood · hero variants</span>'
        + "".join(links)
        + '</div>'
    )


def _title_block() -> str:
    return (
        '<p class="kicker">Trumpflood · Belgian news monitor</p>'
        '<h1 class="title">Is Trump flooding the zone?</h1>'
        '<p class="last-run">LAST RUN: MON 27 APR 2026, 08:16 CEST</p>'
    )


def _zone_idx(active_zone: str) -> int:
    try:
        return ZONE_KEYS.index(active_zone)
    except ValueError:
        return 0


def _water_canvas_script() -> str:
    """Same water animation as the canonical site_gen.py page (sine waves +
    bubbles, easing in to data-water-target). Triggered by any element with
    .portrait + .water-canvas inside it."""
    return """
<script>
(function () {
  const portraits = document.querySelectorAll(".portrait");
  const reduceMotion = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  function hexToRgb(h) {
    h = (h || "").trim().replace(/^#/, "");
    if (h.length === 3) h = h.split("").map(c => c + c).join("");
    return { r: parseInt(h.substr(0,2),16)||0, g: parseInt(h.substr(2,2),16)||0, b: parseInt(h.substr(4,2),16)||0 };
  }
  function lighten(c, a) {
    return { r: Math.min(255, c.r+(255-c.r)*a), g: Math.min(255, c.g+(255-c.g)*a), b: Math.min(255, c.b+(255-c.b)*a) };
  }
  function rgba(c, a) { return "rgba("+c.r+","+c.g+","+c.b+","+a+")"; }
  portraits.forEach(function (portrait) {
    const canvas = portrait.querySelector(".water-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const target = parseFloat(portrait.getAttribute("data-water-target")) || 0;
    const hex = portrait.getAttribute("data-water-color") || "#0ea5e9";
    const wcol = hexToRgb(hex);
    const wcolBk = lighten(wcol, 0.18);
    let cssW = 0, cssH = 0;
    function resize() {
      const rect = canvas.getBoundingClientRect();
      cssW = rect.width; cssH = rect.height;
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.max(1, Math.floor(cssW*dpr));
      canvas.height = Math.max(1, Math.floor(cssH*dpr));
      ctx.setTransform(dpr,0,0,dpr,0,0);
    }
    resize();
    window.addEventListener("resize", resize);
    const bubbles = [];
    function spawn() {
      bubbles.push({ x: 8 + Math.random()*(cssW-16), y: cssH+4,
        r: 1 + Math.random()*3.2, vy: 0.35 + Math.random()*0.9,
        drift: (Math.random()-0.5)*0.3, alpha: 0.25 + Math.random()*0.35 });
    }
    function drawWave(top, amp, freq, phase, color) {
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.moveTo(0, cssH);
      ctx.lineTo(0, top);
      for (let x = 0; x <= cssW; x += 3) {
        const y = top + Math.sin(x*freq+phase)*amp;
        ctx.lineTo(x, y);
      }
      ctx.lineTo(cssW, cssH);
      ctx.closePath();
      ctx.fill();
    }
    function paint(level, time) {
      ctx.clearRect(0, 0, cssW, cssH);
      const top = cssH * (1 - level);
      const amp = 1.2 + Math.min(level*22, 18);
      drawWave(top - 2, amp, 0.022, time*0.9, rgba(wcolBk, 0.42));
      drawWave(top + 3, amp*0.75, 0.034, time*1.6 + Math.PI/1.3, rgba(wcol, 0.60));
      ctx.strokeStyle = "rgba(255,255,255,0.55)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let x = 0; x <= cssW; x += 3) {
        const y = (top+3) + Math.sin(x*0.034 + time*1.6 + Math.PI/1.3) * amp*0.75;
        if (x === 0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
      }
      ctx.stroke();
      return top;
    }
    if (reduceMotion) { paint(target/100, 0); return; }
    let tPrev = 0, bubbleTimer = 0, displayLevel = 0;
    function frame(tMs) {
      if (!tPrev) tPrev = tMs;
      const dt = Math.min(0.05, (tMs - tPrev)/1000);
      tPrev = tMs;
      const easing = 1 - Math.pow(0.02, dt);
      displayLevel += (target - displayLevel) * easing;
      const level = displayLevel/100;
      const time = tMs/1000;
      const waterTop = paint(level, time);
      if (displayLevel > 10) {
        bubbleTimer += dt;
        const spawnEvery = 0.06 + 0.4 / Math.max(10, displayLevel);
        while (bubbleTimer >= spawnEvery) { bubbleTimer -= spawnEvery; spawn(); }
      } else { bubbleTimer = 0; }
      ctx.fillStyle = "rgba(255,255,255,0.75)";
      for (let i = bubbles.length - 1; i >= 0; i--) {
        const b = bubbles[i];
        b.y -= b.vy; b.x += b.drift;
        if (b.y <= waterTop+2 || b.x < -4 || b.x > cssW+4) { bubbles.splice(i,1); continue; }
        ctx.globalAlpha = b.alpha;
        ctx.beginPath();
        ctx.arc(b.x, b.y, b.r, 0, Math.PI*2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  });
})();
</script>
"""


# ------------- VARIANT A: JUMBO --------------------------------------------

CSS_A = """
.hero-jumbo {
  position: relative;
  min-height: 540px;
  margin: 0;
  padding: 24px 0 24px 0;
  overflow: hidden;
}
.jumbo-portrait {
  position: absolute;
  top: 0; right: 0;
  width: 38%; height: 100%;
  background-size: cover;
  background-position: center top;
}
.jumbo-portrait::before {
  content: "";
  position: absolute; inset: 0;
  background: var(--zone-color);
  mix-blend-mode: multiply;
  opacity: 0.55;
}
.jumbo-portrait::after {
  /* Gradient fade from bg colour on the left to transparent on the right */
  content: "";
  position: absolute; inset: 0;
  background: linear-gradient(to right, var(--bg) 0%, rgba(239,234,220,0.0) 45%);
}
.jumbo-content {
  position: relative;
  z-index: 2;
  max-width: 60%;
  padding-right: 24px;
}
.jumbo-readout-label {
  font-family: "Playfair Display", "Times New Roman", Georgia, serif;
  font-size: 64px; line-height: 0.98; font-weight: 900;
  letter-spacing: -0.025em; margin: 0 0 6px;
  color: var(--ink);
}
.jumbo-stat {
  display: flex; align-items: baseline; gap: 18px; margin: 18px 0 8px;
}
.jumbo-pct {
  font-size: 84px; font-weight: 800; line-height: 1;
  color: var(--zone-color); font-variant-numeric: tabular-nums;
  letter-spacing: -0.03em;
}
.jumbo-pct-symbol {
  font-size: 48px; color: var(--muted); margin-left: 4px;
}
.jumbo-sub {
  font-size: 15px; color: var(--muted); margin: 0 0 22px;
}
.jumbo-sub strong { color: var(--ink); }
.jumbo-zone-strip {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 4px;
  margin: 22px 0 16px;
}
.jumbo-zone-strip .zb {
  height: 6px;
  background: var(--rule);
  border-radius: 1px;
  position: relative;
}
.jumbo-zone-strip .zb.active { background: var(--zone-color); }
.jumbo-zone-strip .zb-label {
  position: absolute; top: 10px; left: 0;
  font-size: 9px; text-transform: uppercase;
  color: var(--muted); letter-spacing: 0.06em;
}
.jumbo-zone-strip .zb.active .zb-label { color: var(--ink); font-weight: 700; }
.jumbo-zone-row { margin-bottom: 22px; padding-bottom: 22px; }

@media (max-width: 900px) {
  .jumbo-portrait { width: 100%; height: 240px; position: relative; }
  .jumbo-portrait::after {
    background: linear-gradient(to bottom, transparent 0%, var(--bg) 90%);
  }
  .jumbo-content { max-width: 100%; padding-right: 0; }
  .jumbo-readout-label { font-size: 44px; }
  .jumbo-pct { font-size: 64px; }
}
"""


def render_a(latest: dict) -> str:
    pct = latest.get("percentage", 0.0)
    label = latest.get("label", "")
    matches = latest.get("trump_articles", 0)
    total = latest.get("total_articles", 0)
    active_zone = latest.get("zone") or "dry"
    zone_color = ZONE_COLORS.get(active_zone, ZONE_COLORS["dry"])

    # 5-step horizontal zone strip (Dry → Flooding)
    strip_zones = [
        ("dry", "Dry"), ("puddles", "Puddles"), ("wet", "Wet"),
        ("soaked", "Soaked"), ("flooding", "Flooding"),
    ]
    strip_html = '<div class="jumbo-zone-strip">'
    for key, name in strip_zones:
        is_active = (key == active_zone)
        cls = "zb active" if is_active else "zb"
        strip_html += (
            f'<div class="{cls}" style="--zone-color:{ZONE_COLORS[key]};'
            f'background:{ZONE_COLORS[key] if is_active else "var(--rule)"}">'
            f'<span class="zb-label">{name}</span>'
            f'</div>'
        )
    strip_html += '</div>'

    gates_html = _hero_gates_panel(latest)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Variant A · Jumbo · Trumpflood</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@800;900&display=swap" />
  <style>{SHARED_CSS}{CSS_A}</style>
</head>
<body>
{_nav("A")}
<div class="wrap">
  {_title_block()}
  <section class="hero-jumbo" style="--zone-color:{zone_color}">
    <div class="jumbo-portrait" style="background-image:url('../trump.jpg')"></div>
    <div class="jumbo-content">
      <h2 class="jumbo-readout-label">{label}</h2>
      <div class="jumbo-stat">
        <span class="jumbo-pct">{pct}<span class="jumbo-pct-symbol">%</span></span>
      </div>
      <p class="jumbo-sub"><strong>{matches}</strong> of <strong>{total}</strong> Belgian core-tier headlines name Trump</p>
      <div class="jumbo-zone-row">{strip_html}</div>
      {gates_html}
    </div>
  </section>
  <p style="margin-top:80px;color:var(--muted);font-size:13px;font-style:italic;">
    [Below this hero the canonical page continues: today's matches, comparator chart,
    timeline, history, methodology. Omitted from variant previews.]
  </p>
</div>
</body>
</html>
"""


# ------------- VARIANT B: REFINED 50/50 ------------------------------------

CSS_B = """
.hero-5050 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 36px;
  align-items: stretch;
  min-height: 560px;
}
.hero-5050 .left {
  display: flex;
  align-items: stretch;
  gap: 0;
}
.hero-5050 .portrait {
  flex: 1;
  background-size: cover;
  background-position: center top;
  position: relative;
  overflow: hidden;
}
.hero-5050 .portrait::before {
  content: ""; position: absolute; inset: 0;
  background: var(--zone-color); mix-blend-mode: multiply; opacity: 0.55;
}
.hero-5050 .scale {
  width: 28px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: stretch;
}
.hero-5050 .scale .band {
  flex: 1;
  position: relative;
  border: 1px solid var(--rule);
  border-bottom: none;
}
.hero-5050 .scale .band:last-child { border-bottom: 1px solid var(--rule); }
.hero-5050 .scale .band.active {
  background: var(--zone-color);
  border-color: var(--zone-color);
}
.hero-5050 .scale .band-name {
  position: absolute;
  left: 32px; top: 50%;
  transform: translateY(-50%);
  font-size: 9.5px; text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--muted); white-space: nowrap;
}
.hero-5050 .scale .band.active .band-name {
  color: var(--ink); font-weight: 700;
}
.hero-5050 .right {
  display: flex; flex-direction: column; justify-content: flex-start;
}
.hero-5050 .readout-label {
  font-family: "Playfair Display", serif;
  font-size: 64px; line-height: 0.98; font-weight: 900;
  letter-spacing: -0.025em; margin: 0 0 14px;
}
.hero-5050 .readout-stat {
  display: flex; align-items: baseline; gap: 16px; margin: 6px 0;
}
.hero-5050 .pct {
  font-size: 80px; font-weight: 800; line-height: 1;
  color: var(--zone-color); font-variant-numeric: tabular-nums;
  letter-spacing: -0.03em;
}
.hero-5050 .pct-symbol { font-size: 46px; color: var(--muted); margin-left: 4px; }
.hero-5050 .readout-sub {
  font-size: 15px; color: var(--muted); margin: 0 0 24px;
}
.hero-5050 .readout-sub strong { color: var(--ink); }
.hero-5050 .readout-sep {
  border: 0; border-top: 1px solid var(--rule); margin: 14px 0;
}
@media (max-width: 900px) {
  .hero-5050 { grid-template-columns: 1fr; min-height: 0; }
  .hero-5050 .left { height: 320px; }
  .hero-5050 .readout-label { font-size: 44px; }
  .hero-5050 .pct { font-size: 64px; }
}
"""


def render_b(latest: dict) -> str:
    pct = latest.get("percentage", 0.0)
    label = latest.get("label", "")
    matches = latest.get("trump_articles", 0)
    total = latest.get("total_articles", 0)
    active_zone = latest.get("zone") or "dry"
    zone_color = ZONE_COLORS.get(active_zone, ZONE_COLORS["dry"])
    bands = []
    # Top to bottom: Flooding → Dry (so visual reads as a thermometer with
    # higher zones up top).
    for key, name in [
        ("flooding", "Flooding"), ("soaked", "Soaked"), ("wet", "Wet"),
        ("puddles", "Puddles"), ("dry", "Dry"),
    ]:
        is_active = (key == active_zone)
        cls = "band active" if is_active else "band"
        bands.append(
            f'<div class="{cls}" style="--zone-color:{ZONE_COLORS[key]}">'
            f'<span class="band-name">{name}</span>'
            f'</div>'
        )

    gates_html = _hero_gates_panel(latest)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Variant B · Refined 50/50 · Trumpflood</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@800;900&display=swap" />
  <style>{SHARED_CSS}{CSS_B}</style>
</head>
<body>
{_nav("B")}
<div class="wrap">
  {_title_block()}
  <section class="hero-5050" style="--zone-color:{zone_color}">
    <div class="left">
      <div class="portrait" style="background-image:url('../trump.jpg')"></div>
      <div class="scale">{''.join(bands)}</div>
    </div>
    <div class="right">
      <h2 class="readout-label">{label}</h2>
      <hr class="readout-sep" />
      <div class="readout-stat">
        <span class="pct">{pct}<span class="pct-symbol">%</span></span>
      </div>
      <div class="readout-sub"><strong>{matches}</strong> of <strong>{total}</strong> Belgian core-tier headlines name Trump</div>
      <hr class="readout-sep" />
      {gates_html}
    </div>
  </section>
  <p style="margin-top:80px;color:var(--muted);font-size:13px;font-style:italic;">
    [Below this hero the canonical page continues. Omitted from variant previews.]
  </p>
</div>
</body>
</html>
"""


# Conversational answers to the page title "Is Trump flooding the zone?".
# Replaces the older descriptive labels ("Trump is flooding the zone", etc.)
# in variants where the title is kept as the lead question.
ZONE_ANSWERS = {
    "dry":      "No Trump today.",
    "puddles":  "No, just puddles.",
    "wet":      "Well, it is getting wet.",
    "soaked":   "Almost. The zone is soaked.",
    "flooding": "Yes, he is.",
}


# ------------- VARIANT C: CENTERED EDITORIAL -------------------------------

CSS_C = """
.hero-centered {
  max-width: 760px;
  margin: 0 auto;
  text-align: center;
}
.hero-centered .readout-label {
  font-family: "Playfair Display", serif;
  font-size: 56px; line-height: 1.0; font-weight: 900;
  letter-spacing: -0.02em; margin: 0 0 28px;
}
.hero-centered .pct-block {
  margin: 28px 0 6px;
  display: flex; justify-content: center; align-items: baseline; gap: 14px;
}
.hero-centered .pct {
  font-size: 92px; font-weight: 800; line-height: 1;
  color: var(--zone-color); font-variant-numeric: tabular-nums;
  letter-spacing: -0.03em;
}
.hero-centered .pct-symbol {
  font-size: 52px; color: var(--muted); margin-left: 2px;
}
.hero-centered .sub {
  font-size: 15px; color: var(--muted); margin: 0 0 22px;
}
.hero-centered .sub strong { color: var(--ink); }
.hero-centered .zone-ladder {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 4px;
  max-width: 540px;
  margin: 12px auto 30px;
}
.hero-centered .zone-ladder .step {
  position: relative;
  padding-top: 14px;
  text-align: center;
}
.hero-centered .zone-ladder .step .bar {
  height: 8px;
  background: var(--rule);
  border-radius: 1px;
}
.hero-centered .zone-ladder .step.active .bar {
  height: 14px;
  margin-top: -6px;
}
.hero-centered .zone-ladder .step .label {
  display: block;
  margin-top: 8px;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
}
.hero-centered .zone-ladder .step.active .label {
  color: var(--ink);
  font-weight: 700;
}
.hero-centered .gates-panel { text-align: left; max-width: 720px; margin: 0 auto; }
.hero-centered .gates-header { justify-content: space-between; }
.editorial-figure {
  margin: 40px auto 0;
  max-width: 340px;
  text-align: center;
}
.editorial-figure .frame {
  position: relative;
  width: 100%;
  aspect-ratio: 4 / 5;
  overflow: hidden;
  background: var(--zone-color);
}
.editorial-figure .frame img {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  object-fit: cover; object-position: center top;
}
.editorial-figure .frame::before {
  /* Subtle full-portrait tint: gives the dry top half the zone colour
     so the editorial photo always reads as "today's zone" even before
     the water animation kicks in. The water canvas paints a deeper,
     moving tint below the water line on top of this. */
  content: "";
  position: absolute; inset: 0;
  background: var(--zone-color);
  mix-blend-mode: multiply;
  opacity: 0.45;
  pointer-events: none;
  z-index: 1;
}
.editorial-figure .frame .water-canvas {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  pointer-events: none;
  mix-blend-mode: multiply;
  opacity: 0.85;
  z-index: 2;
}
.editorial-figure figcaption {
  margin-top: 10px;
  font-size: 12px;
  color: var(--muted);
  font-style: italic;
}
@media (max-width: 600px) {
  .hero-centered .readout-label { font-size: 38px; }
  .hero-centered .pct { font-size: 64px; }
}
"""


def render_c(latest: dict) -> str:
    pct = latest.get("percentage", 0.0)
    matches = latest.get("trump_articles", 0)
    total = latest.get("total_articles", 0)
    active_zone = latest.get("zone") or "dry"
    zone_color = ZONE_COLORS.get(active_zone, ZONE_COLORS["dry"])
    answer = ZONE_ANSWERS.get(active_zone, "")

    strip_zones = [
        ("dry", "Dry"), ("puddles", "Puddles"), ("wet", "Wet"),
        ("soaked", "Soaked"), ("flooding", "Flooding"),
    ]
    steps = []
    for key, name in strip_zones:
        is_active = (key == active_zone)
        cls = "step active" if is_active else "step"
        bar_color = ZONE_COLORS[key] if is_active else "var(--rule)"
        steps.append(
            f'<div class="{cls}">'
            f'<div class="bar" style="background:{bar_color}"></div>'
            f'<span class="label">{name}</span>'
            f'</div>'
        )
    active_label = next(n for k, n in strip_zones if k == active_zone)

    # Water animation level for the editorial portrait. Computed as the
    # zone's position in the 5-step ladder, then dampened to 75% of full
    # so even a Flooding day leaves Trump's face above the water (the
    # photo sits below the hero as an editorial accent, not as the
    # canonical hero, so full submersion would be too dramatic).
    zone_idx = ZONE_KEYS.index(active_zone) if active_zone in ZONE_KEYS else 0
    water_target = (zone_idx + 1) * (100 / len(ZONE_KEYS)) * 0.75

    gates_html = _hero_gates_panel(latest)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Variant C · Centered editorial · Trumpflood</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@800;900&display=swap" />
  <style>{SHARED_CSS}{CSS_C}</style>
</head>
<body>
{_nav("C")}
<div class="wrap">
  {_title_block()}
  <section class="hero-centered" style="--zone-color:{zone_color}">
    <h2 class="readout-label">{answer}</h2>
    <div class="pct-block">
      <span class="pct">{pct}<span class="pct-symbol">%</span></span>
    </div>
    <p class="sub"><strong>{matches}</strong> of <strong>{total}</strong> Belgian core-tier headlines name Trump</p>
    <div class="zone-ladder">{''.join(steps)}</div>
    {gates_html}
    <figure class="editorial-figure">
      <div class="frame portrait" data-water-color="{zone_color}" data-water-target="{water_target:.0f}">
        <img src="../trump.jpg" alt="Donald Trump" />
        <canvas class="water-canvas" aria-hidden="true"></canvas>
      </div>
      <figcaption>Trump portrait, official White House photo by Shealah Craighead. Coloured by today's zone.</figcaption>
    </figure>
  </section>
  <p style="margin-top:80px;color:var(--muted);font-size:13px;font-style:italic;">
    [Below this hero the canonical page continues. Omitted from variant previews.]
  </p>
</div>
{_water_canvas_script()}
</body>
</html>
"""


# ------------- VARIANT D: TRACKER HYBRID -----------------------------------

CSS_D = """
.tracker-title {
  display: flex;
  align-items: baseline;
  gap: 16px;
  flex-wrap: wrap;
  margin: 0 0 6px;
}
.tracker-title h1 {
  font-family: "Playfair Display", Georgia, serif;
  font-size: 38px; line-height: 1.05; font-weight: 800;
  letter-spacing: -0.02em; margin: 0;
}
.live-badge {
  display: inline-flex; align-items: center; gap: 8px;
  font-size: 11px; font-weight: 700; letter-spacing: 0.1em;
  text-transform: uppercase; color: var(--ink);
  border: 1px solid var(--rule); padding: 4px 10px;
  background: rgba(255,255,255,0.55);
}
.live-badge .pulse {
  width: 8px; height: 8px; border-radius: 50%;
  background: #2ea44f;
  box-shadow: 0 0 0 0 rgba(46, 164, 79, 0.65);
  animation: live-pulse 2.4s ease-out infinite;
}
@keyframes live-pulse {
  0%   { box-shadow: 0 0 0 0 rgba(46,164,79,0.65); }
  70%  { box-shadow: 0 0 0 8px rgba(46,164,79,0); }
  100% { box-shadow: 0 0 0 0 rgba(46,164,79,0); }
}
.tracker-strap {
  font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--muted);
  border-bottom: 1px solid var(--rule);
  padding-bottom: 18px; margin: 0 0 28px;
}

.tracker-hero {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
  gap: 32px;
  align-items: stretch;
  margin-bottom: 36px;
}
.tracker-hero .left { min-width: 0; }
.tracker-hero .right {
  display: flex; flex-direction: column;
  align-items: stretch; justify-content: center;
}
.tracker-hero .answer {
  font-family: "Playfair Display", Georgia, serif;
  font-size: 48px; line-height: 1.0; font-weight: 900;
  letter-spacing: -0.02em; margin: 0 0 18px;
}
.tracker-stat {
  display: flex; align-items: baseline; gap: 28px;
  margin: 0 0 6px;
}
.tracker-stat .pct {
  font-size: 84px; line-height: 1; font-weight: 800;
  color: var(--zone-color); font-variant-numeric: tabular-nums;
  letter-spacing: -0.03em;
}
.tracker-stat .pct-symbol {
  font-size: 48px; color: var(--muted); margin-left: 2px;
}
.spark-block {
  display: flex; flex-direction: column; align-items: stretch;
  flex: 0 0 auto;
}
.spark-svg { display: block; width: 180px; height: 44px; }
.spark-meta {
  display: flex; align-items: center; gap: 10px;
  font-size: 11px; color: var(--muted);
  letter-spacing: 0.04em; margin-top: 4px;
  font-variant-numeric: tabular-nums;
}
.spark-meta .delta {
  font-weight: 700;
  font-size: 13px;
  letter-spacing: 0;
  text-transform: none;
}
.spark-meta .delta.up { color: var(--zone-color); }
.spark-meta .delta.down { color: var(--muted); }
.spark-meta .label { text-transform: uppercase; letter-spacing: 0.1em; }
.spark-range {
  display: block;
  margin-top: 2px;
  font-size: 10px;
  color: var(--muted);
  letter-spacing: 0.04em;
  font-variant-numeric: tabular-nums;
}

.tracker-hero .sub {
  font-size: 15px; color: var(--muted); margin: 14px 0 0;
}
.tracker-hero .sub strong { color: var(--ink); }

.tracker-hero .right .portrait-box {
  position: relative;
  aspect-ratio: 4 / 5;
  width: 100%;
  max-width: 220px;
  margin: 0 0 0 auto;
  background: var(--zone-color);
  overflow: hidden;
}
.tracker-hero .right .portrait-box img {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  object-fit: cover; object-position: center top;
}
.tracker-hero .right .portrait-box::before {
  content: "";
  position: absolute; inset: 0;
  background: var(--zone-color);
  mix-blend-mode: multiply;
  opacity: 0.45;
  z-index: 1;
}
.tracker-hero .right .portrait-box .water-canvas {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  pointer-events: none;
  mix-blend-mode: multiply;
  opacity: 0.85;
  z-index: 2;
}

/* Zone ladder + gates panel reuse the centered-editorial look but as a
   full-width row in the tracker hybrid. */
.tracker-zone-ladder {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 4px;
  max-width: 100%;
  margin: 0 0 20px;
}
.tracker-zone-ladder .step { position: relative; padding-top: 12px; }
.tracker-zone-ladder .step .bar {
  height: 8px; background: var(--rule); border-radius: 1px;
}
.tracker-zone-ladder .step.active .bar {
  height: 14px; margin-top: -6px;
}
.tracker-zone-ladder .step .label {
  display: block; margin-top: 8px;
  font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--muted);
}
.tracker-zone-ladder .step.active .label {
  color: var(--ink); font-weight: 700;
}

@media (max-width: 800px) {
  .tracker-hero { grid-template-columns: 1fr; }
  .tracker-hero .right { order: -1; }
  .tracker-hero .right .portrait-box { max-width: 180px; margin: 0 auto; }
  .tracker-stat { flex-wrap: wrap; gap: 14px 24px; }
  .spark-svg { width: 160px; height: 40px; }
  .tracker-hero .answer { font-size: 36px; }
  .tracker-stat .pct { font-size: 64px; }
}
"""


def _sparkline_svg(values: list, today_color: str, baseline_color: str = "#cfcabd") -> str:
    """Render a tiny SVG sparkline of the last N daily share values. The
    last point is filled in zone-color; earlier points sit on a thin
    muted line."""
    if not values:
        return '<svg class="spark-svg" viewBox="0 0 180 44"></svg>'
    w, h = 180, 44
    pad_x, pad_y = 4, 6
    inner_w = w - 2 * pad_x
    inner_h = h - 2 * pad_y
    vmax = max(values) if values else 1.0
    vmin = min(values) if values else 0.0
    span = max(0.5, vmax - vmin)
    n = len(values)
    pts = []
    for i, v in enumerate(values):
        x = pad_x + (i / max(1, n - 1)) * inner_w
        y = pad_y + (1 - (v - vmin) / span) * inner_h
        pts.append((x, y))
    path = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    last_x, last_y = pts[-1]
    return (
        f'<svg class="spark-svg" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">'
        f'<path d="{path}" fill="none" stroke="{baseline_color}" stroke-width="1.5" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="3.5" fill="{today_color}"/>'
        f'</svg>'
    )


def _format_local_time(iso: str) -> str:
    """Return e.g. '08:16 CEST' from an ISO timestamp with offset."""
    if not iso:
        return ""
    # Quick'n'dirty: pull HH:MM out of the ISO string and append CEST/CET
    # based on the offset sign. Good enough for a preview; site_gen.py
    # already has _format_last_run for the canonical site.
    try:
        time_part = iso.split("T")[1]
        hh_mm = time_part[:5]
        offset = iso[-6:]
        zone = "CEST" if offset == "+02:00" else ("CET" if offset == "+01:00" else "UTC")
        return f"{hh_mm} {zone}"
    except Exception:
        return ""


# --- Portrait sub-variants for D ------------------------------------------

def _portrait_halftone(latest, water_target, zone_color):
    """Photo + zone-color tint + a fine CSS dot grid as a halftone overlay,
    plus the existing water-canvas animation. Reads as 'newspaper print',
    cheap to render, water still animates on top."""
    css = """
.portrait-halftone {
  position: relative;
  aspect-ratio: 4 / 5;
  width: 100%;
  max-width: 220px;
  margin: 0 0 0 auto;
  background: var(--zone-color);
  overflow: hidden;
}
.portrait-halftone img {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  object-fit: cover; object-position: center top;
  filter: contrast(1.1) saturate(0.85);
}
.portrait-halftone::before {
  content: "";
  position: absolute; inset: 0;
  background: var(--zone-color);
  mix-blend-mode: multiply;
  opacity: 0.55;
  z-index: 1;
}
.portrait-halftone::after {
  /* CMYK-style halftone dot screen on top of the photo. */
  content: "";
  position: absolute; inset: 0;
  background-image:
    radial-gradient(circle, rgba(0,0,0,0.85) 0.7px, transparent 1.4px);
  background-size: 4px 4px;
  background-position: 0 0;
  mix-blend-mode: multiply;
  opacity: 0.5;
  z-index: 2;
  pointer-events: none;
}
.portrait-halftone .water-canvas {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  pointer-events: none;
  mix-blend-mode: multiply;
  opacity: 0.7;
  z-index: 3;
}
"""
    html = (
        f'<div class="portrait-halftone portrait" '
        f'data-water-color="{zone_color}" data-water-target="{water_target:.0f}">'
        f'<img src="../trump.jpg" alt="Donald Trump" />'
        f'<canvas class="water-canvas" aria-hidden="true"></canvas>'
        f'</div>'
    )
    return html, css


def _portrait_strip(latest, water_target, zone_color):
    """Five small portraits side-by-side (or 2 columns x 3 on narrow), one
    per zone with a fixed water level. Today's zone has full saturation +
    a coloured frame; the others are grayscale-muted. Lets a reader see
    the whole zone spectrum at a glance."""
    active_zone = latest.get("zone") or "dry"
    zones = [
        ("dry",      "Dry",      0.18),
        ("puddles",  "Puddles",  0.36),
        ("wet",      "Wet",      0.54),
        ("soaked",   "Soaked",   0.72),
        ("flooding", "Flooding", 0.90),
    ]
    items = []
    for key, name, level in zones:
        is_active = (key == active_zone)
        cls = "mini active" if is_active else "mini"
        items.append(
            f'<div class="{cls}" style="--mini-zone-color:{ZONE_COLORS[key]}">'
            f'<div class="mini-frame">'
            f'<img src="../trump.jpg" alt="" />'
            f'<div class="mini-water" style="height:{int(level*100)}%"></div>'
            f'</div>'
            f'<span class="mini-label">{name}</span>'
            f'</div>'
        )
    html = '<div class="portrait-strip">' + "".join(items) + '</div>'
    css = """
.portrait-strip {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 6px;
  width: 100%;
  max-width: 360px;
  margin: 0 0 0 auto;
}
.portrait-strip .mini {
  display: flex; flex-direction: column; align-items: center;
}
.portrait-strip .mini-frame {
  position: relative;
  aspect-ratio: 4 / 5;
  width: 100%;
  overflow: hidden;
  background: #c8c0aa;
  filter: grayscale(0.85) contrast(0.9);
  opacity: 0.55;
}
.portrait-strip .mini.active .mini-frame {
  filter: none;
  opacity: 1;
  outline: 2px solid var(--mini-zone-color);
  outline-offset: 0;
}
.portrait-strip .mini-frame img {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  object-fit: cover; object-position: center top;
}
.portrait-strip .mini-water {
  position: absolute; left: 0; right: 0; bottom: 0;
  background: var(--mini-zone-color);
  mix-blend-mode: multiply;
  opacity: 0.85;
  pointer-events: none;
}
.portrait-strip .mini-label {
  margin-top: 6px;
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted);
}
.portrait-strip .mini.active .mini-label {
  color: var(--ink); font-weight: 700;
}
"""
    return html, css


def _portrait_typographic(latest, water_target, zone_color):
    """Headline composite: the Trump portrait with today's matched Belgian
    headlines layered on top in mix-blend-mode. Not a true vector
    typographic portrait (which would need a hand-traced silhouette), but
    a reasonable approximation that ties the photo to the actual data
    being measured."""
    matches = latest.get("matches", []) or []
    # Prefer name-only matches; fall back to all if list is short.
    name_only = [m["title"] for m in matches if m.get("name_only")]
    headlines = name_only if len(name_only) >= 6 else [m["title"] for m in matches]
    headlines = [h for h in headlines if h]
    # Cap title length so each line is roughly equal-weight.
    headlines = [(h[:62] + "...") if len(h) > 62 else h for h in headlines]
    headlines = headlines[:14]  # avoid overflowing the portrait

    rows = []
    for i, title in enumerate(headlines):
        rows.append(f'<span class="headline-line">{title}</span>')

    html = (
        f'<div class="portrait-typo portrait" '
        f'data-water-color="{zone_color}" data-water-target="{water_target:.0f}">'
        f'<img src="../trump.jpg" alt="Donald Trump" />'
        f'<div class="headline-overlay">'
        + "".join(rows)
        + f'</div>'
        f'<canvas class="water-canvas" aria-hidden="true"></canvas>'
        f'</div>'
    )
    css = """
.portrait-typo {
  position: relative;
  aspect-ratio: 4 / 5;
  width: 100%;
  max-width: 240px;
  margin: 0 0 0 auto;
  background: var(--zone-color);
  overflow: hidden;
}
.portrait-typo img {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  object-fit: cover; object-position: center top;
  filter: grayscale(1) contrast(1.4) brightness(0.95);
}
.portrait-typo::before {
  content: "";
  position: absolute; inset: 0;
  background: var(--zone-color);
  mix-blend-mode: multiply;
  opacity: 0.85;
  z-index: 1;
}
.portrait-typo .headline-overlay {
  position: absolute; inset: 0;
  z-index: 2;
  display: flex; flex-direction: column; justify-content: center;
  padding: 10px 8px;
  font-family: "Playfair Display", Georgia, serif;
  font-weight: 800;
  color: rgba(255,255,255,0.92);
  mix-blend-mode: overlay;
  pointer-events: none;
  overflow: hidden;
  gap: 2px;
}
.portrait-typo .headline-line {
  display: block;
  font-size: 9px;
  line-height: 1.15;
  letter-spacing: -0.01em;
  text-transform: uppercase;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.portrait-typo .water-canvas {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  pointer-events: none;
  mix-blend-mode: multiply;
  opacity: 0.55;
  z-index: 3;
}
"""
    return html, css


def render_d(latest: dict, history: list, portrait_variant: str = "halftone") -> str:
    pct = latest.get("percentage", 0.0)
    matches = latest.get("trump_articles", 0)
    total = latest.get("total_articles", 0)
    active_zone = latest.get("zone") or "dry"
    zone_color = ZONE_COLORS.get(active_zone, ZONE_COLORS["dry"])
    answer = ZONE_ANSWERS.get(active_zone, "")

    # Last 14 days of name-only share for the sparkline (live data only,
    # GDELT backfill excluded).
    series = []
    for r in history:
        if r.get("backfilled"):
            continue
        v = r.get("core_percentage_name")
        if v is None:
            v = r.get("percentage")
        if v is not None:
            series.append((r.get("date"), float(v)))
    series_14 = series[-14:]
    spark_values = [v for _, v in series_14]
    sparkline = _sparkline_svg(spark_values, zone_color)

    # Delta vs. yesterday (the previous live record, not just any prior).
    delta_html = ""
    if len(series_14) >= 2:
        today_v = series_14[-1][1]
        yest_v = series_14[-2][1]
        delta = round(today_v - yest_v, 1)
        if delta > 0:
            delta_html = f'<span class="delta up">+{delta}pt</span>'
        elif delta < 0:
            delta_html = f'<span class="delta down">{delta}pt</span>'
        else:
            delta_html = '<span class="delta">flat</span>'

    # 14-day min/max annotation lives next to the sparkline, not in the
    # plain-prose sub-line.
    if spark_values:
        spark_range = (
            f'<span class="spark-range">'
            f'min {min(spark_values):.1f}% · max {max(spark_values):.1f}%'
            f'</span>'
        )
    else:
        spark_range = ""

    last_checked = _format_local_time(latest.get("last_checked_at") or "")

    # Zone ladder
    strip_zones = [
        ("dry", "Dry"), ("puddles", "Puddles"), ("wet", "Wet"),
        ("soaked", "Soaked"), ("flooding", "Flooding"),
    ]
    steps = []
    for key, name in strip_zones:
        is_active = (key == active_zone)
        cls = "step active" if is_active else "step"
        bar_color = ZONE_COLORS[key] if is_active else "var(--rule)"
        steps.append(
            f'<div class="{cls}">'
            f'<div class="bar" style="background:{bar_color}"></div>'
            f'<span class="label">{name}</span>'
            f'</div>'
        )

    # Water animation level for the small portrait, dampened to 75%.
    zone_idx = ZONE_KEYS.index(active_zone) if active_zone in ZONE_KEYS else 0
    water_target = (zone_idx + 1) * (100 / len(ZONE_KEYS)) * 0.75

    gates_html = _hero_gates_panel(latest)

    # Portrait sub-variant: which treatment to show on the right of the
    # tracker hero. Each function returns (portrait_html, extra_css).
    portrait_funcs = {
        "halftone": _portrait_halftone,
        "strip":    _portrait_strip,
        "typo":     _portrait_typographic,
    }
    portrait_html, portrait_css = portrait_funcs.get(
        portrait_variant, _portrait_halftone
    )(latest, water_target, zone_color)

    nav_letter_map = {"halftone": "D · halftone",
                      "strip":    "D · 5-strip",
                      "typo":     "D · typographic"}
    nav_label = nav_letter_map.get(portrait_variant, "D")
    title_label = "Variant D · " + portrait_variant + " portrait · Trumpflood"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title_label}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@800;900&display=swap" />
  <style>{SHARED_CSS}{CSS_D}{portrait_css}</style>
</head>
<body>
{_nav(nav_label)}
<div class="wrap">
  <p class="kicker">Trumpflood · Belgian news monitor</p>
  <div class="tracker-title">
    <h1>Is Trump flooding the zone?</h1>
    <span class="live-badge"><span class="pulse"></span> Live · updated {last_checked} · 3 runs/day</span>
  </div>

  <section class="tracker-hero" style="--zone-color:{zone_color}">
    <div class="left">
      <h2 class="answer">{answer}</h2>
      <div class="tracker-stat">
        <span class="pct">{pct}<span class="pct-symbol">%</span></span>
        <div class="spark-block">
          {sparkline}
          <div class="spark-meta">
            {delta_html}
            <span class="label">vs. yesterday</span>
          </div>
          {spark_range}
        </div>
      </div>
      <p class="sub"><strong>{matches}</strong> of <strong>{total}</strong> Belgian news headlines name Trump.</p>
    </div>
    <div class="right">
      {portrait_html}
    </div>
  </section>

  <div class="tracker-zone-ladder">{''.join(steps)}</div>

  {gates_html}

  <p style="margin-top:80px;color:var(--muted);font-size:13px;font-style:italic;">
    [Below this hero the canonical page continues: today's matches, comparator chart,
    timeline, history, methodology. Omitted from variant previews.]
  </p>
</div>
{_water_canvas_script()}
</body>
</html>
"""


# ------------- VARIANT E: DATA-FIRST + DUOTONE PORTRAIT --------------------

# Duotone color pairs per zone. Each pair maps the image's luminance from
# dark (shadow colour) to light (highlight colour). Result: face stays
# recognisable, zone identity comes through in tone.
ZONE_DUOTONE = {
    # zone_key: (shadow_hex, highlight_hex)
    "dry":      ("#6a5a3e", "#f7eed8"),
    "puddles":  ("#2c4658", "#f0f5fa"),
    "wet":      ("#1c3548", "#ecf3f8"),
    "soaked":   ("#0a1a2e", "#e6eef7"),
    "flooding": ("#4a1310", "#fdeae2"),
}


def _hex_to_table(hex_str):
    h = hex_str.lstrip("#")
    if len(h) == 3:
        h = "".join(c + c for c in h)
    r = int(h[0:2], 16) / 255
    g = int(h[2:4], 16) / 255
    b = int(h[4:6], 16) / 255
    return r, g, b


def _duotone_filter_svg() -> str:
    """Inline SVG with one <filter> per zone. The image is first
    desaturated by feColorMatrix (luminance weights), then each channel
    is remapped via feComponentTransfer tableValues from shadow to
    highlight colour. Faces stay readable; the tonal range carries the
    zone colour."""
    grayscale_matrix = (
        "0.299 0.587 0.114 0 0 "
        "0.299 0.587 0.114 0 0 "
        "0.299 0.587 0.114 0 0 "
        "0     0     0     1 0"
    )
    filters = []
    for zone_key, (shadow, highlight) in ZONE_DUOTONE.items():
        sr, sg, sb = _hex_to_table(shadow)
        hr, hg, hb = _hex_to_table(highlight)
        filters.append(
            f'<filter id="duotone-{zone_key}" '
            f'color-interpolation-filters="sRGB">'
            f'<feColorMatrix type="matrix" values="{grayscale_matrix}"/>'
            f'<feComponentTransfer>'
            f'<feFuncR type="table" tableValues="{sr:.3f} {hr:.3f}"/>'
            f'<feFuncG type="table" tableValues="{sg:.3f} {hg:.3f}"/>'
            f'<feFuncB type="table" tableValues="{sb:.3f} {hb:.3f}"/>'
            f'</feComponentTransfer>'
            f'</filter>'
        )
    return (
        '<svg width="0" height="0" style="position:absolute;"'
        ' aria-hidden="true">'
        '<defs>' + "".join(filters) + '</defs>'
        '</svg>'
    )


CSS_E = """
/* Variant-E only: narrow the content column from the shared 1240px wrap
   down to a tighter ~880px so the data-led hero doesn't feel sparse.
   Single column of news-magazine width, all elements aligned. */
body.variant-e .wrap {
  max-width: 880px;
  padding: 28px 28px 96px;
}

.tracker-title {
  display: flex; align-items: baseline; gap: 16px; flex-wrap: wrap;
  margin: 0 0 6px;
}
.tracker-title h1 {
  font-family: "Playfair Display", Georgia, serif;
  font-size: 36px; line-height: 1.05; font-weight: 800;
  letter-spacing: -0.02em; margin: 0;
}
.live-badge {
  display: inline-flex; align-items: center; gap: 8px;
  font-size: 11px; font-weight: 700; letter-spacing: 0.1em;
  text-transform: uppercase; color: var(--ink);
  border: 1px solid var(--rule); padding: 4px 10px;
  background: rgba(255,255,255,0.55);
}
.live-badge .pulse {
  width: 8px; height: 8px; border-radius: 50%;
  background: #2ea44f;
  box-shadow: 0 0 0 0 rgba(46, 164, 79, 0.65);
  animation: live-pulse 2.4s ease-out infinite;
}
@keyframes live-pulse {
  0%   { box-shadow: 0 0 0 0 rgba(46,164,79,0.65); }
  70%  { box-shadow: 0 0 0 8px rgba(46,164,79,0); }
  100% { box-shadow: 0 0 0 0 rgba(46,164,79,0); }
}
.title-divider {
  border: 0;
  border-top: 1px solid var(--rule);
  margin: 16px 0 22px;
}

/* Live badge row above the answer (only used in the full-page preview;
   the hero-only preview keeps the badge inline with the title h1). */
.live-badge-row {
  margin: 0 0 14px;
}

/* Hero is data-only. Tightened spacing so the page reads as one composed
   block, not four full-width strips. */
.data-hero {
  margin-bottom: 22px;
}
.data-hero .answer {
  font-family: "Playfair Display", Georgia, serif;
  font-size: 44px; line-height: 1.0; font-weight: 900;
  letter-spacing: -0.02em; margin: 0 0 16px;
}
.data-hero .stat-row {
  display: flex; align-items: flex-end; gap: 28px;
  flex-wrap: wrap;
  margin: 0;
}
.data-hero .pct-block {
  display: flex; flex-direction: column; align-items: flex-start;
}
.data-hero .pct {
  font-size: 76px; line-height: 1; font-weight: 800;
  color: var(--zone-color); font-variant-numeric: tabular-nums;
  letter-spacing: -0.03em;
}
.data-hero .pct-symbol {
  font-size: 44px; color: var(--muted); margin-left: 2px;
}
.data-hero .pct-label {
  margin-top: 6px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--muted);
}
.data-hero .spark-svg { display: block; width: 200px; height: 44px; margin-bottom: 8px; }
.data-hero .stat-meta-row {
  display: flex; flex-wrap: wrap; align-items: baseline;
  gap: 0 14px;
  margin-top: 6px;
  font-size: 12px;
  color: var(--muted);
  letter-spacing: 0.04em;
  font-variant-numeric: tabular-nums;
}
.data-hero .stat-meta-row .delta {
  font-weight: 700; font-size: 13px; color: var(--ink);
}
.data-hero .stat-meta-row .delta.up { color: var(--zone-color); }
.data-hero .stat-meta-row .delta.down { color: var(--ink); }
.data-hero .stat-meta-row .label {
  text-transform: uppercase; letter-spacing: 0.1em;
  color: var(--muted);
}
.data-hero .stat-meta-row .sep { color: var(--rule); }
.data-hero .sub {
  font-size: 15px; color: var(--muted); margin: 14px 0 0;
}
.data-hero .sub strong { color: var(--ink); }

/* Zone ladder, full width below the data hero. */
.tracker-zone-ladder {
  display: grid; grid-template-columns: repeat(5, 1fr);
  gap: 4px; max-width: 100%; margin: 0 0 22px;
}
.tracker-zone-ladder .step { position: relative; padding-top: 14px; }
.tracker-zone-ladder .step .bar {
  height: 8px; background: var(--rule); border-radius: 1px;
}
.tracker-zone-ladder .step.active .bar {
  height: 14px; margin-top: -6px;
}
.tracker-zone-ladder .step .label {
  display: block; margin-top: 8px;
  font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--muted);
}
.tracker-zone-ladder .step.active .label {
  color: var(--ink); font-weight: 700;
}

/* Editorial portrait directly below the gates panel (28px gap, not 56,
   so the photo peeks above the fold and invites scroll without orphan
   whitespace). Duotone treatment, no multiply stack. */
.portrait-figure {
  margin: 28px auto 0;
  max-width: 280px;
  text-align: center;
}
.portrait-figure .frame {
  position: relative;
  width: 100%;
  aspect-ratio: 4 / 5;
  overflow: hidden;
  background: #f1ead7;
}
.portrait-figure .frame img {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  object-fit: cover; object-position: center top;
  /* The duotone filter is applied via inline style so the active zone
     drives which <filter> from the inline <svg> is referenced. */
}
.portrait-figure .frame .water-canvas {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  pointer-events: none;
  /* Multiply against the duotoned image. The duotone has narrowed the
     image's tonal range, so the water needs higher opacity than on a
     normal photo to stay clearly visible. 0.7 reads as a real water
     band against the duotoned face without crushing the highlights. */
  mix-blend-mode: multiply;
  opacity: 0.7;
}
/* Floating zone label aligned with the water surface inside the photo
   frame. Acts as a measurement marker on the right edge, closing the
   visual link between the horizontal zone ladder above and the rising
   water below. */
.portrait-figure .water-marker {
  position: absolute;
  right: -2px;
  transform: translateY(-50%);
  z-index: 4;
  display: inline-flex;
  align-items: center;
  font-size: 9.5px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ink);
  background: rgba(255,255,255,0.95);
  padding: 4px 9px 4px 8px;
  white-space: nowrap;
  box-shadow: 0 1px 2px rgba(0,0,0,0.08);
}
.portrait-figure .water-marker::before {
  content: "";
  display: inline-block;
  width: 14px;
  height: 2px;
  background: var(--zone-color);
  margin-right: 6px;
}
.portrait-figure figcaption {
  margin-top: 10px;
  font-size: 12px; color: var(--muted); font-style: italic;
}

@media (max-width: 760px) {
  .tracker-title h1 { font-size: 28px; }
  .data-hero .answer { font-size: 38px; margin-bottom: 18px; }
  .data-hero .stat-row { gap: 20px; }
  .data-hero .pct { font-size: 72px; }
  .data-hero .pct-symbol { font-size: 42px; }
  .data-hero .spark-svg { width: 180px; height: 44px; }
}
"""


def render_e(latest: dict, history: list) -> str:
    pct = latest.get("percentage", 0.0)
    matches = latest.get("trump_articles", 0)
    total = latest.get("total_articles", 0)
    active_zone = latest.get("zone") or "dry"
    zone_color = ZONE_COLORS.get(active_zone, ZONE_COLORS["dry"])
    answer = ZONE_ANSWERS.get(active_zone, "")

    # Sparkline data (live days only).
    series = []
    for r in history:
        if r.get("backfilled"):
            continue
        v = r.get("core_percentage_name")
        if v is None:
            v = r.get("percentage")
        if v is not None:
            series.append((r.get("date"), float(v)))
    series_14 = series[-14:]
    spark_values = [v for _, v in series_14]
    sparkline = _sparkline_svg(spark_values, zone_color).replace(
        'class="spark-svg"', 'class="spark-svg"'
    )

    delta_html = ""
    if len(series_14) >= 2:
        today_v = series_14[-1][1]
        yest_v = series_14[-2][1]
        delta = round(today_v - yest_v, 1)
        if delta > 0:
            delta_html = f'<span class="delta up">+{delta}pt</span>'
        elif delta < 0:
            delta_html = f'<span class="delta down">{delta}pt</span>'
        else:
            delta_html = '<span class="delta">flat</span>'

    if spark_values:
        spark_range = (
            f'<span class="spark-range">'
            f'min {min(spark_values):.1f}% · max {max(spark_values):.1f}%'
            f'</span>'
        )
    else:
        spark_range = ""

    last_checked = _format_local_time(latest.get("last_checked_at") or "")

    strip_zones = [
        ("dry", "Dry"), ("puddles", "Puddles"), ("wet", "Wet"),
        ("soaked", "Soaked"), ("flooding", "Flooding"),
    ]
    steps = []
    for key, name in strip_zones:
        is_active = (key == active_zone)
        cls = "step active" if is_active else "step"
        bar_color = ZONE_COLORS[key] if is_active else "var(--rule)"
        steps.append(
            f'<div class="{cls}">'
            f'<div class="bar" style="background:{bar_color}"></div>'
            f'<span class="label">{name}</span>'
            f'</div>'
        )

    # Water animation level for the editorial portrait. Dampened to 70%
    # so the wave line sits visibly across the lower half of the photo
    # (face stays fully above it) and the wave motion reads at a glance.
    zone_idx = ZONE_KEYS.index(active_zone) if active_zone in ZONE_KEYS else 0
    water_target = (zone_idx + 1) * (100 / len(ZONE_KEYS)) * 0.70

    gates_html = _hero_gates_panel(latest)
    duotone_defs = _duotone_filter_svg()

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Variant E · Data-first duotone · Trumpflood</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@800;900&display=swap" />
  <style>{SHARED_CSS}{CSS_E}</style>
</head>
<body class="variant-e">
{_nav("E · data-first duotone")}
{duotone_defs}
<div class="wrap">
  <p class="kicker">Trumpflood · Belgian news monitor</p>
  <div class="tracker-title">
    <h1>Is Trump flooding the zone?</h1>
    <span class="live-badge"><span class="pulse"></span> Live · updated {last_checked} · 3 runs/day</span>
  </div>
  <hr class="title-divider" />

  <section class="data-hero" style="--zone-color:{zone_color}">
    <h2 class="answer">{answer}</h2>
    <div class="stat-row">
      <span class="pct">{pct}<span class="pct-symbol">%</span></span>
      <div class="spark-block">
        {sparkline}
        <div class="spark-meta">
          {delta_html}
          <span class="label">vs. yesterday</span>
        </div>
        {spark_range}
      </div>
    </div>
    <p class="sub"><strong>{matches}</strong> of <strong>{total}</strong> Belgian news headlines name Trump.</p>
  </section>

  <div class="tracker-zone-ladder">{''.join(steps)}</div>

  {gates_html}

  <figure class="portrait-figure">
    <div class="frame portrait" data-water-color="{zone_color}" data-water-target="{water_target:.0f}">
      <img src="../trump.jpg" alt="Donald Trump"
           style="filter: url(#duotone-{active_zone});" />
      <canvas class="water-canvas" aria-hidden="true"></canvas>
      <span class="water-marker" style="top: {100 - water_target:.1f}%;">{active_zone.upper()}</span>
    </div>
    <figcaption>Trump portrait, official White House photo by Shealah Craighead. Duotoned in today's zone colour. Water level marks the active zone on the thermometer above.</figcaption>
  </figure>

  <p style="margin-top:80px;color:var(--muted);font-size:13px;font-style:italic;">
    [Below this hero the canonical page continues. Omitted from variant previews.]
  </p>
</div>
{_water_canvas_script()}
</body>
</html>
"""


def _e_hero_block(latest: dict, history: list) -> str:
    """Returns just the variant-E hero block (answer + big % + sparkline +
    sub + zone ladder + gates panel + duotone portrait), ready to be
    inserted into the canonical PAGE template's {hero} slot.

    The canonical masthead above the slot already provides kicker + h1 +
    last-run, so we don't repeat them here. The portrait carries the
    floating zone label aligned with the water surface."""
    pct = latest.get("percentage", 0.0)
    matches = latest.get("trump_articles", 0)
    total = latest.get("total_articles", 0)
    active_zone = latest.get("zone") or "dry"
    zone_color = ZONE_COLORS.get(active_zone, ZONE_COLORS["dry"])
    answer = ZONE_ANSWERS.get(active_zone, "")

    series = []
    for r in history:
        if r.get("backfilled"):
            continue
        v = r.get("core_percentage_name")
        if v is None:
            v = r.get("percentage")
        if v is not None:
            series.append((r.get("date"), float(v)))
    series_14 = series[-14:]
    spark_values = [v for _, v in series_14]
    sparkline = _sparkline_svg(spark_values, zone_color)

    delta_html = ""
    if len(series_14) >= 2:
        today_v = series_14[-1][1]
        yest_v = series_14[-2][1]
        delta = round(today_v - yest_v, 1)
        if delta > 0:
            delta_html = f'<span class="delta up">+{delta}pt</span>'
        elif delta < 0:
            delta_html = f'<span class="delta down">{delta}pt</span>'
        else:
            delta_html = '<span class="delta">flat</span>'

    if spark_values:
        range_html = (
            f'<span>min {min(spark_values):.1f}% · max {max(spark_values):.1f}% over 14 days</span>'
        )
    else:
        range_html = ""

    last_checked = _format_local_time(latest.get("last_checked_at") or "")

    strip_zones = [
        ("dry", "Dry"), ("puddles", "Puddles"), ("wet", "Wet"),
        ("soaked", "Soaked"), ("flooding", "Flooding"),
    ]
    steps = []
    for key, name in strip_zones:
        is_active = (key == active_zone)
        cls = "step active" if is_active else "step"
        bar_color = ZONE_COLORS[key] if is_active else "var(--rule)"
        steps.append(
            f'<div class="{cls}">'
            f'<div class="bar" style="background:{bar_color}"></div>'
            f'<span class="label">{name}</span>'
            f'</div>'
        )

    zone_idx = ZONE_KEYS.index(active_zone) if active_zone in ZONE_KEYS else 0
    water_target = (zone_idx + 1) * (100 / len(ZONE_KEYS)) * 0.70
    gates_html = _hero_gates_panel(latest)

    sep_html = '<span class="sep">·</span>' if (delta_html and range_html) else ''

    return f"""
<section class="data-hero" style="--zone-color:{zone_color}">
  <div class="live-badge-row">
    <span class="live-badge"><span class="pulse"></span> Live · updated {last_checked} · 3 runs/day</span>
  </div>
  <h2 class="answer">{answer}</h2>
  <div class="stat-row">
    <div class="pct-block">
      <span class="pct">{pct}<span class="pct-symbol">%</span></span>
      <span class="pct-label">share of Belgian news headlines today</span>
    </div>
    {sparkline}
  </div>
  <div class="stat-meta-row">
    {delta_html}
    <span class="label">vs. yesterday</span>
    {sep_html}
    {range_html}
  </div>
  <p class="sub"><strong>{matches}</strong> of <strong>{total}</strong> headlines name Trump.</p>
</section>

<div class="tracker-zone-ladder">{''.join(steps)}</div>

{gates_html}

<figure class="portrait-figure">
  <div class="frame portrait" data-water-color="{zone_color}" data-water-target="{water_target:.0f}">
    <img src="trump.jpg" alt="Donald Trump"
         style="filter: url(#duotone-{active_zone});" />
    <canvas class="water-canvas" aria-hidden="true"></canvas>
    <span class="water-marker" style="top: {100 - water_target:.1f}%;">{active_zone.upper()}</span>
  </div>
  <figcaption>Trump portrait, official White House photo by Shealah Craighead. Duotoned in today's zone colour. Water level marks the active zone on the thermometer above.</figcaption>
</figure>
"""


def build_e_full_preview(latest, history):
    """Render the canonical page with variant-E hero patched in. Goes to
    trumpflood/_variants/E-full/index.html so the user can scroll through
    the entire page (timeline, comparators, today's matches, methodology)
    with the new hero on top."""
    import site_gen
    from pathlib import Path

    full_dir = OUT_DIR / "E-full"
    full_dir.mkdir(parents=True, exist_ok=True)

    # Copy the trump.jpg so the relative path in the patched hero resolves.
    if PORTRAIT_SRC.exists():
        shutil.copyfile(PORTRAIT_SRC, full_dir / "trump.jpg")

    original_hero = site_gen._hero
    original_output = site_gen.OUTPUT_DIR

    def patched_hero(rec):
        return _e_hero_block(rec, history)

    site_gen._hero = patched_hero
    site_gen.OUTPUT_DIR = full_dir

    try:
        site_gen.render()
    finally:
        site_gen._hero = original_hero
        site_gen.OUTPUT_DIR = original_output

    # Inject variant-E CSS + duotone SVG into the rendered page so the
    # new hero styles correctly.
    out_file = full_dir / "index.html"
    html = out_file.read_text(encoding="utf-8")
    extra = (
        f'<style>{CSS_E}</style>'
        f'{_duotone_filter_svg()}'
    )
    html = html.replace("</head>", f"{extra}</head>", 1)
    html = html.replace("<body>", '<body class="variant-e">', 1)
    # Add a top nav so the user can switch back to the hero-only previews.
    html = html.replace(
        '<body class="variant-e">',
        '<body class="variant-e">\n' + _nav("E · data-first duotone"),
        1,
    )
    out_file.write_text(html, encoding="utf-8")


# --------------------------------- BUILD ------------------------------------

INDEX_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Trumpflood · Hero variants index</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif;
           background: #efeadc; color: #0a1929; padding: 48px;
           max-width: 720px; margin: 0 auto; }
    h1 { font-family: "Playfair Display", Georgia, serif; }
    a { display: block; padding: 14px 18px; margin: 8px 0;
        background: #fff; color: #0a1929; text-decoration: none;
        border: 1px solid #d8d3c5; }
    a:hover { background: #1A5276; color: #fff; }
    .small { color: #6b6356; font-size: 13px; }
  </style>
</head>
<body>
<h1>Trumpflood · hero variants</h1>
<p class="small">Three layout proposals for the hero section. Click to compare; use the top bar inside each to switch quickly.</p>
<a href="/">Current 50/50 (rendered live page)</a>
<a href="/_variants/A.html">A · Jumbo (CFPB-style, portrait fades from right third)</a>
<a href="/_variants/B.html">B · Refined 50/50 (left column matches right column height)</a>
<a href="/_variants/C.html">C · Centered editorial (FT/Pudding-style, portrait below)</a>
<p class="small" style="margin-top:24px;">D · Tracker hybrid - three portrait treatments:</p>
<a href="/_variants/D-halftone.html">D · Halftone newspaper (CSS dot overlay)</a>
<a href="/_variants/D-strip.html">D · 5-state zone strip (5 mini-portraits, today highlighted)</a>
<a href="/_variants/D-typo.html">D · Typographic (today's headlines layered over portrait)</a>
<p class="small" style="margin-top:24px;">E · Data-first, no portrait in hero, duotone editorial photo below:</p>
<a href="/_variants/E.html">E · Data-first duotone (hero only, no rest of page)</a>
<a href="/_variants/E-full/">E · Full page preview (variant-E hero + canonical timeline / matches / methodology)</a>
</body>
</html>
"""


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Symlink trump.jpg next to the variants so background-image url('../trump.jpg')
    # resolves from inside _variants/. The portrait already lives in trumpflood/,
    # one level up, so the relative path works without copying.
    if not (OUT_DIR.parent / "trump.jpg").exists() and PORTRAIT_SRC.exists():
        shutil.copyfile(PORTRAIT_SRC, OUT_DIR.parent / "trump.jpg")

    latest = _latest()
    history = _full_log()

    (OUT_DIR / "A.html").write_text(render_a(latest), encoding="utf-8")
    (OUT_DIR / "B.html").write_text(render_b(latest), encoding="utf-8")
    (OUT_DIR / "C.html").write_text(render_c(latest), encoding="utf-8")
    (OUT_DIR / "D-halftone.html").write_text(
        render_d(latest, history, "halftone"), encoding="utf-8")
    (OUT_DIR / "D-strip.html").write_text(
        render_d(latest, history, "strip"), encoding="utf-8")
    (OUT_DIR / "D-typo.html").write_text(
        render_d(latest, history, "typo"), encoding="utf-8")
    (OUT_DIR / "E.html").write_text(render_e(latest, history), encoding="utf-8")
    build_e_full_preview(latest, history)
    (OUT_DIR / "index.html").write_text(INDEX_PAGE, encoding="utf-8")

    print(f"Wrote variant pages to {OUT_DIR}")


if __name__ == "__main__":
    main()
