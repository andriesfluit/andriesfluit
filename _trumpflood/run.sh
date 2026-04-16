#!/usr/bin/env bash
# Scheduled run for trumpflood.
#
# Called by ~/Library/LaunchAgents/com.andriesfluit.trumpflood.plist
# three times a day (08:00 / 14:00 / 20:00 local).
#
# 1. Runs main.py, which fetches headlines, writes data/log.json, and
#    regenerates the site at <repo-root>/trumpflood/.
# 2. If the output changed, commits + pushes the relevant files so GitHub
#    Pages serves the fresh version at andriesfluit.be/trumpflood/.
#
# The git step is best-effort: failures are logged but don't break the run.

set -e
cd "$(dirname "$0")"
mkdir -p logs

if [ -d "venv" ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

python3 main.py 2>>logs/errors.log

# ---------------------------------------------------------------
# Publish step: commit and push only the trumpflood site artefacts
# and the data/log history. Everything else the user has pending
# in the repo (portfolio edits, unrelated files) is left alone.
# ---------------------------------------------------------------
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -n "$REPO_ROOT" ]; then
  # Never fail the cron run because of a push hiccup.
  {
    cd "$REPO_ROOT"
    # Stage only the paths we own.
    git add -A trumpflood/ _trumpflood/data/log.json 2>/dev/null || true

    # Any staged changes to commit?
    if ! git diff --cached --quiet; then
      STAMP="$(date '+%Y-%m-%d %H:%M %Z')"
      git -c user.email="trumpflood-bot@andriesfluit.be" \
          -c user.name="trumpflood-bot" \
          commit -m "trumpflood: update for $STAMP" >/dev/null
      git push 2>&1 || echo "[trumpflood] git push failed at $(date)"
    fi
  } >> "$(dirname "$0")/logs/publish.log" 2>&1 || true
fi
