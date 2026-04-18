#!/bin/bash
# Scheduled run for trumpflood.
#
# Called by ~/Library/LaunchAgents/com.andriesfluit.trumpflood.plist
# three times a day (08:00 / 14:00 / 20:00 local) plus once at login/boot
# (RunAtLoad=true) to catch up on mornings the Mac was off.
#
# Design:
#   - Everything goes to logs/run.log with a date-stamped header so we
#     can see exactly what each invocation did.
#   - We DO NOT use `set -e` because we want individual commands to fail
#     visibly in the log without aborting the whole run.
#   - Script ALWAYS exits 0 regardless of what failed. launchd treats
#     non-zero as a reason to back off, which hides problems.

cd "$(dirname "$0")" || exit 0
mkdir -p logs

LOG="logs/run.log"
STAMP=$(date '+%Y-%m-%d %H:%M:%S %Z')

{
  echo ""
  echo "=========================================="
  echo "[$STAMP] run.sh started (pid=$$)"
  echo "=========================================="

  # ------------------- 1. Python fetch + render --------------------
  PYTHON="./venv/bin/python"
  if [ ! -x "$PYTHON" ]; then
    echo "[!] venv python not found, falling back to python3"
    PYTHON="python3"
  fi

  echo "[1/2] Running main.py via $PYTHON ..."
  if "$PYTHON" main.py; then
    echo "[1/2] main.py OK"
  else
    echo "[1/2] !!! main.py exited with $? — skipping publish"
    exit 0
  fi

  # ------------------- 2. Git publish ------------------------------
  REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
  if [ -z "$REPO_ROOT" ]; then
    echo "[2/2] No git repo found, skipping publish"
    exit 0
  fi

  cd "$REPO_ROOT" || { echo "[2/2] cd to $REPO_ROOT failed"; exit 0; }

  echo "[2/2] Pull-rebase origin/main ..."
  if git pull --rebase --autostash 2>&1; then
    echo "[2/2] pull OK"
  else
    echo "[2/2] !!! pull failed; aborting rebase, skipping publish"
    git rebase --abort 2>/dev/null
    exit 0
  fi

  echo "[2/2] Staging publish paths ..."
  git add -A trumpflood/ _trumpflood/data/log.json 2>&1
  # Non-fatal if no paths exist yet.

  if git diff --cached --quiet; then
    echo "[2/2] No changes to commit"
  else
    COMMIT_MSG="trumpflood: update for $(date '+%Y-%m-%d %H:%M %Z')"
    echo "[2/2] Committing: $COMMIT_MSG"
    git \
      -c user.email="trumpflood-bot@andriesfluit.be" \
      -c user.name="trumpflood-bot" \
      commit -m "$COMMIT_MSG" 2>&1

    echo "[2/2] Pushing ..."
    if git push 2>&1; then
      echo "[2/2] push OK"
    else
      echo "[2/2] !!! push failed (will retry next run)"
    fi
  fi

  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] run.sh finished"
} >> "$LOG" 2>&1

# Always exit 0 so launchd doesn't mark us as failing and back off.
exit 0
