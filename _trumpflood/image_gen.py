from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W = H = 1080

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
    "dry":      "Dry",
    "puddles":  "Puddles",
    "wet":      "Wet",
    "soaked":   "Soaked",
    "flooding": "Flooding",
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


def _lighten(color, amount=60):
    return tuple(min(255, c + amount) for c in color)


def _line_h(font):
    bb = font.getbbox("Ay")
    return bb[3] - bb[1]


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

    # ── Layout constants ─────────────────────────────────────────────────────
    HDR_H   = 130          # top colored header bar
    FOOT_H  = 62           # bottom footer strip
    SCALE_W = 110          # left zone-scale column
    BODY_Y0 = HDR_H
    BODY_Y1 = H - FOOT_H
    BODY_H  = BODY_Y1 - BODY_Y0   # 888 px
    CX      = SCALE_W + 54        # content left x
    CR      = W - 50              # content right x
    CW      = CR - CX             # content width  (~866 px)

    # ── Header bar ───────────────────────────────────────────────────────────
    draw.rectangle([0, 0, W, HDR_H], fill=zc)

    title_f = _load(_SANS_BOLD, 34)
    title   = "IS TRUMP FLOODING THE ZONE?"
    tw      = draw.textlength(title, font=title_f)
    draw.text(((W - tw) / 2, 22), title, fill=WHITE, font=title_f)

    url_f = _load(_SANS_REG, 20)
    url   = "andriesfluit.be/trumpflood"
    uw    = draw.textlength(url, font=url_f)
    draw.text(((W - uw) / 2, 74), url, fill=(220, 215, 210), font=url_f)

    # ── Zone scale (left column, top → bottom = Flooding → Dry) ─────────────
    band_h    = BODY_H / len(ZONE_ORDER)
    band_f    = _load(_SANS_BOLD, 12)

    for i, z in enumerate(ZONE_ORDER):
        color     = ZONE_COLORS[z]
        is_active = (z == zone)
        y0 = BODY_Y0 + int(i * band_h)
        y1 = BODY_Y0 + int((i + 1) * band_h)

        fill = color if is_active else _lighten(color, 60)
        draw.rectangle([0, y0, SCALE_W, y1], fill=fill)

        name = ZONE_LABELS[z]
        nw   = draw.textlength(name, font=band_f)
        cy   = (y0 + y1) / 2 - 7
        tc   = WHITE if is_active else (160, 150, 140)
        draw.text(((SCALE_W - nw) / 2, cy), name, fill=tc, font=band_f)

    # Separator between scale and content
    draw.line([SCALE_W, BODY_Y0, SCALE_W, BODY_Y1], fill=RULE_C, width=1)

    # ── Main content ─────────────────────────────────────────────────────────
    y = BODY_Y0 + 60

    # Zone label (serif bold, large)
    lbl_f = _load(_SERIF_BOLD, 64)
    lines = _wrap(draw, label, lbl_f, CW)
    lh    = _line_h(lbl_f)
    for line in lines:
        draw.text((CX, y), line, fill=INK, font=lbl_f)
        y += lh + 6
    y += 22

    # Rule
    draw.line([CX, y, CR, y], fill=RULE_C, width=1)
    y += 32

    # Percentage (serif bold, very large, zone color)
    pct_f   = _load(_SERIF_BOLD, 148)
    pct_str = f"{pct}%"
    draw.text((CX, y), pct_str, fill=zc, font=pct_f)
    y += _line_h(pct_f) + 4

    # Sub-line: X of Y headlines
    sub_f = _load(_SANS_REG, 26)
    sub   = f"{trump_count} of {total} Belgian headlines name Trump"
    draw.text((CX, y), sub, fill=MUTED, font=sub_f)
    y += _line_h(sub_f) + 22

    # Rule
    draw.line([CX, y, CR, y], fill=RULE_C, width=1)
    y += 24

    # Stats (up to 3 lines)
    stat_f = _load(_SANS_REG, 25)
    if rank and n_people:
        s = f"Rank #{rank} of {n_people} named figures"
        if dominance is not None and dominance > 0:
            s += f"  ·  {dominance}× vs. rest combined"
        draw.text((CX, y), s, fill=MUTED, font=stat_f)
        y += _line_h(stat_f) + 10
    if breadth and core_outlets_active:
        n_out = int(round(breadth * core_outlets_active))
        draw.text(
            (CX, y),
            f"In {n_out} of {core_outlets_active} national outlets",
            fill=MUTED, font=stat_f,
        )
        y += _line_h(stat_f) + 10
    if rival_label and rival_count:
        draw.text(
            (CX, y),
            f"Next up: {rival_label} ({rival_count})",
            fill=MUTED, font=stat_f,
        )

    # ── Footer ───────────────────────────────────────────────────────────────
    draw.line([0, BODY_Y1, W, BODY_Y1], fill=RULE_C, width=1)
    date_f   = _load(_SANS_REG, 21)
    date_str = today.isoformat() if hasattr(today, "isoformat") else str(today)
    draw.text((CX, BODY_Y1 + 18), date_str, fill=MUTED, font=date_f)

    img.save(str(path), "PNG")
