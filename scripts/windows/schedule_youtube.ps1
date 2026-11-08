<#
.SYNOPSIS
  Schedules automatic YouTube Shorts uploads with Windows Task Scheduler.

.DESCRIPTION
  Creates a scheduled task that runs scripts\windows\run_youtube.bat at the
  given times every day, for the YouTube account with the given nickname
  (as created in the app's YouTube menu). Each run makes one Short and
  uploads it; output goes to logs\youtube.log.

  The task runs as you, only while you are logged in, because uploading uses
  your logged-in Firefox profile. If the computer was off or asleep at a
  scheduled time, the task runs as soon as it can afterwards.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\windows\schedule_youtube.ps1 -Nickname WonderBytes -Times 17:00

.EXAMPLE
  # Twice a day
  powershell -ExecutionPolicy Bypass -File scripts\windows\schedule_youtube.ps1 -Nickname WonderBytes -Times 12:00,18:00

.EXAMPLE
  # Remove the scheduled task
  powershell -ExecutionPolicy Bypass -File scripts\windows\schedule_youtube.ps1 -Remove
#>
param(
    [string]$Nickname = "WonderBytes",
    [string[]]$Times = @("17:00"),
    [string]$Model = "",
    [string]$TaskName = "MoneyPrinterV2 YouTube Shorts",
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed scheduled task '$TaskName'."
    exit 0
}

$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$cachePath = Join-Path $root ".mp\youtube.json"
if (-not (Test-Path $cachePath)) {
    throw "No YouTube accounts yet. Run the app (python src\main.py), choose YouTube Shorts Automation and create the account first."
}

$accounts = (Get-Content $cachePath -Raw | ConvertFrom-Json).accounts
$account = $accounts | Where-Object { $_.nickname -eq $Nickname } | Select-Object -First 1
if (-not $account) {
    $names = ($accounts | ForEach-Object { $_.nickname }) -join ", "
    throw "No YouTube account named '$Nickname'. Accounts found: $names"
}

$config = Get-Content (Join-Path $root "config.json") -Raw | ConvertFrom-Json
if (-not $Model) { $Model = $config.ollama_model }

$bat = Join-Path $root "scripts\windows\run_youtube.bat"
$arguments = "/c `"`"$bat`" $($account.id) $Model`""
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $arguments -WorkingDirectory $root
$triggers = $Times | ForEach-Object { New-ScheduledTaskTrigger -Daily -At $_ }
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $triggers -Settings $settings `
    -Description "Makes and uploads a YouTube Short for $Nickname (MoneyPrinterV2)." -Force | Out-Null

Write-Host "Scheduled '$TaskName' for $Nickname at $($Times -join ', ') every day."
Write-Host "Log file: $(Join-Path $root 'logs\youtube.log')"
Write-Host "To test now: Start-ScheduledTask -TaskName '$TaskName'"
