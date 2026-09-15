# The whole Windows test, in one run: install the desk the way a reader does, open
# every screen with no keys at all, run the desk's own check, then remove it and make
# sure it is gone. A fresh Windows machine runs this on every change, which is how
# Windows is tested when there is no Windows PC in the room.
#
# It asks 127.0.0.1 rather than "localhost" throughout, because a fresh Windows machine
# in the cloud has no IPv6 and reads that name as an IPv6 address first.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Dest = if ($env:GREEKSOUP_HOME) { $env:GREEKSOUP_HOME } else { Join-Path $env:TEMP "GreekSoupSmoke" }
$Port = if ($env:GREEKSOUP_PORT) { $env:GREEKSOUP_PORT } else { "8799" }
$Base = "http://127.0.0.1:$Port"

Write-Host "`n=== Installing into $Dest on door $Port ==="
$env:GREEKSOUP_HOME = $Dest
$env:GREEKSOUP_PORT = $Port
$env:GREEKSOUP_NO_SERVICE = "1"
& (Join-Path $Root "install.ps1")

Write-Host "`n=== Every screen, with no keys at all ==="
$screens = @("/", "/usdesk", "/book", "/risk", "/watch?list=us", "/watch?list=global", "/funds", "/flow",
             "/short", "/capitol", "/macro", "/commods", "/chain", "/settings", "/api/ping", "/agent")
$bad = @()
foreach ($s in $screens) {
  try {
    $r = Invoke-WebRequest -Uri "$Base$s" -UseBasicParsing -TimeoutSec 90
    if ($r.StatusCode -eq 200) { Write-Host ("  {0,-18} 200" -f $s) }
    else { Write-Host ("  {0,-18} {1}" -f $s, $r.StatusCode); $bad += $s }
  } catch {
    Write-Host ("  {0,-18} {1}" -f $s, $_.Exception.Message)
    $bad += $s
  }
}
if ($bad.Count -gt 0) { throw ("these screens did not answer on Windows: " + ($bad -join ", ")) }

Write-Host "`n=== The desk's own check ==="
& (Join-Path $Dest ".venv\Scripts\python.exe") (Join-Path $Dest "doctor.py") "--offline"
if ($LASTEXITCODE -ne 0) { throw "the check found something to fix on Windows" }

Write-Host "`n=== Uninstall, keeping the folder ==="
Push-Location $Dest
try {
  $env:GREEKSOUP_DELETE = "n"
  & cmd /c "`"Uninstall Desk.bat`" < NUL"
} finally {
  Pop-Location
}
Start-Sleep -Seconds 3
$stillUp = $false
try {
  Invoke-WebRequest -Uri "$Base/api/ping" -UseBasicParsing -TimeoutSec 5 | Out-Null
  $stillUp = $true
} catch { }
if ($stillUp) { throw "the desk is still answering after the uninstall" }
Write-Host "  the desk is stopped"

Write-Host "`nWindows: install, every screen, the check and the uninstall all passed.`n"
