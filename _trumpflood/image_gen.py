from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# LinkedIn URL-preview: 1200×628 (≈1.91:1)
W, H = 1200, 628

# ── Site palette ─────────────────────────────────────────────────────────────
PAPER  = (245, 243, 238)
INK    = (10,  25,  41)
MUTED  = (107, 99,  86)
RULE_C = (216, 211, 197)
WHITE  = (255, 255, 255)

ZONE_COLORS = {
    "dry":      (200, 184, 154),
    "puddles":  (168, 196, 216),
    "wet":      (74,  127, 160),
    "soaked":   (30,  58,  95),
    "flooding": (176, 58,  46),
}
ZONE_ORDER  = ["flooding", "soaked", "wet", "puddles", "dry"]  # top → bottom
ZONE_LABELS = {"dry": "Dry", "puddles": "Puddles", "wet": "Wet",
               "soaked": "Soaked", "flooding": "Flooding"}

TRUMP_JPG = Path(__file__).parent.parent / "trumpflood" / "trump.jpg"

_SERIF_BOLD = [
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
]
_SANS_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
_SANS_REG = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
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
    """Crop trump.jpg to photo_w×photo_h with a zone-colour water overlay."""
    src      = Image.open(TRUMP_JPG).convert("RGB")
    scale    = photo_h / src.height
    scaled_w = int(src.width * scale)
    src      = src.resize((scaled_w, photo_h), Image.LANCZOS)
    off_x    = max(0, (scaled_w - photo_w) // 2)
    src      = src.crop((off_x, 0, off_x + photo_w, photo_h))

    # Solid zone-colour fill below water line, fading out near the surface.
    water_h = int(photo_h * water_pct)
    if water_h > 0:
        overlay = Image.new("RGBA", (photo_w, photo_h), (0, 0, 0, 0))
        od      = ImageDraw.Draw(overlay)
        r, g, b = zone_color
        fade    = min(water_h, 80)          # fade zone: top 80 px of water
        for row in range(water_h):
            if row < fade:
                alpha = int(200 * row / fade)   # 0 → 200 at water surface
            else:
                alpha = 200                      # fully opaque below
            od.line([(0, photo_h - water_h + row), (photo_w, photo_h - water_h + row)],
                    fill=(r, g, b, alpha))
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

    # ── Layout ───────────────────────────────────────────────────────────────
    BORDER  = 6
    SCALE_W = 72
    PHOTO_W = 300
    PAD     = 48
    FOOT_H  = 44
    PX      = SCALE_W + PHOTO_W   # photo right edge / content left boundary
    CX      = PX + PAD
    CR      = W - PAD
    CW      = CR - CX

    # ── Fonts ─────────────────────────────────────────────────────────────────
    site_f  = _load(_SANS_BOLD,  18)   # "Is Trump flooding the zone?"
    lbl_f   = _load(_SERIF_BOLD, 62)   # zone label
    url_f   = _load(_SANS_REG,   16)
    band_f  = _load(_SANS_BOLD,  11)
    date_f  = _load(_SANS_REG,   17)

    # ── Measure content for vertical centering ────────────────────────────────
    label_lines = _wrap(draw, label, lbl_f, CW)
    lbl_h       = sum(_lh(lbl_f) + 6 for _ in label_lines) - 6

    CONTENT_H = _lh(site_f) + 16 + 1 + 20 + lbl_h
    BODY_H    = H - BORDER - FOOT_H
    y         = BORDER + max(24, (BODY_H - CONTENT_H) // 2)

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

    # ── Trump portrait with water ─────────────────────────────────────────────
    zone_idx  = ZONE_ORDER.index(zone) if zone in ZONE_ORDER else 0
    water_pct = (len(ZONE_ORDER) - zone_idx) / len(ZONE_ORDER)
    if TRUMP_JPG.exists():
        portrait = _trump_strip(PHOTO_W, H - BORDER, zc, water_pct)
        img.paste(portrait, (SCALE_W, BORDER))
    draw.line([PX, BORDER, PX, H], fill=RULE_C, width=1)

    # ── Content ───────────────────────────────────────────────────────────────

    # Site title
    draw.text((CX, y), "Is Trump flooding the zone?", fill=INK, font=site_f)
    y += _lh(site_f) + 16

    # Rule
    draw.line([CX, y, CR, y], fill=RULE_C, width=1)
    y += 20

    # Zone label (large serif)
    for line in label_lines:
        draw.text((CX, y), line, fill=INK, font=lbl_f)
        y += _lh(lbl_f) + 6

    # ── Footer ────────────────────────────────────────────────────────────────
    foot_y   = H - FOOT_H + 8
    date_str = today.isoformat() if hasattr(today, "isoformat") else str(today)
    draw.line([PX, foot_y - 8, W, foot_y - 8], fill=RULE_C, width=1)
    draw.text((CX, foot_y), date_str, fill=MUTED, font=date_f)
    uw = draw.textlength("andriesfluit.be/trumpflood", font=url_f)
    draw.text((CR - uw, foot_y), "andriesfluit.be/trumpflood", fill=MUTED, font=url_f)

    img.save(str(path), "PNG")
