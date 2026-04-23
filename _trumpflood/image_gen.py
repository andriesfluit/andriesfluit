from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# LinkedIn URL-preview: 1200×628 (≈1.91:1)
W, H = 1200, 628

# ── Site palette (matches CSS variables) ────────────────────────────────────
PAPER  = (245, 243, 238)   # --paper: #f5f3ee
INK    = (10,  25,  41)    # --ink:   #0a1929
MUTED  = (107, 99,  86)    # --muted: #6b6356
RULE_C = (216, 211, 197)   # --rule:  #d8d3c5
WHITE  = (255, 255, 255)

ZONE_COLORS = {
    "dry":      (200, 184, 154),   # #c8b89a
    "puddles":  (168, 196, 216),   # #a8c4d8
    "wet":      (74,  127, 160),   # #4a7fa0
    "soaked":   (30,  58,  95),    # #1e3a5f
    "flooding": (176, 58,  46),    # #b03a2e
}
ZONE_ORDER  = ["flooding", "soaked", "wet", "puddles", "dry"]  # top → bottom
ZONE_LABELS = {
    "dry": "Dry", "puddles": "Puddles", "wet": "Wet",
    "soaked": "Soaked", "flooding": "Flooding",
}

_SERIF_BOLD = [
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
    "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
]
_SANS_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]
_SANS_REG = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]


def _load(paths, size):
    for p in paths:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    words = text.split()
    lines, line = [], ""
    for w in words:
        cand = (line + " " + w).strip()
        if draw.textlength(cand, font=font) <= max_w:
            line = cand
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def _lh(font):
    bb = font.getbbox("Ay")
    return bb[3] - bb[1]


def _lighten(color, amount=55):
    return tuple(min(255, c + amount) for c in color)


def generate_image(
    path, label, today, pct, total,
    zone="dry", trump_count=0,
    rank=None, n_people=None, dominance=None,
    breadth=None, core_outlets_active=0,
    rival_label=None, rival_count=0,
):
    img  = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)
    zc   = ZONE_COLORS.get(zone, ZONE_COLORS["dry"])

    # ── Layout ───────────────────────────────────────────────────────────────
    BORDER   = 6      # top accent strip (zone color)
    SCALE_W  = 80     # left zone-scale column
    PAD      = 44     # horizontal padding inside content area
    CX       = SCALE_W + PAD          # content left x
    CR       = W - PAD                # content right x
    CW       = CR - CX               # content width (~1032 px)

    # ── Top accent border (zone color, thin) ─────────────────────────────────
    draw.rectangle([0, 0, W, BORDER], fill=zc)

    # ── Zone scale (left column, full height below border) ───────────────────
    body_h  = H - BORDER
    band_h  = body_h / len(ZONE_ORDER)
    band_f  = _load(_SANS_BOLD, 11)

    for i, z in enumerate(ZONE_ORDER):
        color     = ZONE_COLORS[z]
        is_active = (z == zone)
        y0 = BORDER + int(i * band_h)
        y1 = BORDER + int((i + 1) * band_h)
        fill = color if is_active else _lighten(color, 55)
        draw.rectangle([0, y0, SCALE_W, y1], fill=fill)
        name = ZONE_LABELS[z]
        nw   = draw.textlength(name, font=band_f)
        cy   = (y0 + y1) / 2 - 7
        tc   = WHITE if is_active else (155, 145, 135)
        draw.text(((SCALE_W - nw) / 2, cy), name, fill=tc, font=band_f)

    # Separator line between scale and content
    draw.line([SCALE_W, BORDER, SCALE_W, H], fill=RULE_C, width=1)

    # ── Content area ─────────────────────────────────────────────────────────
    y = BORDER + 30

    # Site title + URL (ink color, like on the site)
    title_f = _load(_SANS_BOLD, 22)
    title   = "Is Trump flooding the zone?"
    draw.text((CX, y), title, fill=INK, font=title_f)

    url_f = _load(_SANS_REG, 17)
    url   = "andriesfluit.be/trumpflood"
    uw    = draw.textlength(url, font=url_f)
    draw.text((CR - uw, y + 3), url, fill=MUTED, font=url_f)
    y += _lh(title_f) + 14

    # Rule
    draw.line([CX, y, CR, y], fill=RULE_C, width=1)
    y += 18

    # Zone label (large serif, ink)
    lbl_f = _load(_SERIF_BOLD, 56)
    lines = _wrap(draw, label, lbl_f, CW)
    for line in lines:
        draw.text((CX, y), line, fill=INK, font=lbl_f)
        y += _lh(lbl_f) + 4
    y += 14

    # Rule
    draw.line([CX, y, CR, y], fill=RULE_C, width=1)
    y += 16

    # Percentage (serif bold, large, zone color) + stats side by side
    pct_f   = _load(_SERIF_BOLD, 96)
    pct_str = f"{pct}%"
    pct_w   = draw.textlength(pct_str, font=pct_f)
    draw.text((CX, y), pct_str, fill=zc, font=pct_f)

    # Stats to the right of the percentage
    stats = []
    if rank and n_people:
        s = f"Rank #{rank} of {n_people} named figures"
        if dominance is not None and dominance > 0:
            s += f"  ·  {dominance}× vs. rest combined"
        stats.append(s)
    if breadth and core_outlets_active:
        n_out = int(round(breadth * core_outlets_active))
        stats.append(f"In {n_out} of {core_outlets_active} national outlets")
    if rival_label and rival_count:
        stats.append(f"Next up: {rival_label} ({rival_count})")

    stat_f  = _load(_SANS_REG, 21)
    stat_x  = CX + int(pct_w) + 36
    stat_y  = y + 10
    for s in stats:
        draw.text((stat_x, stat_y), s, fill=MUTED, font=stat_f)
        stat_y += _lh(stat_f) + 10

    y += _lh(pct_f) + 8

    # Sub-line below percentage
    sub_f = _load(_SANS_REG, 21)
    sub   = f"{trump_count} of {total} Belgian headlines name Trump"
    draw.text((CX, y), sub, fill=MUTED, font=sub_f)

    # ── Footer ───────────────────────────────────────────────────────────────
    foot_y = H - 38
    draw.line([SCALE_W, foot_y, W, foot_y], fill=RULE_C, width=1)
    date_f   = _load(_SANS_REG, 19)
    date_str = today.isoformat() if hasattr(today, "isoformat") else str(today)
    draw.text((CX, foot_y + 10), date_str, fill=MUTED, font=date_f)

    img.save(str(path), "PNG")
