@echo off
rem Delegate argument handling and exit status to the shared V1 runner.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0make.ps1" %*
exit /b %errorlevel%
