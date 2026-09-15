@echo off
rem Double-click me ONCE (Windows). From then on the desk starts when you log in and restarts
rem by itself if it ever stops. Double-click "Stop Desk.bat" to switch it off.
rem No administrator needed: a scheduled task for this user, or a Startup shortcut when
rem Windows will not allow the task.
cd /d "%~dp0"
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0desk-autostart.ps1"
echo.
echo   Open it at http://localhost:8765 (or the door number in .env). Log: logs\desk-service.log
echo.
pause
