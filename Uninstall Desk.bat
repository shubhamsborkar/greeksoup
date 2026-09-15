@echo off
rem Double-click me to remove GreekSoup from this PC. It stops the desk, removes the
rem start-at-login task, saves a copy of your lists to the Desktop, and asks before
rem deleting the folder. Python stays; it is yours.
cd /d "%~dp0"
echo.
echo   GreekSoup: uninstall
echo   --------------------
rem Remove the start-at-login task only when it starts THIS folder's desk. Somebody
rem with a second copy of the desk keeps that copy's task exactly as it is.
set "TASK=Research Desk"
powershell -NoProfile -Command "$t = (schtasks /Query /TN '%TASK%' /XML 2>$null) -join ''; if (-not $t) { Write-Host '  No start-at-login task to remove.' } elseif ($t -like ('*' + '%~dp0'.TrimEnd('\') + '*')) { schtasks /End /TN '%TASK%' | Out-Null; schtasks /Delete /TN '%TASK%' /F | Out-Null; Write-Host '  Start-at-login task removed.' } else { Write-Host '  Left the start-at-login task alone: it starts another copy of the desk, not this one.' }"
rem stop only the desk that runs from THIS folder, never other Python programs
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0desk-stop.ps1"
if exist "data" (
  powershell -NoProfile -Command "$d=[Environment]::GetFolderPath('Desktop'); $z=Join-Path $d ('GreekSoup-backup-' + (Get-Date -Format yyyy-MM-dd) + '.zip'); Compress-Archive -Path 'data' -DestinationPath $z -Force; Write-Host ('  Your lists and data are saved at ' + $z + ' (your keys are not in it).')"
)
echo.
set /p ANSWER=  Delete the folder %~dp0 as well? [y/N]
if /i "%ANSWER%"=="y" goto delete
echo   Folder kept. Delete it whenever you like; nothing else remains.
pause
exit /b 0
:delete
echo   Deleting the folder. GreekSoup is gone from this PC.
start "" /min cmd /c "timeout /t 2 >nul & rd /s /q "%~dp0""
exit /b 0
