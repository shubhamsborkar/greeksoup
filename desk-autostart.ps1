# Sets the desk in THIS folder to start when you log in, and starts it now. The one-line
# install and "Keep Desk Running.bat" call it; with -Remove, "Stop Desk.bat" and
# "Uninstall Desk.bat" call it to take the entry away again. Nothing to run by hand.
#
# Two ways to start at logon, tried in order, neither needing an administrator:
#   1. a task named "Research Desk" in Task Scheduler, made for this user only and with
#      no time limit (the default would stop the desk after three days);
#   2. if Windows refuses that, which many work and school PCs do with "Access is denied",
#      a shortcut in this user's own Startup folder, which every Windows allows.
# Either way the entry names this folder, so a second copy of the desk somewhere else is
# recognised and left alone. Windows can spell one folder two ways (C:\Users\runneradmin
# and C:\Users\RUNNER~1), so both spellings count as this folder.
param([switch]$Remove)
$ErrorActionPreference = "SilentlyContinue"

$here = (Split-Path -Parent $MyInvocation.MyCommand.Path).TrimEnd('\')
$short = (New-Object -ComObject Scripting.FileSystemObject).GetFolder($here).ShortPath.TrimEnd('\')
$task = "Research Desk"
$script = Join-Path $here "desk-service.ps1"
$lnk = Join-Path ([Environment]::GetFolderPath("Startup")) "GreekSoup Desk.lnk"
$psArgs = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$script`""
$port = 8765
$envFile = Join-Path $here ".env"
if (Test-Path $envFile) {
  $m = Select-String -Path $envFile -Pattern '^DESK_PORT=(\d+)' | Select-Object -First 1
  if ($m) { $port = [int]$m.Matches[0].Groups[1].Value }
}

function NamesHere($text) {
  if (-not $text) { return $false }
  foreach ($f in @($here, $short)) { if ($f -and $text.IndexOf($f, [StringComparison]::OrdinalIgnoreCase) -ge 0) { return $true } }
  return $false
}
function TaskXml { return ((schtasks /Query /TN $task /XML 2>$null) -join '') }
function LinkArgs { if (Test-Path $lnk) { return (New-Object -ComObject WScript.Shell).CreateShortcut($lnk).Arguments } else { return "" } }
function Up { try { Invoke-WebRequest -Uri "http://127.0.0.1:$port/api/ping" -TimeoutSec 2 -UseBasicParsing | Out-Null; $true } catch { $false } }

if ($Remove) {
  $x = TaskXml
  if (-not $x -and -not (Test-Path $lnk)) { Write-Host "  No start-at-login entry to remove."; exit 0 }
  if ($x) {
    if (NamesHere $x) { schtasks /End /TN $task 2>$null | Out-Null; schtasks /Delete /TN $task /F 2>$null | Out-Null; Write-Host "  Start-at-login task removed." }
    else { Write-Host "  Left the start-at-login task alone: it starts another copy of the desk, not this one." }
  }
  if (Test-Path $lnk) {
    if (NamesHere (LinkArgs)) { Remove-Item $lnk -Force; Write-Host "  Start-at-login shortcut removed." }
    else { Write-Host "  Left the Startup shortcut alone: it starts another copy of the desk, not this one." }
  }
  exit 0
}

if (-not (Test-Path (Join-Path $here ".venv\Scripts\python.exe"))) {
  Write-Host "  The desk is not installed yet. Run the one-line install first, or open this folder in your AI agent and paste the instruction from README.md."
  exit 1
}

# 1. the scheduled task, for this user only, no time limit. GREEKSOUP_NO_TASK=1 skips it,
#    which is how the Startup-shortcut path is tested on a machine that would allow the task.
$made = ""
try {
  if ($env:GREEKSOUP_NO_TASK) { throw "skipped" }
  $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $psArgs -WorkingDirectory $here
  $trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
  $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew
  Register-ScheduledTask -TaskName $task -Action $action -Trigger $trigger -Settings $settings -RunLevel Limited -Force -ErrorAction Stop | Out-Null
  if (NamesHere (TaskXml)) { $made = "task" }
} catch { $made = "" }
# one entry per folder: a shortcut left from an earlier run would start the desk twice
if ($made -eq "task" -and (Test-Path $lnk) -and (NamesHere (LinkArgs))) { Remove-Item $lnk -Force }

# 2. the Startup folder shortcut, when Windows would not allow the task
if (-not $made) {
  try {
    $ws = New-Object -ComObject WScript.Shell
    $s = $ws.CreateShortcut($lnk)
    $s.TargetPath = "powershell.exe"; $s.Arguments = $psArgs; $s.WorkingDirectory = $here
    $s.WindowStyle = 7; $s.Description = "Starts the GreekSoup desk when you log in"
    $s.Save()
    if (NamesHere (LinkArgs)) { $made = "shortcut" }
  } catch { $made = "" }
}
if (-not $made) {
  Write-Host "  Could not set the desk to start at login: Windows refused both a scheduled task and a Startup shortcut."
  Write-Host "  The desk still starts now. Paste this window's text to your AI agent and ask it to fix the start-at-login part."
}

# start it now, unless it already answers; one start only, never two
if (-not (Up)) {
  if ($made -eq "task") { schtasks /Run /TN $task 2>$null | Out-Null }
  else { Start-Process -FilePath "powershell.exe" -ArgumentList $psArgs -WorkingDirectory $here -WindowStyle Hidden }
}
switch ($made) {
  "task"     { Write-Host "  The desk starts at every login (a task in Task Scheduler) and restarts by itself if it stops." }
  "shortcut" { Write-Host "  The desk starts at every login (a shortcut in your Startup folder) and restarts by itself if it stops." }
}
exit 0
