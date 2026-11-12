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
# Two native libraries bundle OpenMP on Intel Macs; without this the run aborts (OMP: Error #15)
export KMP_DUPLICATE_LIB_OK=TRUE
# On Intel Macs the two runtimes still crash Whisper unless OpenMP uses one thread
if [ "$(uname -m)" = "x86_64" ]; then export OMP_NUM_THREADS=1; fi
# If anything crashes, log the Python line it happened on
export PYTHONFAULTHANDLER=1

{
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') ====="
  # Pick up new scripts added to the queue (e.g. by the weekly writing session).
  # Fast-forward only, so local changes are never overwritten; carry on either way.
  git pull --ff-only --quiet 2>&1 && echo "Updated from GitHub." || echo "Could not update from GitHub; using local scripts."
  "$ROOT/venv/bin/python" src/cron.py youtube "$@"
  echo "Exit code: $?"
} >> logs/youtube.log 2>&1
