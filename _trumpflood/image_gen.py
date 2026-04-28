"""Daily 1200x628 OG / share image for Trumpflood. Mirrors the visual
identity of the live page: zone-color top band, kicker, question +
conversational answer, big share %, vertical zone ladder, duotone-style
Trump portrait with rising water, date + URL footer.

Used as og:image and twitter:image. A new PNG is committed every run by
the GitHub Action (3x/day), so a LinkedIn share preview always reflects
the current zone, percentage and answer.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

# LinkedIn URL-preview: 1200x628 (~1.91:1)
W, H = 1200, 628

# Site palette (kept aligned with site_gen.py CSS variables).
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
ZONE_ORDER  = ["flooding", "soaked", "wet", "puddles", "dry"]  # top -> bottom
ZONE_LABELS = {"dry": "Dry", "puddles": "Puddles", "wet": "Wet",
               "soaked": "Soaked", "flooding": "Flooding"}

# Conversational answer per zone, mirrors site_gen.py _ZONE_ANSWERS.
ZONE_ANSWERS = {
    "dry":      "No Trump today.",
    "puddles":  "No, just puddles.",
    "wet":      "Well, it is getting wet.",
    "soaked":   "Almost. The zone is soaked.",
    "flooding": "Yes, he is.",
}

TRUMP_JPG = Path(__file__).parent.parent / "trumpflood" / "trump.jpg"

_SERIF_BOLD = [
    # Linux (GitHub Actions runner)
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
    # macOS (local dev)
    "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
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
    """Grayscale + contrast(1.05) portrait with zone-colour water overlay,
    mirroring the site's CSS filter + canvas animation."""
    src = Image.open(TRUMP_JPG).convert("RGB")

    scale    = photo_h / src.height
    scaled_w = int(src.width * scale)
    src      = src.resize((scaled_w, photo_h), Image.LANCZOS)
    off_x    = max(0, (scaled_w - photo_w) // 2)
    src      = src.crop((off_x, 0, off_x + photo_w, photo_h))

    src = ImageEnhance.Contrast(
        src.convert("L").convert("RGB")
    ).enhance(1.05)

    water_h = int(photo_h * water_pct)
    if water_h > 0:
        overlay = Image.new("RGBA", (photo_w, photo_h), (0, 0, 0, 0))
        od      = ImageDraw.Draw(overlay)
        r, g, b = zone_color
        fade    = min(water_h, 60)
        for row in range(water_h):
            alpha = int(200 * min(row, fade) / fade)
            od.line(
                [(0, photo_h - water_h + row), (photo_w, photo_h - water_h + row)],
                fill=(r, g, b, alpha),
            )
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
    answer = ZONE_ANSWERS.get(zone, "")

    # Layout constants
    BORDER  = 6     # top zone-color accent band
    SCALE_W = 72    # vertical zone-ladder width
    PHOTO_W = 300   # Trump portrait width
    PAD     = 52    # right-column inset
    FOOT_H  = 44    # footer height
    PX      = SCALE_W + PHOTO_W                # right edge of left block
    CX      = PX + PAD                         # right column left edge
    CR      = W - PAD                          # right column right edge
    CW      = CR - CX                          # right column width

    # Fonts
    kicker_f = _load(_SANS_BOLD,  18)
    title_f  = _load(_SERIF_BOLD, 40)
    answer_f = _load(_SERIF_BOLD, 70)
    pct_f    = _load(_SANS_BOLD,  108)
    pct_sym_f = _load(_SANS_BOLD, 60)
    label_f  = _load(_SANS_BOLD,  16)
    url_f    = _load(_SANS_REG,   16)
    band_f   = _load(_SANS_BOLD,  11)
    date_f   = _load(_SANS_REG,   17)

    # Top accent band in today's zone colour.
    draw.rectangle([0, 0, W, BORDER], fill=zc)

    # Vertical zone ladder on the left edge.
    body_h = H - BORDER
    band_h = body_h / len(ZONE_ORDER)
    for i, z in enumerate(ZONE_ORDER):
        color     = ZONE_COLORS[z]
        is_active = (z == zone)
        y0 = BORDER + int(i * band_h)
        y1 = BORDER + int((i + 1) * band_h)
        draw.rectangle(
            [0, y0, SCALE_W, y1],
            fill=color if is_active else _lighten(color, 55),
        )
        name = ZONE_LABELS[z]
        nw   = draw.textlength(name, font=band_f)
        draw.text(
            ((SCALE_W - nw) / 2, (y0 + y1) / 2 - 7),
            name,
            fill=WHITE if is_active else (155, 145, 135),
            font=band_f,
        )

    # Trump portrait with zone-coloured water rising to today's zone level.
    zone_idx  = ZONE_ORDER.index(zone) if zone in ZONE_ORDER else 0
    water_pct = (len(ZONE_ORDER) - zone_idx) / len(ZONE_ORDER)
    if TRUMP_JPG.exists():
        portrait = _trump_strip(PHOTO_W, H - BORDER, zc, water_pct)
        img.paste(portrait, (SCALE_W, BORDER))
    draw.line([PX, BORDER, PX, H], fill=RULE_C, width=1)

    # Right column content. Vertical layout, top-anchored.
    # Block heights are computed so the cluster sits centred between the
    # top accent and the footer rule, with a tight rhythm:
    #   kicker -> title -> answer -> big % -> label
    kicker  = "TRUMPFLOOD · BELGIAN NEWS MONITOR"
    title   = "Is Trump flooding the zone?"
    pct_str = f"{pct}"
    pct_sym = "%"
    sub_lbl = "share of Belgian news headlines today"

    title_lines = _wrap(draw, title, title_f, CW)
    answer_lines = _wrap(draw, answer, answer_f, CW)

    kicker_h    = _lh(kicker_f)
    title_h     = sum(_lh(title_f) + 6 for _ in title_lines) - 6
    answer_h    = sum(_lh(answer_f) + 6 for _ in answer_lines) - 6
    pct_h       = _lh(pct_f)
    label_h     = _lh(label_f)

    gap_kicker_to_title  = 16
    gap_title_to_answer  = 18
    gap_answer_to_pct    = 26
    gap_pct_to_label     = 12

    block_total = (
        kicker_h + gap_kicker_to_title +
        title_h + gap_title_to_answer +
        answer_h + gap_answer_to_pct +
        pct_h + gap_pct_to_label +
        label_h
    )

    avail_h = H - BORDER - FOOT_H
    y = BORDER + max(40, (avail_h - block_total) // 2)

    # Kicker
    draw.text((CX, y), kicker, fill=MUTED, font=kicker_f)
    y += kicker_h + gap_kicker_to_title

    # Title (serif, multi-line if needed)
    for line in title_lines:
        draw.text((CX, y), line, fill=INK, font=title_f)
        y += _lh(title_f) + 6
    y -= 6
    y += gap_title_to_answer

    # Answer (larger serif, ink colour)
    for line in answer_lines:
        draw.text((CX, y), line, fill=INK, font=answer_f)
        y += _lh(answer_f) + 6
    y -= 6
    y += gap_answer_to_pct

    # Big percentage in zone colour, with smaller % symbol in muted.
    pct_w     = draw.textlength(pct_str, font=pct_f)
    pct_sym_w = draw.textlength(pct_sym, font=pct_sym_f)
    # Vertical alignment: % symbol baseline matches the digits' baseline.
    pct_baseline_y = y + _lh(pct_f)
    sym_y = pct_baseline_y - _lh(pct_sym_f) - 6
    draw.text((CX, y), pct_str, fill=zc, font=pct_f)
    draw.text((CX + pct_w + 4, sym_y), pct_sym, fill=MUTED, font=pct_sym_f)
    y += pct_h + gap_pct_to_label

    # Subtitle label under the big number.
    draw.text((CX, y), sub_lbl.upper(), fill=MUTED, font=label_f)

    # Footer: date left, URL right, separator rule above.
    foot_y   = H - FOOT_H + 8
    date_str = today.isoformat() if hasattr(today, "isoformat") else str(today)
    draw.line([PX, foot_y - 8, W, foot_y - 8], fill=RULE_C, width=1)
    draw.text((CX, foot_y), date_str, fill=MUTED, font=date_f)
    url_text = "andriesfluit.be/trumpflood"
    uw = draw.textlength(url_text, font=url_f)
    draw.text((CR - uw, foot_y), url_text, fill=MUTED, font=url_f)

    img.save(str(path), "PNG")
