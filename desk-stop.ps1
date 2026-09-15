# Stops the desk that runs from THIS folder, and only that one. "Stop Desk.bat" and
# "Uninstall Desk.bat" call it; nothing to run by hand.
#
# How this copy is told apart from any other program, in order:
#   1. logs\desk.pid: the desk writes its own process number there once it holds its
#      door number. That process is stopped when it is still a server.py.
#   2. Whatever answers on this folder's door number, when it, or the launcher that
#      started it, runs from this folder. A desk started through its .venv on Windows
#      runs as the child of a small launcher, and only the launcher's path names the
#      folder. Windows can also spell one folder two ways (C:\Users\runneradmin\... and
#      C:\Users\RUNNER~1\...), so both spellings are compared.
# Other Python programs, and another copy of the desk in another folder, are left alone.
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

function InFolder($p) {
  if (-not $p) { return $false }
  $exe = "$($p.ExecutablePath)"; $cmd = "$($p.CommandLine)"
  foreach ($f in @($long, $short)) {
    if ($f -and ($exe.StartsWith($f, [StringComparison]::OrdinalIgnoreCase) -or $cmd.IndexOf($f, [StringComparison]::OrdinalIgnoreCase) -ge 0)) { return $true }
  }
  return $false
}
function IsThisDesk($p) {
  if (-not $p) { return $false }
  if ("$($p.CommandLine)" -notmatch 'server\.py') { return $false }
  if (InFolder $p) { return $true }
  $parent = Get-CimInstance Win32_Process -Filter "ProcessId = $($p.ParentProcessId)"
  return (InFolder $parent)
}

$stopped = 0
# 1. the number the desk wrote down itself
$pidFile = Join-Path $long "logs\desk.pid"
if (Test-Path $pidFile) {
  $id = 0
  if ([int]::TryParse((Get-Content $pidFile -Raw).Trim(), [ref]$id) -and $id -gt 0) {
    $p = Get-CimInstance Win32_Process -Filter "ProcessId = $id"
    if ($p -and "$($p.CommandLine)" -match 'server\.py') { Stop-Process -Id $id -Force; $stopped++ }
  }
  Remove-Item $pidFile -Force
}
# 2. whatever answers on this folder's door number
foreach ($id in (Get-NetTCPConnection -LocalPort $port -State Listen | Select-Object -ExpandProperty OwningProcess -Unique)) {
  $p = Get-CimInstance Win32_Process -Filter "ProcessId = $id"
  if (-not $p) { continue }
  if (IsThisDesk $p) { Stop-Process -Id $id -Force; $stopped++ }
  else { Write-Host "  Left alone: process $id ($($p.Name)) answers on door $port but is not this folder's desk." }
}
# 3. a desk from this folder that is starting up or between restarts, and its launcher
Get-CimInstance Win32_Process | Where-Object { IsThisDesk $_ } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; $stopped++ }

Start-Sleep -Milliseconds 800
if (Get-NetTCPConnection -LocalPort $port -State Listen) { Write-Host "  Something still answers on door $port. Restart the PC if it is the desk."; exit 1 }
if ($stopped -gt 0) { Write-Host "  The desk is stopped." } else { Write-Host "  The desk was not running." }
exit 0
