# GreekSoup: the one-person equity research desk. One-line install for Windows.
#
#   irm https://greeksoup.ai/install.ps1 | iex
#
# Finds Python (installs it with winget if missing), downloads the desk into
# %USERPROFILE%\GreekSoup, installs what it needs into its own folder, sets the desk to
# start at logon, starts it, and opens http://localhost:8765. Written from Microsoft's
# documented commands and not yet run on a Windows machine by the author; if a line
# complains, paste the window's text to your AI agent and ask it to fix it.
$ErrorActionPreference = "Stop"
$Repo = "shubhamsborkar/one-person-equity-research-desk"
$ZipUrl = "https://codeload.github.com/$Repo/zip/refs/heads/main"
$Dest = if ($env:GREEKSOUP_HOME) { $env:GREEKSOUP_HOME } else { Join-Path $env:USERPROFILE "GreekSoup" }
$Port = if ($env:GREEKSOUP_PORT) { $env:GREEKSOUP_PORT } else { "8765" }

Write-Host "`n  GreekSoup: the one-person equity research desk`n  ------------------------------------------------"

function Find-Python {
  foreach ($c in @("py -3.13", "py -3.12", "py -3.11", "py -3.10", "python3", "python")) {
    try {
      $v = & cmd /c "$c -c `"import sys;print(sys.version_info>=(3,10))`"" 2>$null
      if ($v -match "True") { return $c }
    } catch {}
  }
  return $null
}
$Py = Find-Python
if (-not $Py) {
  Write-Host "`n  Python is not on this PC yet. Installing it with winget (a window may ask you to approve)."
  winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements | Out-Null
  $Py = Find-Python
  if (-not $Py) { throw "Python was installed but could not be found. Close this window, open a new PowerShell and run the same line again." }
}
Write-Host "`n  Python found: $Py"

if (Test-Path (Join-Path $Dest "server.py")) {
  Write-Host "`n  The desk is already installed at $Dest. Starting it; new versions arrive through the strip inside the desk."
} else {
  Write-Host "`n  Downloading the desk into $Dest ..."
  $Tmp = Join-Path $env:TEMP ("greeksoup-" + [guid]::NewGuid().ToString())
  New-Item -ItemType Directory -Path $Tmp | Out-Null
  Invoke-WebRequest -Uri $ZipUrl -OutFile (Join-Path $Tmp "desk.zip")
  Expand-Archive -Path (Join-Path $Tmp "desk.zip") -DestinationPath $Tmp
  $Src = Get-ChildItem -Path $Tmp -Directory | Select-Object -First 1
  New-Item -ItemType Directory -Path (Split-Path $Dest) -Force | Out-Null
  Move-Item -Path $Src.FullName -Destination $Dest
  Remove-Item -Recurse -Force $Tmp
}
Set-Location $Dest

if (-not (Test-Path ".venv\Scripts\python.exe")) {
  Write-Host "`n  Installing what the desk needs (into its own folder) ..."
  & cmd /c "$Py -m venv .venv"
}
& .venv\Scripts\python.exe -m pip install -q --upgrade pip 2>$null
& .venv\Scripts\python.exe -m pip install -q -r requirements.txt

if (-not (Test-Path ".env")) {
  Copy-Item .env.example .env
  if ($Port -ne "8765") { (Get-Content .env) -replace "^DESK_PORT=.*", "DESK_PORT=$Port" | Set-Content .env }
}
New-Item -ItemType Directory -Path logs -Force | Out-Null

$Url = "http://localhost:$Port"
# GREEKSOUP_NO_SERVICE=1 starts the desk for this run only, without the start-at-login
# entry and without opening a browser. It is how the desk is tested on a fresh Windows
# machine that nobody is sitting at.
$NoService = -not [string]::IsNullOrWhiteSpace($env:GREEKSOUP_NO_SERVICE)
function Up { try { Invoke-WebRequest -Uri "$Url/api/ping" -TimeoutSec 2 -UseBasicParsing | Out-Null; $true } catch { $false } }
if (-not (Up)) {
  if ($NoService) {
    Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "server.py" -WorkingDirectory $Dest `
      -WindowStyle Hidden -RedirectStandardOutput "logs\desk.log" -RedirectStandardError "logs\desk-start.log"
  } else {
    $env:DESK_PORT = $Port
    & cmd /c "`"Keep Desk Running.bat`"" | Out-Null
  }
}
for ($i = 0; $i -lt 30; $i++) { if (Up) { break }; Start-Sleep -Seconds 2 }
if (-not (Up)) { throw "The desk has not answered yet. Give it a minute, then open $Url . If it stays blank, read $Dest\logs\desk-service.log or give it to your AI agent." }
if (-not $NoService) { Start-Process $Url }
$tail = if ($NoService) { "(this run only; not set to start at login)." } else { "and it starts with your computer from now on." }
Write-Host "`n  Done. The desk is at $Url $tail"
Write-Host "  Folder: $Dest"
Write-Host "  Keys are optional: the Settings screen inside the desk takes them."
Write-Host "  Newer versions: the desk tells you on every screen and updates with one click.`n"
