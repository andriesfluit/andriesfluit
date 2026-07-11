#!/bin/bash
# Build a single Markdown document from claudeOS sources and upload it to Google
# Drive via rclone. Idempotent, non-interactive. Same concatenation shape as
# .claude/hooks/session-start.sh so the chat-side and cloud-session-side stay
# consistent.

set -euo pipefail

SRC="${CLAUDEOS_SRC:-$HOME/Documents/Claude/ClaudeOS}"
REMOTE="${RCLONE_REMOTE:-gdrive}"
DEST_NAME="${CLAUDEOS_DRIVE_NAME:-ClaudeOS Context.md}"
OUT="${CLAUDEOS_OUT:-/tmp/claudeos-context.md}"

if [ ! -d "$SRC" ]; then
  echo "claudeOS bron niet gevonden: $SRC" >&2
  exit 1
fi

if ! command -v rclone >/dev/null 2>&1; then
  echo "rclone ontbreekt. Installeer met: brew install rclone" >&2
  exit 1
fi

{
  echo "# Andries' persoonlijke memory (claudeOS)"
  echo "Bron: ${SRC}"
  echo "Gegenereerd: $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo
  find "$SRC" -type f -name '*.md' -not -path '*/.git/*' | sort | while read -r f; do
    rel="${f#$SRC/}"
    echo "---"
    echo "## ${rel}"
    echo
    cat "$f"
    echo
  done
} > "$OUT"

rclone copyto "$OUT" "${REMOTE}:${DEST_NAME}" \
  --drive-use-trash=false \
  --quiet

echo "OK: $(date '+%Y-%m-%d %H:%M:%S') -> ${REMOTE}:${DEST_NAME} ($(wc -c < "$OUT") bytes)"
