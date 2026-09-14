@echo off
rem Double-click me to remove GreekSoup from this PC. It stops the desk, removes the
rem start-at-login task, saves a copy of your lists to the Desktop, and asks before
rem deleting the folder. Python stays; it is yours.
cd /d "%~dp0"
echo.
echo   GreekSoup: uninstall
echo   --------------------
set "TASK=Research Desk"
schtasks /End /TN "%TASK%" >nul 2>&1
schtasks /Delete /TN "%TASK%" /F >nul 2>&1
echo   Start-at-login task removed.
rem stop only the desk that runs from THIS folder, never other Python programs
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*server.py*' -and $_.CommandLine -like '*%~dp0*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo   The desk is stopped.
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
