#!/bin/bash
# SessionStart hook: load Andries' claudeOS memory from a private GitHub repo.
# - Local sessions: skip (Andries' ~/Desktop/claudeOS/ is the source of truth there).
# - Cloud sessions (Claude Code on the web): clone the private mirror and inject
#   its contents into the session context via `additionalContext`.
#
# Ordering matters: the preview Claude sees is the first ~2KB of the output.
# Identity and business files come first so the model has the real facts about
# Andries, akkanto and Bikon before anything else. Skill templates under
# .claude/commands/ are emitted as a one-line index, not in full, to avoid
# pushing the relevant context out of the preview. Full skill content is read
# on-demand when a skill is actually invoked.
#
# Requires env var CLAUDEOS_TOKEN (a GitHub PAT with `repo` scope) configured
# in the cloud environment settings. Configure under: Settings → Environments
# → (this environment) → Environment variables.

set -euo pipefail

REPO="andriesfluit/claudeos"
CLONE_DIR="${HOME}/.claudeos"

emit() {
  local ctx="$1"
  python3 -c '
import json, sys
ctx = sys.stdin.read()
out = {"hookSpecificOutput": {"hookEventName": "SessionStart"}}
if ctx.strip():
    out["hookSpecificOutput"]["additionalContext"] = ctx
print(json.dumps(out))
' <<< "$ctx"
}

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  emit ""
  exit 0
fi

if [ -z "${CLAUDEOS_TOKEN:-}" ]; then
  emit "claudeOS memory niet geladen: CLAUDEOS_TOKEN ontbreekt in de cloud-environment. Voeg 'm toe onder Settings → Environments → Environment variables."
  exit 0
fi

if [ -d "$CLONE_DIR/.git" ]; then
  git -C "$CLONE_DIR" fetch --quiet origin
  git -C "$CLONE_DIR" reset --hard --quiet origin/HEAD
else
  rm -rf "$CLONE_DIR"
  git clone --quiet --depth 1 "https://x-access-token:${CLAUDEOS_TOKEN}@github.com/${REPO}.git" "$CLONE_DIR"
fi

# Files loaded in full, in this exact order. They describe who Andries is and
# what akkanto and Bikon actually are, so they belong at the top.
PRIORITY_FILES=(
  "USER.md"
  "IDENTITY.md"
  "SOUL.md"
  "MEMORY.md"
  "Business/akkanto.md"
  "Business/bikon.md"
)

emit_file() {
  local rel="$1"
  local abs="$CLONE_DIR/$rel"
  if [ -f "$abs" ]; then
    echo "---"
    echo "## ${rel}"
    echo
    cat "$abs"
    echo
  fi
}

# One-line summary of a skill: H1 title (or filename) + first prose line.
skill_summary() {
  local f="$1"
  local rel="${f#$CLONE_DIR/}"
  local title desc
  title=$(grep -m1 '^# ' "$f" | sed 's/^# //' || true)
  [ -z "$title" ] && title=$(basename "$f" .md)
  desc=$(awk '/^# /{found=1; next} found && NF && !/^#/ && !/^---/ {print; exit}' "$f")
  if [ -n "$desc" ]; then
    echo "- \`${rel}\` — **${title}**: ${desc}"
  else
    echo "- \`${rel}\` — **${title}**"
  fi
}

CONTEXT=$(
  {
    echo "# Andries' persoonlijke memory (claudeOS)"
    echo "Bron: github.com/${REPO}"
    echo
    echo "Volgorde: (1) identity + business eerst, (2) overige memory, (3) skill-index. Volledige skill-inhoud lees je on-demand via Read uit \`${CLONE_DIR}/.claude/commands/<naam>.md\`."
    echo

    for rel in "${PRIORITY_FILES[@]}"; do
      emit_file "$rel"
    done

    EXCLUDE_PATTERN=$(printf '|^%s$' "${PRIORITY_FILES[@]}")
    EXCLUDE_PATTERN="${EXCLUDE_PATTERN:1}"

    find "$CLONE_DIR" -type f -name '*.md' \
      -not -path '*/.git/*' \
      -not -path "$CLONE_DIR/.claude/commands/*" \
      | sort | while read -r f; do
        rel="${f#$CLONE_DIR/}"
        if ! echo "$rel" | grep -qE "$EXCLUDE_PATTERN"; then
          echo "---"
          echo "## ${rel}"
          echo
          cat "$f"
          echo
        fi
      done

    if [ -d "$CLONE_DIR/.claude/commands" ]; then
      echo "---"
      echo "## Skill-index (.claude/commands/)"
      echo
      echo "Lees de volledige skill met \`Read\` wanneer je hem effectief gaat uitvoeren. Hieronder enkel naam + één-regel-beschrijving."
      echo
      find "$CLONE_DIR/.claude/commands" -type f -name '*.md' | sort | while read -r f; do
        skill_summary "$f"
      done
      echo
    fi
  }
)

emit "$CONTEXT"
