#!/usr/bin/env bash
#
# dispatch-monitors.sh
#
# Reliable backstop for GitHub's flaky `schedule` trigger. GitHub scheduled
# (cron) runs are best-effort and were not firing for this repo; manual/API
# dispatch works fine. Run this from launchd on the Mac once each morning: it
# dispatches each mediamonitor workflow on the right weekday, and skips a
# workflow if a run already happened today, so it coexists with GitHub's cron
# without sending duplicate mails.
#
# Cadence (Brussels weekday):
#   akkanto  (mediamonitor.yml)       Mon-Fri
#   bikon    (mediamonitor-bikon.yml) Mon/Wed/Fri
#
# Token: a fine-grained PAT for andriesfluit/andriesfluit with
#   Repository permissions -> Actions: Read and write.
# Provide it via env GH_DISPATCH_TOKEN, or in ~/.config/monitor-dispatch.token
# (chmod 600). Never commit the token; this repo is public.
#
# Usage:
#   GH_DISPATCH_TOKEN=... scripts/dispatch-monitors.sh [--dry-run]

set -euo pipefail

OWNER="andriesfluit"
REPO="andriesfluit"
API="https://api.github.com/repos/$OWNER/$REPO"
DRY_RUN="${1:-}"

TOKEN="${GH_DISPATCH_TOKEN:-}"
if [ -z "$TOKEN" ] && [ -f "$HOME/.config/monitor-dispatch.token" ]; then
  TOKEN=$(tr -d '\r\n' < "$HOME/.config/monitor-dispatch.token")
fi
if [ -z "$TOKEN" ]; then
  echo "ERROR: no token (set GH_DISPATCH_TOKEN or ~/.config/monitor-dispatch.token)" >&2
  exit 1
fi

DOW=$(TZ=Europe/Brussels date +%u)   # 1=Mon .. 7=Sun
TODAY=$(TZ=Europe/Brussels date +%F)

_api() {
  curl -fsS --max-time 25 \
            -H "Authorization: Bearer $TOKEN" \
            -H "Accept: application/vnd.github+json" \
            -H "X-GitHub-Api-Version: 2022-11-28" "$@"
}

dispatch_if_due() {
  local wf="$1" days="$2" label="$3"

  case ",$days," in
    *",$DOW,"*) ;;
    *) echo "[$label] not due today (Brussels weekday $DOW)"; return ;;
  esac

  # Date of the most recent run (any trigger/conclusion). If it is today, a
  # scheduled or earlier dispatch already covered it, so skip to avoid a dupe.
  # Fail-open: on any API hiccup, `last` is empty and we dispatch.
  local last
  last=$(_api "$API/actions/workflows/$wf/runs?per_page=1" 2>/dev/null \
         | python3 -c 'import sys,json; r=json.load(sys.stdin).get("workflow_runs",[]); print(r[0]["created_at"][:10] if r else "")' \
         2>/dev/null || echo "")

  if [ "$last" = "$TODAY" ]; then
    echo "[$label] already ran today ($last); skipping."
    return
  fi

  if [ "$DRY_RUN" = "--dry-run" ]; then
    echo "[$label] WOULD dispatch $wf (last run: ${last:-none})"
    return
  fi

  _api -X POST "$API/actions/workflows/$wf/dispatches" -d '{"ref":"main"}'
  echo "[$label] dispatched $wf at $(date '+%H:%M:%S')"
}

echo "=== monitor dispatch $(TZ=Europe/Brussels date '+%Y-%m-%d %H:%M %Z') (weekday $DOW) ==="
dispatch_if_due "mediamonitor.yml"       "1,2,3,4,5" "akkanto"
dispatch_if_due "mediamonitor-bikon.yml" "1,3,5"     "bikon"
