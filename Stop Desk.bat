@echo off
rem Double-click me to switch the always-on desk OFF. Run "Keep Desk Running.bat" to switch it back on.
cd /d "%~dp0"
set "TASK=Research Desk"
schtasks /End /TN "%TASK%" >nul 2>&1
schtasks /Delete /TN "%TASK%" /F >nul 2>&1
rem stop only the desk that runs from THIS folder, never other Python programs
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0desk-stop.ps1"
echo.
echo   The desk is OFF and will not start at login. Double-click "Keep Desk Running.bat" to turn it back on.
echo.
pause
