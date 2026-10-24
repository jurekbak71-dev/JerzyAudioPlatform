@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Wifi.ps1"
set "RESULT=%ERRORLEVEL%"
pause
exit /b %RESULT%
