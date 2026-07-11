"""Daily 1200x628 OG / share image for Trumpflood. Mirrors the visual
identity of the live page: thin top accent band, kicker, question h1,
conversational answer, big share % with label, sub-line with absolute
counts, horizontal zone ladder, duotone-mapped Trump portrait on the
right, date + URL footer.

Used as og:image and twitter:image. A new PNG is committed every run by
the GitHub Action (3x/day), so a LinkedIn share preview always reflects
the current zone, percentage and answer.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# LinkedIn URL-preview: 1200x628 (~1.91:1)
W, H = 1200, 628

# Site palette (kept aligned with site_gen.py CSS variables).
PAPER = (245, 243, 238)
INK   = (10, 25, 41)
MUTED = (107, 99, 86)
RULE  = (216, 211, 197)

ZONE_COLORS = {
    "dry":      (200, 184, 154),
    "puddles":  (168, 196, 216),
    "wet":      (74,  127, 160),
    "soaked":   (30,  58,  95),
    "flooding": (176, 58,  46),
}

# Horizontal ladder, left -> right (matches the site's data-hero ladder).
ZONE_ORDER_LTR = ["dry", "puddles", "wet", "soaked", "flooding"]
ZONE_LABELS    = {"dry": "Dry", "puddles": "Puddles", "wet": "Wet",
                  "soaked": "Soaked", "flooding": "Flooding"}

# Conversational answer per zone (matches site_gen.py _ZONE_ANSWERS).
ZONE_ANSWERS = {
    "dry":      "No Trump today.",
    "puddles":  "No, just puddles.",
    "wet":      "Well, it is getting wet.",
    "soaked":   "Almost. The zone is soaked.",
    "flooding": "Yes, he is.",
}

# Duotone shadow / highlight pairs (match site_gen.py _ZONE_DUOTONE).
ZONE_DUOTONE = {
    "dry":      ((106, 90, 62),  (247, 238, 216)),
    "puddles":  ((44,  70, 88),  (240, 245, 250)),
    "wet":      ((28,  53, 72),  (236, 243, 248)),
    "soaked":   ((10,  26, 46),  (230, 238, 247)),
    "flooding": ((74,  19, 16),  (253, 234, 226)),
}

TRUMP_JPG = Path(__file__).parent.parent / "trumpflood" / "trump.jpg"

_SERIF_BOLD = [
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
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
    words, lines, line = text.split(), [], ""
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


def _duotone(img, shadow_rgb, highlight_rgb):
    """Luminance-based duotone: convert to grayscale, then map each
    intensity to a colour interpolated between shadow (dark) and
    highlight (light). Matches the SVG feComponentTransfer filter on
    the live page so the OG portrait reads as the same treatment."""
    gray = img.convert("L")
    lut_r = [int(shadow_rgb[0] + (highlight_rgb[0] - shadow_rgb[0]) * (i / 255)) for i in range(256)]
    lut_g = [int(shadow_rgb[1] + (highlight_rgb[1] - shadow_rgb[1]) * (i / 255)) for i in range(256)]
    lut_b = [int(shadow_rgb[2] + (highlight_rgb[2] - shadow_rgb[2]) * (i / 255)) for i in range(256)]
    return Image.merge("RGB", (
        gray.point(lut_r),
        gray.point(lut_g),
        gray.point(lut_b),
    ))


def _portrait(target_w, target_h, zone):
    """Crop, resize and duotone the portrait so it slots into the right
    column of the OG card."""
    src = Image.open(TRUMP_JPG).convert("RGB")
    scale = max(target_w / src.width, target_h / src.height)
    new_w, new_h = int(src.width * scale), int(src.height * scale)
    src = src.resize((new_w, new_h), Image.LANCZOS)
    off_x = max(0, (new_w - target_w) // 2)
    src = src.crop((off_x, 0, off_x + target_w, target_h))
    shadow, highlight = ZONE_DUOTONE.get(zone, ZONE_DUOTONE["dry"])
    return _duotone(src, shadow, highlight)


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

    # ── Layout ────────────────────────────────────────────────────────
    BORDER     = 6
    PAD_X      = 56
    PAD_TOP    = 36
    FOOT_H     = 50
    PORTRAIT_W = 280
    PORTRAIT_H = 350
    GAP        = 36
    LX         = PAD_X
    RIGHT_X    = W - PAD_X - PORTRAIT_W
    LEFT_W     = RIGHT_X - LX - GAP

    # ── Fonts ─────────────────────────────────────────────────────────
    kicker_f  = _load(_SANS_BOLD,  16)
    title_f   = _load(_SERIF_BOLD, 38)
    answer_f  = _load(_SERIF_BOLD, 64)
    pct_f     = _load(_SANS_BOLD,  102)
    pct_sym_f = _load(_SANS_BOLD,  56)
    label_f   = _load(_SANS_BOLD,  14)
    sub_f     = _load(_SANS_REG,   16)
    band_f    = _load(_SANS_BOLD,  11)
    foot_f    = _load(_SANS_REG,   15)

    # ── Top accent band in today's zone colour ────────────────────────
    draw.rectangle([0, 0, W, BORDER], fill=zc)

    # ── Left column: text content (matches site reading order) ─────────
    y = BORDER + PAD_TOP

    # Kicker
    kicker = "TRUMPFLOOD · BELGIAN NEWS MONITOR"
    # Letter-spacing approximation: render with tracked spacing.
    draw.text((LX, y), kicker, fill=MUTED, font=kicker_f)
    y += _lh(kicker_f) + 18

    # Question h1 (serif). Wrap if needed; usually fits one line.
    title = "Is Trump flooding the zone?"
    for line in _wrap(draw, title, title_f, LEFT_W):
        draw.text((LX, y), line, fill=INK, font=title_f)
        y += _lh(title_f) + 4
    y += 10

    # Conversational answer (larger serif, dominant).
    for line in _wrap(draw, answer, answer_f, LEFT_W):
        draw.text((LX, y), line, fill=INK, font=answer_f)
        y += _lh(answer_f) + 4
    y += 16

    # Big percentage in zone colour with smaller % glyph in muted.
    pct_str = f"{pct}"
    pct_w   = draw.textlength(pct_str, font=pct_f)
    pct_sym_w = draw.textlength("%", font=pct_sym_f)
    pct_baseline = y + _lh(pct_f)
    sym_y = pct_baseline - _lh(pct_sym_f) - 4
    draw.text((LX, y), pct_str, fill=zc, font=pct_f)
    draw.text((LX + pct_w + 4, sym_y), "%", fill=MUTED, font=pct_sym_f)
    y += _lh(pct_f) + 8

    # Label under the % (small uppercase muted).
    draw.text((LX, y), "SHARE OF BELGIAN NEWS HEADLINES TODAY",
              fill=MUTED, font=label_f)
    y += _lh(label_f) + 16

    # Sub-line with absolute counts.
    sub = f"{trump_count} of {total} headlines name Trump."
    draw.text((LX, y), sub, fill=INK, font=sub_f)
    y += _lh(sub_f) + 28

    # ── Horizontal zone ladder (Dry → Flooding) ─────────────────────────
    LADDER_W = LEFT_W
    ladder_top = y
    seg_w = LADDER_W / len(ZONE_ORDER_LTR)
    for i, key in enumerate(ZONE_ORDER_LTR):
        is_active = (key == zone)
        seg_x = LX + i * seg_w
        bar_h = 12 if is_active else 6
        bar_y = ladder_top + (12 - bar_h) // 2
        bar_color = ZONE_COLORS[key] if is_active else RULE
        draw.rectangle(
            [seg_x, bar_y, seg_x + seg_w - 4, bar_y + bar_h],
            fill=bar_color,
        )
        # Label below
        name = ZONE_LABELS[key]
        nw   = draw.textlength(name, font=band_f)
        lbl_x = seg_x + (seg_w - 4 - nw) / 2
        draw.text(
            (lbl_x, ladder_top + 18),
            name,
            fill=INK if is_active else MUTED,
            font=band_f,
        )

    # ── Right column: duotone Trump portrait ──────────────────────────
    if TRUMP_JPG.exists():
        portrait = _portrait(PORTRAIT_W, PORTRAIT_H, zone)
        # Vertical position: align the portrait roughly with the
        # answer + big % cluster on the left so the OG reads as a single
        # composed block, not text-on-top + image-on-bottom.
        py = BORDER + PAD_TOP + 40
        img.paste(portrait, (RIGHT_X, py))

    # ── Footer: divider rule, date left, URL right ────────────────────
    foot_y_rule = H - FOOT_H
    draw.line([PAD_X, foot_y_rule, W - PAD_X, foot_y_rule],
              fill=RULE, width=1)
    foot_y = foot_y_rule + 14
    date_str = today.isoformat() if hasattr(today, "isoformat") else str(today)
    draw.text((PAD_X, foot_y), date_str, fill=MUTED, font=foot_f)
    url_text = "andriesfluit.be/trumpflood"
    uw = draw.textlength(url_text, font=foot_f)
    draw.text((W - PAD_X - uw, foot_y), url_text, fill=MUTED, font=foot_f)

    img.save(str(path), "PNG")
