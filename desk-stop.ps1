# Stops the desk that runs from THIS folder, and only that one. "Stop Desk.bat" and
# "Uninstall Desk.bat" call it; nothing to run by hand.
#
# A desk is this folder's when the program answering on this folder's own door number
# is a server.py started by this folder's Python. Windows can spell the same folder two
# ways (C:\Users\runneradmin\... and C:\Users\RUNNER~1\...), and the desk may have been
# started under either, so both spellings are compared. Other Python programs, and
# another copy of the desk in another folder, are left exactly as they are.
param([string]$Folder = (Split-Path -Parent $MyInvocation.MyCommand.Path))
$ErrorActionPreference = "SilentlyContinue"

$long = (Resolve-Path $Folder).Path.TrimEnd('\')
$short = (New-Object -ComObject Scripting.FileSystemObject).GetFolder($long).ShortPath.TrimEnd('\')
$port = 8765
$envFile = Join-Path $long ".env"
if (Test-Path $envFile) {
  $m = Select-String -Path $envFile -Pattern '^DESK_PORT=(\d+)' | Select-Object -First 1
  if ($m) { $port = [int]$m.Matches[0].Groups[1].Value }
}

function IsThisDesk($p) {
  $exe = "$($p.ExecutablePath)"; $cmd = "$($p.CommandLine)"
  if ($cmd -notmatch 'server\.py') { return $false }
  foreach ($f in @($long, $short)) {
    if ($f -and ($exe.StartsWith($f, 'OrdinalIgnoreCase') -or $cmd.IndexOf($f, [StringComparison]::OrdinalIgnoreCase) -ge 0)) { return $true }
  }
  return $false
}

$stopped = 0
# First, whatever answers on this folder's door number.
$listeners = Get-NetTCPConnection -LocalPort $port -State Listen | Select-Object -ExpandProperty OwningProcess -Unique
foreach ($id in $listeners) {
  $p = Get-CimInstance Win32_Process -Filter "ProcessId = $id"
  if ($p -and (IsThisDesk $p)) { Stop-Process -Id $id -Force; $stopped++ }
  elseif ($p) { Write-Host "  Left alone: process $id ($($p.Name)) answers on door $port but is not this folder's desk." }
}
# Then any server.py run by this folder's Python that is not listening yet (starting up, or between restarts).
Get-CimInstance Win32_Process | Where-Object { IsThisDesk $_ } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; $stopped++ }

Start-Sleep -Milliseconds 800
$still = Get-NetTCPConnection -LocalPort $port -State Listen
if ($still) { Write-Host "  Something still answers on door $port. Restart the PC if it is the desk."; exit 1 }
if ($stopped -gt 0) { Write-Host "  The desk is stopped." } else { Write-Host "  The desk was not running." }
exit 0
