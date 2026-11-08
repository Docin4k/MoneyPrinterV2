#!/bin/bash
# Schedules automatic YouTube Shorts uploads on macOS with launchd.
#
# Creates ~/Library/LaunchAgents/com.moneyprinterv2.youtube.plist, which runs
# scripts/mac/run_youtube.sh at the given times every day for the YouTube
# account with the given nickname (as created in the app's YouTube menu).
# Each run makes one Short and uploads it; output goes to logs/youtube.log.
#
# The job runs as you while you're logged in, because uploading uses your
# logged-in Firefox profile. If the Mac was asleep at a scheduled time, the
# job runs when it wakes; if it was shut down, that run is skipped.
#
# Usage:
#   scripts/mac/schedule_youtube.sh --nickname WonderBytes --times 17:00
#   scripts/mac/schedule_youtube.sh --nickname WonderBytes --times 12:00,18:00
#   scripts/mac/schedule_youtube.sh --run-now     # run the scheduled job once now
#   scripts/mac/schedule_youtube.sh --remove      # stop and delete the schedule

set -euo pipefail

LABEL="com.moneyprinterv2.youtube"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
NICKNAME="WonderBytes"
TIMES="17:00"
MODEL=""
ACTION="install"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --nickname) NICKNAME="$2"; shift 2 ;;
    --times) TIMES="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --remove) ACTION="remove"; shift ;;
    --run-now) ACTION="run"; shift ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1 (try --help)"; exit 1 ;;
  esac
done

if [[ "$ACTION" == "remove" ]]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"
  echo "Removed the schedule ($LABEL)."
  exit 0
fi

if [[ "$ACTION" == "run" ]]; then
  launchctl kickstart -p "gui/$(id -u)/$LABEL"
  echo "Started. Follow along with: tail -f \"$ROOT/logs/youtube.log\""
  exit 0
fi

PY="$ROOT/venv/bin/python"
[[ -x "$PY" ]] || { echo "No venv found at $ROOT/venv. Follow docs/MacSetup.md first."; exit 1; }
[[ -f "$ROOT/.mp/youtube.json" ]] || {
  echo "No YouTube accounts yet. Run the app (python src/main.py), choose YouTube Shorts Automation and create the account first."
  exit 1
}

ACCOUNT_ID="$("$PY" - "$ROOT/.mp/youtube.json" "$NICKNAME" <<'PYEOF'
import json, sys
accounts = json.load(open(sys.argv[1])).get("accounts", [])
match = [a["id"] for a in accounts if a.get("nickname") == sys.argv[2]]
if not match:
    names = ", ".join(a.get("nickname", "?") for a in accounts) or "none"
    sys.exit(f"No YouTube account named '{sys.argv[2]}'. Accounts found: {names}")
print(match[0])
PYEOF
)"

if [[ -z "$MODEL" ]]; then
  MODEL="$("$PY" -c "import json;print(json.load(open('$ROOT/config.json')).get('ollama_model',''))")"
fi

# One StartCalendarInterval entry per HH:MM time
INTERVALS=""
IFS=',' read -ra TIME_LIST <<< "$TIMES"
for t in "${TIME_LIST[@]}"; do
  t="$(echo "$t" | tr -d ' ')"
  [[ "$t" =~ ^([01]?[0-9]|2[0-3]):([0-5][0-9])$ ]] || { echo "Bad time '$t'; use HH:MM, e.g. 17:00"; exit 1; }
  INTERVALS+="    <dict><key>Hour</key><integer>$((10#${BASH_REMATCH[1]}))</integer><key>Minute</key><integer>$((10#${BASH_REMATCH[2]}))</integer></dict>
"
done

ARGS="    <string>/bin/bash</string>
    <string>$ROOT/scripts/mac/run_youtube.sh</string>
    <string>$ACCOUNT_ID</string>"
[[ -n "$MODEL" ]] && ARGS+="
    <string>$MODEL</string>"

mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/logs"
cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
$ARGS
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>StartCalendarInterval</key>
  <array>
$INTERVALS  </array>
  <key>StandardOutPath</key><string>$ROOT/logs/launchd.log</string>
  <key>StandardErrorPath</key><string>$ROOT/logs/launchd.log</string>
</dict>
</plist>
PLISTEOF

plutil -lint "$PLIST" >/dev/null
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "Scheduled $NICKNAME uploads every day at: $TIMES"
echo "Log file: $ROOT/logs/youtube.log"
echo "To test now: scripts/mac/schedule_youtube.sh --run-now"
