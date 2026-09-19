# GreekSoup: the one-person equity research desk. One-line install for Windows.
#
#   irm https://greeksoup.ai/install.ps1 | iex
#
# Finds Python (installs it with winget if missing), downloads the desk into
# %USERPROFILE%\GreekSoup, installs what it needs into its own folder, sets the desk to
# start at logon (no administrator needed), starts it, and opens http://localhost:8765.
# A fresh Windows machine runs this whole line on every change to the desk; if a line
# still complains on yours, paste the window's text to your AI agent and ask it to fix it.
$ErrorActionPreference = "Stop"
$Repo = "shubhamsborkar/greeksoup"
$ZipUrl = "https://codeload.github.com/$Repo/zip/refs/heads/main"
# the same repository, mirrored on GitLab with every push; used when GitHub does not answer
$MirrorZipUrl = "https://gitlab.com/shikshan-nivesh/greeksoup/-/archive/main/greeksoup-main.zip"
function Get-Desk($Out) {
  try { Invoke-WebRequest -Uri $ZipUrl -OutFile $Out }
  catch { Invoke-WebRequest -Uri $MirrorZipUrl -OutFile $Out }
}
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

# Ask 127.0.0.1 rather than "localhost": on Windows "localhost" is often the IPv6
# address first, and the desk listens on the IPv4 one, so the name can say nothing is
# there while the desk is running perfectly well.
function Up { try { Invoke-WebRequest -Uri "http://127.0.0.1:$Port/api/ping" -TimeoutSec 2 -UseBasicParsing | Out-Null; $true } catch { $false } }

if (Test-Path (Join-Path $Dest "server.py")) {
  if (Up) {
    Write-Host "`n  The desk is already installed at $Dest and running. New versions arrive through the strip inside the desk."
  } else {
    # Running the line again on an installed desk that is not up brings the folder to
    # the current version first (keys, lists and logs untouched), then starts it. A copy
    # too old to carry the updater gets the current files copied over it instead.
    Write-Host "`n  The desk is already installed at $Dest. Bringing it up to date, then starting it."
    if ((Test-Path (Join-Path $Dest "updater.py")) -and (Test-Path (Join-Path $Dest ".venv\Scripts\python.exe"))) {
      Push-Location $Dest
      try { & .venv\Scripts\python.exe updater.py apply 2>$null | Out-Null } catch {}
      Pop-Location
    } else {
      $Tmp = Join-Path $env:TEMP ("greeksoup-" + [guid]::NewGuid().ToString())
      New-Item -ItemType Directory -Path $Tmp | Out-Null
      Get-Desk (Join-Path $Tmp "desk.zip")
      Expand-Archive -Path (Join-Path $Tmp "desk.zip") -DestinationPath $Tmp
      $Src = (Get-ChildItem -Path $Tmp -Directory | Select-Object -First 1).FullName
      Get-ChildItem -Path $Src -Force | Where-Object { $_.Name -notin @(".env", "data", "logs", "cache", ".venv") } |
        ForEach-Object { Copy-Item -Path $_.FullName -Destination $Dest -Recurse -Force }
      Remove-Item -Recurse -Force $Tmp
    }
  }
} else {
  Write-Host "`n  Downloading the desk into $Dest ..."
  $Tmp = Join-Path $env:TEMP ("greeksoup-" + [guid]::NewGuid().ToString())
  New-Item -ItemType Directory -Path $Tmp | Out-Null
  Get-Desk (Join-Path $Tmp "desk.zip")
  Expand-Archive -Path (Join-Path $Tmp "desk.zip") -DestinationPath $Tmp
  $Src = Get-ChildItem -Path $Tmp -Directory | Select-Object -First 1
  New-Item -ItemType Directory -Path (Split-Path $Dest) -Force | Out-Null
  Move-Item -Path $Src.FullName -Destination $Dest
  Remove-Item -Recurse -Force $Tmp
  # The website and the install scripts came along in the zip; the desk never uses them,
  # and an antivirus reads an install script on disk as a downloader. Out they go.
  foreach ($x in @("docs", "site", "install.ps1", "install.sh")) {
    Remove-Item -Recurse -Force (Join-Path $Dest $x) -ErrorAction SilentlyContinue
  }
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
$proc = $null
if (-not (Up)) {
  if ($NoService) {
    $proc = Start-Process -FilePath (Join-Path $Dest ".venv\Scripts\python.exe") -ArgumentList "server.py" -WorkingDirectory $Dest `
      -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $Dest "logs\desk.log") `
      -RedirectStandardError (Join-Path $Dest "logs\desk-start.log")
  } else {
    # Start at logon and start now, with no administrator needed: a task for this
    # user, or a Startup shortcut when Windows refuses the task. Run as its own
    # PowerShell so a PC that forbids scripts still runs this one.
    $env:DESK_PORT = $Port
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Dest "desk-autostart.ps1")
  }
}
for ($i = 0; $i -lt 30; $i++) { if (Up) { break }; Start-Sleep -Seconds 2 }
if (-not (Up)) {
  # Say what the desk itself printed, so the reader (or their agent) has the reason
  # in front of them instead of only the fact that nothing answered.
  Write-Host "`n  The desk has not answered yet. This is what it printed:"
  if ($proc) {
    if ($proc.HasExited) { Write-Host "  The desk stopped by itself, exit code $($proc.ExitCode)." }
    else { Write-Host "  The desk is still running as process $($proc.Id), but nothing answered on door $Port." }
  }
  foreach ($f in @("logs\desk.log", "logs\desk-start.log", "logs\desk-service.log")) {
    $p = Join-Path $Dest $f
    if (Test-Path $p) {
      $size = (Get-Item $p).Length
      Write-Host "`n  --- $f ($size bytes) ---"
      if ($size -gt 0) { Get-Content $p -Tail 40 -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "  $_" } }
    } else {
      Write-Host "`n  --- ${f}: not there ---"
    }
  }
  throw "The desk has not answered yet. Give it a minute, then open $Url . If it stays blank, read $Dest\logs\desk.log or give it to your AI agent."
}
if (-not $NoService) { Start-Process $Url }
$tail = if ($NoService) { "(this run only; not set to start at login)." } else { "and it starts with your computer from now on." }
Write-Host "`n  Done. The desk is at $Url $tail"
Write-Host "  Folder: $Dest"
Write-Host "  Keys are optional: the Settings screen inside the desk takes them."
Write-Host "  Newer versions: the desk tells you on every screen and updates with one click.`n"
