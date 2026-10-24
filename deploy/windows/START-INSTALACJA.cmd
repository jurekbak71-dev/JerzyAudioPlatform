@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Instaluj.ps1"
set "RESULT=%ERRORLEVEL%"
echo.
pause
exit /b %RESULT%
