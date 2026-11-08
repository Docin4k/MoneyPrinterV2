#!/bin/bash
# Makes one YouTube Short and uploads it, logging to logs/youtube.log.
# Usage: scripts/mac/run_youtube.sh <account_id> [ollama_model] [--no-upload]
# Normally started by launchd (see scripts/mac/schedule_youtube.sh).

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT" || exit 1
mkdir -p logs

# launchd starts jobs with a minimal PATH; ffmpeg from Homebrew lives here
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
export PYTHONUTF8=1

{
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') ====="
  "$ROOT/venv/bin/python" src/cron.py youtube "$@"
  echo "Exit code: $?"
} >> logs/youtube.log 2>&1
