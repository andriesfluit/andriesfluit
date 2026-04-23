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

TRUMP_JPG = Path(__file__).parent.parent / "trumpflood" / "trump.jpg"

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


def _trump_strip(photo_w, photo_h, zone_color, water_pct):
    """Return a photo_w × photo_h crop of trump.jpg with a zone-colour water
    overlay rising from the bottom to water_pct of the image height."""
    src = Image.open(TRUMP_JPG).convert("RGB")
    # Scale so height fills photo_h, then center-crop to photo_w.
    scale   = photo_h / src.height
    scaled_w = int(src.width * scale)
    src     = src.resize((scaled_w, photo_h), Image.LANCZOS)
    off_x   = max(0, (scaled_w - photo_w) // 2)
    src     = src.crop((off_x, 0, off_x + photo_w, photo_h))

    # Water tint: semi-transparent zone-colour wash rising from bottom.
    water_h = int(photo_h * water_pct)
    if water_h > 0:
        overlay = Image.new("RGBA", (photo_w, photo_h), (0, 0, 0, 0))
        od      = ImageDraw.Draw(overlay)
        r, g, b = zone_color
        # Gradient: fully opaque at bottom, fading to transparent at water line.
        for row in range(water_h):
            alpha = int(140 * (1 - row / water_h))  # 140 → 0 top-to-bottom
            y_pos = photo_h - water_h + row
            od.line([(0, y_pos), (photo_w, y_pos)], fill=(r, g, b, alpha))
        src = Image.alpha_composite(src.convert("RGBA"), overlay).convert("RGB")

    return src


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
    BORDER  = 6
    SCALE_W = 72    # left zone-scale column
    PHOTO_W = 252   # Trump portrait strip
    PAD     = 40    # horizontal padding for text
    FOOT_H  = 38
    PX      = SCALE_W + PHOTO_W          # photo right edge
    CX      = PX + PAD                   # content left x
    CR      = W - PAD                    # content right x
    CW      = CR - CX                    # content width

    # ── Load all fonts up front ───────────────────────────────────────────────
    title_f = _load(_SANS_BOLD,  21)
    url_f   = _load(_SANS_REG,   16)
    lbl_f   = _load(_SERIF_BOLD, 52)
    pct_f   = _load(_SERIF_BOLD, 90)
    sub_f   = _load(_SANS_REG,   20)
    stat_f  = _load(_SANS_REG,   20)
    band_f  = _load(_SANS_BOLD,  11)
    date_f  = _load(_SANS_REG,   18)

    # ── Pre-compute content (needed for height measurement) ───────────────────
    label_lines = _wrap(draw, label, lbl_f, CW)

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

    # ── Measure content block height for vertical centering ───────────────────
    lbl_h     = sum(_lh(lbl_f) + 4 for _ in label_lines) - 4
    stats_h   = sum(_lh(stat_f) + 10 for _ in stats) - 10 if stats else 0
    pct_row_h = max(_lh(pct_f), stats_h)

    CONTENT_H = (
        _lh(title_f) + 14 +
        1 + 17 +
        lbl_h + 14 +
        1 + 15 +
        pct_row_h +
        8 + _lh(sub_f)
    )
    BODY_H = H - BORDER - FOOT_H
    y = BORDER + max(20, (BODY_H - CONTENT_H) // 2)

    # ── Top accent border ─────────────────────────────────────────────────────
    draw.rectangle([0, 0, W, BORDER], fill=zc)

    # ── Zone scale ────────────────────────────────────────────────────────────
    body_h = H - BORDER
    band_h = body_h / len(ZONE_ORDER)
    for i, z in enumerate(ZONE_ORDER):
        color     = ZONE_COLORS[z]
        is_active = (z == zone)
        y0 = BORDER + int(i * band_h)
        y1 = BORDER + int((i + 1) * band_h)
        draw.rectangle([0, y0, SCALE_W, y1],
                       fill=color if is_active else _lighten(color, 55))
        name = ZONE_LABELS[z]
        nw   = draw.textlength(name, font=band_f)
        draw.text(((SCALE_W - nw) / 2, (y0 + y1) / 2 - 7), name,
                  fill=WHITE if is_active else (155, 145, 135), font=band_f)

    # ── Trump portrait ────────────────────────────────────────────────────────
    # Water level: top of active zone band (same logic as the site's water-target).
    zone_idx   = ZONE_ORDER.index(zone) if zone in ZONE_ORDER else 0
    # Zones are ordered top→bottom, so active band starts at zone_idx/5 from top.
    # Water rises from bottom → water_pct = fraction from bottom = (5-zone_idx)/5.
    water_pct  = (len(ZONE_ORDER) - zone_idx) / len(ZONE_ORDER)
    if TRUMP_JPG.exists():
        portrait = _trump_strip(PHOTO_W, H - BORDER, zc, water_pct)
        img.paste(portrait, (SCALE_W, BORDER))
    # Thin separator between portrait and content
    draw.line([PX, BORDER, PX, H], fill=RULE_C, width=1)

    # ── Content — vertically centered ─────────────────────────────────────────

    # Title + URL
    draw.text((CX, y), "Is Trump flooding the zone?", fill=INK, font=title_f)
    uw = draw.textlength("andriesfluit.be/trumpflood", font=url_f)
    draw.text((CR - uw, y + 3), "andriesfluit.be/trumpflood", fill=MUTED, font=url_f)
    y += _lh(title_f) + 14

    draw.line([CX, y, CR, y], fill=RULE_C, width=1)
    y += 18

    # Zone label
    for line in label_lines:
        draw.text((CX, y), line, fill=INK, font=lbl_f)
        y += _lh(lbl_f) + 4
    y -= 4
    y += 14

    draw.line([CX, y, CR, y], fill=RULE_C, width=1)
    y += 16

    # Percentage + stats
    pct_str = f"{pct}%"
    pct_w   = draw.textlength(pct_str, font=pct_f)
    draw.text((CX, y), pct_str, fill=zc, font=pct_f)

    stat_x, stat_y = CX + int(pct_w) + 32, y + 8
    for s in stats:
        draw.text((stat_x, stat_y), s, fill=MUTED, font=stat_f)
        stat_y += _lh(stat_f) + 10

    y += _lh(pct_f) + 8
    draw.text((CX, y), f"{trump_count} of {total} Belgian headlines name Trump",
              fill=MUTED, font=sub_f)

    # ── Footer ────────────────────────────────────────────────────────────────
    foot_y   = H - FOOT_H
    date_str = today.isoformat() if hasattr(today, "isoformat") else str(today)
    draw.line([PX, foot_y, W, foot_y], fill=RULE_C, width=1)
    draw.text((CX, foot_y + 10), date_str, fill=MUTED, font=date_f)

    img.save(str(path), "PNG")
