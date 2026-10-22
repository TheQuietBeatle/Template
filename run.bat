@echo off
REM Start EGX Monitor (add --browser to open in your browser instead of a desktop window).
cd /d "%~dp0backend"
start "" .venv\Scripts\pythonw -m egx_monitor %*
