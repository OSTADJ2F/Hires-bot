@echo off
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" "qobuz_login.py"
pause
