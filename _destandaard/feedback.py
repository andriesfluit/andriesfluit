"""The feedback loop.

Two flat files in data/ close the loop between digests:

  history.jsonl   one line per shown item, written every run. Lets a feedback
                  handle (e.g. "0626-a3") be resolved back to its title,
                  rubriek and tier (kern vs verrassing) later.

  feedback.md     Andries appends lines like:
                      0626-a3 + meer van dit soort duiding
                      0626-v1 -
                  (handle, then + or -, then an optional free-text note.)

On the next run we read feedback.md, join it with history, and build a compact
"geleerde voorkeuren" text block that is handed to the editor model. That block
steers the KERN selection and the quality bar — but NOT the size or diversity
of the verrassing section. The anti-echo-chamber guarantee lives in the prompt
(digest.py): negative feedback on a surprise topic makes the model pick a
*different* surprise, never shrink the surprise quota.
"""

import json
import logging
import re
from collections import Counter

logger = logging.getLogger(__name__)

HISTORY_FILE = "history.jsonl"
FEEDBACK_FILE = "feedback.md"

_FEEDBACK_LINE = re.compile(r"^\s*(\d{4}-[av]\d+)\s*([+-])\s*(.*?)\s*$")

# Only fold in the most recent feedback so the prompt stays bounded and the
# model tracks evolving taste rather than the entire history.
_MAX_FEEDBACK_ITEMS = 60


def record_shown(data_dir, date, kern, verrassing):
    """Append one history line per shown item. `kern`/`verrassing` are lists of
    dicts that already carry a `handle` and the underlying article fields."""
    path = data_dir / HISTORY_FILE
    rows = []
    for tier, items in (("kern", kern), ("verrassing", verrassing)):
        for it in items:
            rows.append(json.dumps({
                "date": date,
                "handle": it["handle"],
                "uid": it["uid"],
                "title": it["title"],
                "rubriek": it["rubriek"],
                "tier": tier,
            }, ensure_ascii=False))
    if rows:
        with path.open("a", encoding="utf-8") as f:
            f.write("\n".join(rows) + "\n")
    logger.info("recorded %d shown items to %s", len(rows), path.name)


def _load_history(data_dir):
    path = data_dir / HISTORY_FILE
    by_handle = {}
    if not path.exists():
        return by_handle
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            by_handle[rec["handle"]] = rec
        except (json.JSONDecodeError, KeyError):
            continue
    return by_handle


def load_feedback_context(data_dir):
    """Return a human-readable Dutch block summarising prior feedback, or "".

    Resolves each feedback handle through history so the model sees the title
    and rubriek it reacted to, plus an aggregate per-rubriek tally."""
    fb_path = data_dir / FEEDBACK_FILE
    if not fb_path.exists():
        return ""

    history = _load_history(data_dir)
    likes, dislikes = [], []
    rubriek_signal = Counter()

    in_fence = False
    for line in fb_path.read_text(encoding="utf-8").splitlines():
        # Skip fenced code blocks so the example lines in the template are not
        # parsed as real feedback.
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _FEEDBACK_LINE.match(line)
        if not m:
            continue
        handle, sign, note = m.group(1), m.group(2), m.group(3)
        rec = history.get(handle, {})
        title = rec.get("title", f"(onbekend item {handle})")
        rubriek = rec.get("rubriek", "?")
        entry = {"title": title, "rubriek": rubriek, "note": note}
        if sign == "+":
            likes.append(entry)
            rubriek_signal[rubriek] += 1
        else:
            dislikes.append(entry)
            rubriek_signal[rubriek] -= 1

    if not likes and not dislikes:
        return ""

    likes = likes[-_MAX_FEEDBACK_ITEMS:]
    dislikes = dislikes[-_MAX_FEEDBACK_ITEMS:]

    out = ["GELEERDE VOORKEUREN (uit eerdere feedback van Andries):"]
    if likes:
        out.append("\nWaardeerde hij (👍):")
        for e in likes:
            note = f" — \"{e['note']}\"" if e["note"] else ""
            out.append(f"  · [{e['rubriek']}] {e['title']}{note}")
    if dislikes:
        out.append("\nVond hij minder interessant (👎):")
        for e in dislikes:
            note = f" — \"{e['note']}\"" if e["note"] else ""
            out.append(f"  · [{e['rubriek']}] {e['title']}{note}")

    pos = [r for r, n in rubriek_signal.items() if n > 0]
    neg = [r for r, n in rubriek_signal.items() if n < 0]
    if pos or neg:
        out.append("\nNetto signaal per rubriek:")
        if pos:
            out.append("  meer interesse in: " + ", ".join(sorted(pos)))
        if neg:
            out.append("  minder interesse in: " + ", ".join(sorted(neg)))

    out.append(
        "\nGebruik dit ALLEEN om de KERN-selectie en de kwaliteitslat scherper "
        "te stellen. Laat het de VERRASSING-sectie niet krimpen of naar zijn "
        "voorkeuren toetrekken — dat is precies de echokamer die we vermijden."
    )
    return "\n".join(out)
