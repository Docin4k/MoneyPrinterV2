@echo off
REM Makes one YouTube Short and uploads it, logging to logs\youtube.log.
REM Usage: run_youtube.bat <account_id> [ollama_model] [--no-upload]
REM Normally started by Windows Task Scheduler (see schedule_youtube.ps1).

cd /d "%~dp0..\.."
if not exist logs mkdir logs

REM Status messages contain emoji; make Python write UTF-8 to the log file
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ===== %date% %time% ===== >> logs\youtube.log
REM Pick up new scripts added to the queue; fast-forward only, carry on either way
git pull --ff-only --quiet >> logs\youtube.log 2>&1 || echo Could not update from GitHub; using local scripts. >> logs\youtube.log
"venv\Scripts\python.exe" src\cron.py youtube %* >> logs\youtube.log 2>&1
echo Exit code: %errorlevel% >> logs\youtube.log
