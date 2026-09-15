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

Write-Host "`n=== Every PowerShell file parses ==="
foreach ($f in (Get-ChildItem -Path $Root -Filter *.ps1 -Recurse | Where-Object { $_.FullName -notmatch '\\\.venv\\' })) {
  $errs = $null
  [System.Management.Automation.Language.Parser]::ParseFile($f.FullName, [ref]$null, [ref]$errs) | Out-Null
  if ($errs -and $errs.Count -gt 0) { $errs | ForEach-Object { Write-Host ("  {0}: {1}" -f $f.Name, $_.Message) }; throw ("does not parse: " + $f.Name) }
  Write-Host ("  {0,-28} ok" -f $f.Name)
}

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

Write-Host "`n=== Start at login, the way a reader's PC gets it ==="
# A fresh machine in the cloud is the closest thing to a locked-down work PC: the
# task may be refused, and the Startup shortcut must then take over. Either way the
# check must see an entry that names this folder.
$env:GREEKSOUP_NO_TASK = "1"     # first the way a locked-down PC goes: the task refused, the shortcut takes over
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Dest "desk-autostart.ps1")
$doc = & (Join-Path $Dest ".venv\Scripts\python.exe") (Join-Path $Dest "doctor.py") "--offline" 2>&1 | Out-String
if ($doc -notmatch "start-at-login shortcut present") { Write-Host $doc; throw "the Startup shortcut was not made for this folder" }
Write-Host "  Startup shortcut made and the check sees it"
$env:GREEKSOUP_NO_TASK = ""      # then the ordinary way
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Dest "desk-autostart.ps1")
$doc = & (Join-Path $Dest ".venv\Scripts\python.exe") (Join-Path $Dest "doctor.py") "--offline" 2>&1 | Out-String
if ($doc -notmatch "start-at-login task present") { Write-Host $doc; throw "the scheduled task was not made for this folder" }
Write-Host "  scheduled task made and the check sees it"

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
$lnk = Join-Path ([Environment]::GetFolderPath("Startup")) "GreekSoup Desk.lnk"
$taskLeft = (schtasks /Query /TN "Research Desk" 2>$null) -join ''
if ((Test-Path $lnk) -or $taskLeft) { throw "a start-at-login entry is still there after the uninstall" }
Write-Host "  no start-at-login entry left behind"

Write-Host "`nWindows: install, every screen, the check and the uninstall all passed.`n"
