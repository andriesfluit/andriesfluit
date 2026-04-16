from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH = HEIGHT = 1080
BAR_HEIGHT = 60
BAR_MARGIN = 80
START = (0xAE, 0xD6, 0xF1)
END = (0x1A, 0x52, 0x76)

FONT_BOLD_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]
FONT_REG_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def _load(paths, size):
    for p in paths:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _interp(pct):
    t = max(0.0, min(1.0, pct / 100.0))
    return tuple(int(START[i] + (END[i] - START[i]) * t) for i in range(3))


def _wrap(draw, text, font, max_width):
    words = text.split()
    lines, line = [], ""
    for w in words:
        cand = (line + " " + w).strip()
        if draw.textlength(cand, font=font) <= max_width:
            line = cand
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def generate_image(path, label, today, pct, total):
    img = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    label_font = _load(FONT_BOLD_CANDIDATES, 80)
    sub_font = _load(FONT_REG_CANDIDATES, 32)

    max_w = WIDTH - 160
    lines = _wrap(draw, label, label_font, max_w)
    bbox = label_font.getbbox("Ay")
    line_h = bbox[3] - bbox[1]
    total_h = line_h * len(lines) + (len(lines) - 1) * 10
    y = int(HEIGHT * 0.40) - total_h // 2
    for line in lines:
        w = draw.textlength(line, font=label_font)
        draw.text(((WIDTH - w) / 2, y), line, fill="black", font=label_font)
        y += line_h + 10

    sub = f"{today.isoformat()}  \u00b7  {pct}% of {total} headlines mention Trump"
    sw = draw.textlength(sub, font=sub_font)
    draw.text(((WIDTH - sw) / 2, y + 30), sub, fill=(120, 120, 120), font=sub_font)

    bar_y0 = HEIGHT - BAR_MARGIN - BAR_HEIGHT
    bar_y1 = HEIGHT - BAR_MARGIN
    full_w = WIDTH - 2 * BAR_MARGIN
    bar_w = int(full_w * max(0.0, min(1.0, pct / 100.0)))
    color = _interp(pct)
    draw.rectangle([BAR_MARGIN, bar_y0, BAR_MARGIN + bar_w, bar_y1], fill=color)

    img.save(path, "PNG")
