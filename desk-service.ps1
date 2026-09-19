# Runs the desk and restarts it if it ever exits. Started at logon by the task that
# "Keep Desk Running.bat" registers. Nothing to run by hand.
#
# When the desk stops within a minute of starting three times in a row, something in the
# folder is wrong (an update that a Windows antivirus stopped part way, say). The service
# then brings the current version in by itself and starts again, so a desk nobody is
# watching comes back without anyone clicking anything.
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here
New-Item -ItemType Directory -Force -Path (Join-Path $here "logs") | Out-Null
$log = Join-Path $here "logs\desk-service.log"
$python = Join-Path $here ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }
$fastExits = 0
while ($true) {
  "$(Get-Date -Format s) starting desk" | Out-File -Append $log
  $started = Get-Date
  & $python server.py *>> $log
  $ran = ((Get-Date) - $started).TotalSeconds
  if ($ran -lt 60) { $fastExits++ } else { $fastExits = 0 }
  if ($fastExits -ge 3 -and (Test-Path (Join-Path $here "updater.py"))) {
    "$(Get-Date -Format s) the desk stopped three times within a minute of starting; bringing the current version in" | Out-File -Append $log
    try { & $python updater.py apply *>> $log } catch { "$(Get-Date -Format s) could not bring the version in: $_" | Out-File -Append $log }
    $fastExits = 0
    Start-Sleep -Seconds 30
    continue
  }
  "$(Get-Date -Format s) desk exited, restarting in 5 seconds" | Out-File -Append $log
  Start-Sleep -Seconds 5
}
