@echo off
setlocal
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
set "continue_result=%ERRORLEVEL%"
if not "%continue_result%"=="0" echo Continue installation did not finish. Read the message above; no administrator rights are needed.
pause
exit /b %continue_result%
