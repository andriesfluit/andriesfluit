#!/bin/bash
# SessionStart hook: load Andries' claudeOS memory from a private GitHub repo.
# - Local sessions: skip (Andries' ~/Desktop/claudeOS/ is the source of truth there).
# - Cloud sessions (Claude Code on the web): clone the private mirror and inject
#   its contents into the session context via `additionalContext`.
#
# Requires env var CLAUDEOS_TOKEN (a GitHub PAT with `repo` scope) configured
# in the cloud environment settings. Configure under: Settings → Environments
# → (this environment) → Environment variables.

set -euo pipefail

REPO="andriesfluit/claudeos"
CLONE_DIR="${HOME}/.claudeos"

emit() {
  # Emit a SessionStart hook JSON payload with optional additionalContext.
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

# Only run in the cloud environment; locally the memory lives on disk already.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  emit ""
  exit 0
fi

if [ -z "${CLAUDEOS_TOKEN:-}" ]; then
  emit "claudeOS memory niet geladen: CLAUDEOS_TOKEN ontbreekt in de cloud-environment. Voeg 'm toe onder Settings → Environments → Environment variables."
  exit 0
fi

# Clone or update the private repo. Idempotent.
if [ -d "$CLONE_DIR/.git" ]; then
  git -C "$CLONE_DIR" fetch --quiet origin
  git -C "$CLONE_DIR" reset --hard --quiet origin/HEAD
else
  rm -rf "$CLONE_DIR"
  git clone --quiet --depth 1 "https://x-access-token:${CLAUDEOS_TOKEN}@github.com/${REPO}.git" "$CLONE_DIR"
fi

# Assemble context: concatenate every .md file in the repo (sorted).
CONTEXT=$(
  {
    echo "# Andries' persoonlijke memory (claudeOS)"
    echo "Bron: github.com/${REPO}"
    echo
    find "$CLONE_DIR" -type f -name '*.md' -not -path '*/.git/*' | sort | while read -r f; do
      rel="${f#$CLONE_DIR/}"
      echo "---"
      echo "## ${rel}"
      echo
      cat "$f"
      echo
    done
  }
)

emit "$CONTEXT"
